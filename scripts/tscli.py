"""Run the pinned tree-sitter CLI for the check scripts. Stdlib only.

Every run of the CLI goes through `cli()` or `popen()`, which call `verify()`
first. Once per process `verify()` copies the installed binary into a private
directory and hashes the copy: its SHA-256 must equal the decompressed release
asset recorded for this platform in docs/provenance/upstream-sources.md
(ADR-0002). Only then is the copy run, once, to confirm that it reports the
version pinned in package.json (60 s timeout), and from then on every run
executes that copy and nothing else. A binary that fails the hash comparison is
never executed; replacing or retargeting the installed binary after the check
does not change what the process runs; no DLL placed beside the installed
binary is loaded, because the copy's directory holds only the copy. Not
covered: another process of the same user writing into the private directory
while this one runs. `python scripts/tscli.py <arguments>` runs the verified
CLI the same way from the command line (for example `test`).

The CLI caches a compiled parser by grammar name alone, so every process gets
its own parser-library directory (TREE_SITTER_LIBDIR) and compiles the grammar
of its working directory on first use. An empty private configuration
directory (TREE_SITTER_DIR) keeps a user's `parser-directories` from selecting
another grammar for `.brs` files. Exit status 1 means either a visible
error in the tree or a failure to run (missing input, unloadable language), so
`parse` accepts a run only if a tree was printed. The error state of a tree is
the root line of `--cst` output (`•` marks has_error): it alone also reports
hidden MISSING nodes, which the exit status and the default output omit.
`has_error()` reads only that line (S04-H5), so a deep tree costs its parse,
not the depth-squared rest of the CST output.

A timeout stops only the CLI process started here. A compiler the CLI started
for its first grammar build may outlive it and leave a partial library in the
private parser directory; later calls then fail with "Failed to load
language" (fail-closed). The check scripts compile first with a long timeout.
Cleanup is `atexit` only: a killed process leaves its private directories in
the temporary directory. The working tree's record (upstream-sources.md,
package.json) and these scripts are trusted, and the programs the CLI starts
itself (node for `generate`, the C compiler for the first build) are not
identity-bound; V1 drift detects a divergent `generate`.
"""
import atexit
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

from corpus import ROOT

EXE = ROOT / "node_modules/tree-sitter-cli" / ("tree-sitter.exe" if sys.platform == "win32" else "tree-sitter")
LIBDIR = tempfile.mkdtemp(prefix="tree-sitter-lib-")
CONFIGDIR = tempfile.mkdtemp(prefix="tree-sitter-config-")
BINDIR = tempfile.mkdtemp(prefix="tree-sitter-bin-")
atexit.register(shutil.rmtree, LIBDIR, True)
atexit.register(shutil.rmtree, CONFIGDIR, True)
atexit.register(shutil.rmtree, BINDIR, True)
ENV = {**os.environ, "TREE_SITTER_LIBDIR": LIBDIR, "TREE_SITTER_DIR": CONFIGDIR, "NO_COLOR": "1"}
# A node line of --cst output: range, indentation, field, has_error mark, kind.
# Lines that hold only node text (hidden-text rows) start with a backtick and never match.
CST_LINE = re.compile(r"^(\d+):(\d+)\s*-\s*(\d+):(\d+)\s+(?:[a-z_]+: )?(•?)(\"(?:[^\"\\]|\\.)*\"|[^\s`]\S*)", re.M)
# A row of the release-asset table in upstream-sources.md: asset, asset SHA-256, decompressed binary SHA-256.
ASSET_ROW = re.compile(r"\| `(tree-sitter-[a-z0-9]+-[a-z0-9]+)\.gz` \| `([0-9a-f]{64})` \| `([0-9a-f]{64})` \|")
_verified = {}


def asset():
    """Name of the release asset for this platform, e.g. tree-sitter-windows-x64."""
    os_name = {"win32": "windows", "linux": "linux", "darwin": "macos"}.get(sys.platform, sys.platform)
    machine = platform.machine().lower()
    arch = {"amd64": "x64", "x86_64": "x64", "arm64": "arm64", "aarch64": "arm64"}.get(machine, machine)
    return f"tree-sitter-{os_name}-{arch}"


