"""Run the pinned tree-sitter CLI for the check scripts. Stdlib only.

Every run of the CLI goes through `cli()` or `popen()`, which call `verify()`
first: the binary's SHA-256 must equal the decompressed release asset recorded
for this platform in docs/provenance/upstream-sources.md (ADR-0002), and only
then is the binary run, once, to confirm that it reports the version pinned in
package.json. A binary that fails the hash comparison is never executed. The
result is cached per process. `python scripts/tscli.py <arguments>` runs the
verified CLI the same way from the command line (for example `test`).

The CLI caches a compiled parser by grammar name alone, so every process gets
its own parser-library directory (TREE_SITTER_LIBDIR) and compiles the grammar
of its working directory on first use. An empty private configuration
directory (TREE_SITTER_DIR) keeps a user's `parser-directories` from selecting
another grammar for `.brs` files. Exit status 1 means either a visible
error in the tree or a failure to run (missing input, unloadable language), so
`parse` accepts a run only if a tree was printed. The error state of a tree is
the root line of `--cst` output (`•` marks has_error): it alone also reports
hidden MISSING nodes, which the exit status and the default output omit.
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

from corpus import ROOT

EXE = ROOT / "node_modules/tree-sitter-cli" / ("tree-sitter.exe" if sys.platform == "win32" else "tree-sitter")
LIBDIR = tempfile.mkdtemp(prefix="tree-sitter-lib-")
CONFIGDIR = tempfile.mkdtemp(prefix="tree-sitter-config-")
atexit.register(shutil.rmtree, LIBDIR, True)
atexit.register(shutil.rmtree, CONFIGDIR, True)
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
    """Return (asset, binary SHA-256, version) of EXE, or raise RuntimeError without running a wrong binary."""
    if EXE in _verified:
        return _verified[EXE]
    if not EXE.is_file():
        raise RuntimeError(f"generator binary missing: {EXE} (run npm ci)")
    name, digest = asset(), hashlib.sha256(EXE.read_bytes()).hexdigest()
    sources = (ROOT / "docs/provenance/upstream-sources.md").read_text(encoding="utf-8")
    recorded = {m.group(1): m.group(3) for m in ASSET_ROW.finditer(sources)}.get(name)
    if recorded != digest:
        raise RuntimeError(f"{name}: installed binary SHA-256 {digest} != recorded {recorded} "
                           "in upstream-sources.md; the binary was not run")
    pinned = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))["devDependencies"]["tree-sitter-cli"]
    version = subprocess.run([str(EXE), "--version"], env=ENV, capture_output=True, text=True).stdout.strip()
    if version != f"tree-sitter {pinned}":
        raise RuntimeError(f"installed CLI reports {version!r}, pinned {pinned}")
    _verified[EXE] = (name, digest, version)
    return _verified[EXE]


def popen(*args, cwd=ROOT, env=None, **kwargs):
    """Start the verified CLI with the private directories; the caller owns the process."""
    verify()
    return subprocess.Popen([str(EXE), *map(str, args)], cwd=cwd, env={**ENV, **(env or {})}, **kwargs)


def cli(*args, cwd=ROOT, timeout=120, env=None):
    """Run the verified CLI; return (exit status, stdout with LF line ends, stderr)."""
    verify()
    r = subprocess.run([str(EXE), *map(str, args)], cwd=cwd, env={**ENV, **(env or {})}, capture_output=True,
                       timeout=timeout)
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


def cst_nodes(out):
    """(start row, column, end row, column, has_error, kind) for every node line of --cst output."""
    return [(int(a), int(b), int(c), int(d), e == "•", k) for a, b, c, d, e, k in CST_LINE.findall(out)]


if __name__ == "__main__":
    try:
        verify()
    except RuntimeError as e:
        sys.exit(f"tscli: {e}")
    sys.exit(subprocess.call([str(EXE), *sys.argv[1:]], env=ENV))
