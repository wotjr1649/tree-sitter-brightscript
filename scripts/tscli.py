"""Run the pinned tree-sitter CLI for the check scripts. Stdlib only.

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
import os
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


def cli(*args, cwd=ROOT, timeout=120, env=None):
    """Run the CLI; return (exit status, stdout with LF line ends, stderr)."""
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