def verify():
    """Return (asset, binary SHA-256, version) of the private copy of EXE that every run executes,
    or raise RuntimeError without running a wrong binary."""
    if EXE in _verified:
        return _verified[EXE][0]
    if not EXE.is_file():
        raise RuntimeError(f"generator binary missing: {EXE} (run npm ci)")
    run_dir = Path(tempfile.mkdtemp(dir=BINDIR))
    copy = run_dir / EXE.name
    shutil.copyfile(EXE, copy)
    copy.chmod(0o700)
    name, digest = asset(), hashlib.sha256(copy.read_bytes()).hexdigest()
    sources = (ROOT / "docs/provenance/upstream-sources.md").read_text(encoding="utf-8")
    recorded = {m.group(1): m.group(3) for m in ASSET_ROW.finditer(sources)}.get(name)
    if recorded != digest:
        shutil.rmtree(run_dir, True)
        raise RuntimeError(f"{name}: installed binary SHA-256 {digest} != recorded {recorded} "
                           "in upstream-sources.md; the binary was not run")
    pinned = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))["devDependencies"]["tree-sitter-cli"]
    version = subprocess.run([str(copy), "--version"], env=ENV, capture_output=True, text=True,
                             timeout=60).stdout.strip()
    if version != f"tree-sitter {pinned}":
        raise RuntimeError(f"installed CLI reports {version!r}, pinned {pinned}")
    _verified[EXE] = ((name, digest, version), copy)
    return _verified[EXE][0]


def executable():
    """Path of the verified private copy (verify() first); the only file any run executes."""
    verify()
    return _verified[EXE][1]


def popen(*args, cwd=ROOT, env=None, **kwargs):
    """Start the verified CLI with the private directories; the caller owns the process."""
    if {"executable", "shell"} & kwargs.keys():
        raise ValueError("popen runs only the verified CLI: executable= and shell= are not accepted")
    return subprocess.Popen([str(executable()), *map(str, args)], cwd=cwd, env={**ENV, **(env or {})}, **kwargs)


def cli(*args, cwd=ROOT, timeout=120, env=None):
    """Run the verified CLI; return (exit status, stdout with LF line ends, stderr)."""
    r = subprocess.run([str(executable()), *map(str, args)], cwd=cwd, env={**ENV, **(env or {})},
                       capture_output=True, timeout=timeout)
    return r.returncode, r.stdout.decode("utf-8").replace("\r\n", "\n"), r.stderr.decode("utf-8", "replace")


def parse(path, *args, cwd=ROOT, timeout=120):
    """Parse one file; return the printed output, or raise if no tree was printed."""
    code, out, err = cli("parse", path, *args, cwd=cwd, timeout=timeout)
    tree = out.lstrip()
    if code not in (0, 1) or not (tree.startswith("(") or CST_LINE.match(tree)):
        raise RuntimeError(f"tree-sitter parse {path} failed (exit {code}): {err.strip()[-500:]}")
    return out


def cst(path, *args, cwd=ROOT, timeout=120):
    """Parse one file with --cst; return (root has_error, output)."""
    out = parse(path, "--cst", *args, cwd=cwd, timeout=timeout)
    return CST_LINE.match(out.lstrip()).group(5) == "•", out


def has_error(path, cwd=ROOT, timeout=120):
    """Root has_error of one file from the first node line of `--cst` output, without the rest.

    The CLI prints the finished tree's root line first; the rest of the CST
    output grows with depth squared (indentation and a parent lookup per node,
    crates/cli/src/parse.rs @ v0.27.0), so the child is stopped once the root
    line has been read. Only that child, started here, is ever terminated.
    """
    with tempfile.TemporaryFile() as err:
        proc = popen("parse", "--cst", path, cwd=cwd, stdout=subprocess.PIPE, stderr=err)
        expired = threading.Event()
        timer = threading.Timer(timeout, lambda: (expired.set(), proc.kill()))
        timer.start()
        try:
            line = b""
            while not line.strip():
                line = proc.stdout.readline()
                if not line:
                    break
            if proc.poll() is None:
                proc.kill()
            proc.communicate()
        finally:
            timer.cancel()
        m = CST_LINE.match(line.decode("utf-8", "replace").strip())
        if not m and expired.is_set():
            raise subprocess.TimeoutExpired(f"tree-sitter parse --cst {path}", timeout)
        if not m:
            err.seek(0)
            raise RuntimeError(f"tree-sitter parse --cst {path} printed no tree (exit {proc.returncode}): "
                               f"{err.read().decode('utf-8', 'replace').strip()[-500:]}")
        return m.group(5) == "•"


def cst_nodes(out):
    """(start row, column, end row, column, has_error, kind) for every node line of --cst output."""
    return [(int(a), int(b), int(c), int(d), e == "•", k) for a, b, c, d, e, k in CST_LINE.findall(out)]


if __name__ == "__main__":
    try:
        verify()
    except RuntimeError as e:
        sys.exit(f"tscli: {e}")
    sys.exit(subprocess.call([str(executable()), *sys.argv[1:]], env=ENV))
