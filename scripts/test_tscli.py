"""Self-test of the verified CLI path in scripts/tscli.py (R1-06, S04-H5). Stdlib unittest.

Usage: python scripts/test_tscli.py

1. The recorded, pinned binary runs.
2. A binary whose SHA-256 differs from the record is never executed, by any
   entry point (subprocess is not called), including the command line
   `python scripts/tscli.py` run in a copied tree.
3. Every run executes the verified private copy (validation.md "Identity
   binding"): a binary replaced in place after verification is not run, the
   copy's directory holds only the copy, a copy that differs from what was
   installed is refused, and the command line runs the copy.
4. A binary reporting another version than the pin is refused.
5. The check scripts still work through the shared path.
6. No other script names a CLI launcher or starts a program other than git
   (AST check), every `run` key of ci.yml is readable by the test, and every
   command it runs is on an allowlist without shell metacharacters, so the
   check does not depend on CI running check_generated.py first.
7. has_error() agrees with the full --cst root line, hidden MISSING
   included, and stays fast on a deep tree (S04-H5).
"""
import ast
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

import tscli
from corpus import read_corpus

SCRIPTS = Path(__file__).resolve().parent
# Commands a CI run step may execute: the installer, the check scripts (which reach the CLI only through tscli)
# and git. Anything else, for example `npm test` or `npx tree-sitter`, fails the structural test.
# Arguments are limited to characters without shell meaning, so nothing can be chained after an allowed command.
CI_ALLOWED = (r'npm ci|python scripts/[a-z0-9_]+\.py( [A-Za-z0-9_./=-]+)*|git [a-z-]+( --?[a-z-]+)*'
              r'|test -z "\$\(git status --porcelain\)"')
# Any `run` key in any YAML spelling (flow mapping, quoted key, extra spaces); each must be one the parser read.
ANY_RUN_KEY = re.compile(r"""(?:^|[\s{,])["']?run["']?\s*:""", re.M)


def ci_commands(text):
    """Every command of every `run:` step (single-line with continuation lines, `|` and `>` blocks).
    Raises ValueError for a `run` key the block-style parser cannot read, so no spelling goes unchecked."""
    lines, out, keys = text.splitlines(), [], 0
    for i, line in enumerate(lines):
        m = re.match(r"^(\s*)(- )?run: ?(.*)$", line)
        if not m:
            continue
        keys += 1
        indent = len(m.group(1)) + len(m.group(2) or "")
        body = []
        for nxt in lines[i + 1:]:
            if nxt.strip() and len(nxt) - len(nxt.lstrip()) <= indent:
                break
            body.append(nxt.strip())
        if m.group(3).strip() in ("|", ">"):
            out += [b for b in body if b]
        else:  # a plain scalar continues on more-indented lines
            out.append(" ".join([m.group(3).strip(), *[b for b in body if b]]))
    if len(ANY_RUN_KEY.findall(text)) != keys:
        raise ValueError("ci.yml has a run key in a form this test cannot check")
    return out


def allowed(command):
    return re.fullmatch(CI_ALLOWED, command) is not None


def copied_tree(d, suffix=b"", pin=None):
    """A minimal copy of the repository: scripts, provenance, package.json and the installed binary."""
    root = Path(d)
    shutil.copytree(SCRIPTS, root / "scripts", ignore=shutil.ignore_patterns("__pycache__"))
    (root / "docs/provenance").mkdir(parents=True)
    shutil.copyfile(tscli.ROOT / "docs/provenance/upstream-sources.md", root / "docs/provenance/upstream-sources.md")
    pkg = json.loads((tscli.ROOT / "package.json").read_text(encoding="utf-8"))
    if pin:
        pkg["devDependencies"]["tree-sitter-cli"] = pin
    (root / "package.json").write_text(json.dumps(pkg), encoding="utf-8")
    exe = root / tscli.EXE.relative_to(tscli.ROOT)
    exe.parent.mkdir(parents=True)
    exe.write_bytes(tscli.EXE.read_bytes() + suffix)
    return root


def command_line(root, *args):
    return subprocess.run([sys.executable, str(root / "scripts/tscli.py"), *args], capture_output=True, text=True,
                          encoding="utf-8")


class VerifiedCli(unittest.TestCase):
    def test_recorded_binary_runs(self):
        name, digest, version = tscli.verify()
        self.assertEqual(name, tscli.asset())
        self.assertRegex(digest, r"^[0-9a-f]{64}$")
        code, out, _ = tscli.cli("--version")
        self.assertEqual((code, out.strip()), (0, version))

    def test_substituted_binary_is_not_run(self):
        calls = []
        real = (tscli.EXE, tscli.subprocess.run, tscli.subprocess.Popen)
        with tempfile.TemporaryDirectory() as d:
            fake = Path(d) / tscli.EXE.name
            shutil.copyfile(tscli.EXE, fake)
            with open(fake, "ab") as f:
                f.write(b"\0")  # still a runnable program, but not the recorded one
            tscli.EXE = fake
            tscli.subprocess.run = tscli.subprocess.Popen = lambda *a, **k: calls.append(a)
            try:
                for entry in (lambda: tscli.cli("--version"), lambda: tscli.popen("--version"),
                              lambda: tscli.parse(fake), tscli.verify):
                    with self.assertRaisesRegex(RuntimeError, "was not run"):
                        entry()
                tscli.EXE = Path(d) / "missing"
                with self.assertRaisesRegex(RuntimeError, "missing"):
                    tscli.cli("--version")
            finally:
                tscli.EXE, tscli.subprocess.run, tscli.subprocess.Popen = real
        self.assertEqual(calls, [])

    def test_command_line_refuses_substituted_binary(self):
        with tempfile.TemporaryDirectory() as d:
            r = command_line(copied_tree(d, suffix=b"\0"), "--version")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("was not run", r.stderr)
        self.assertNotIn("tree-sitter", r.stdout)

    def test_version_other_than_the_pin_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            r = command_line(copied_tree(d, pin="0.0.0"), "--version")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("pinned 0.0.0", r.stderr)

    def test_replaced_binary_is_not_run_after_verification(self):
        real = tscli.EXE
        with tempfile.TemporaryDirectory() as d:
            installed = Path(d) / real.name
            shutil.copyfile(real, installed)
            tscli.EXE = installed
            try:
                _, digest, version = tscli.verify()
                installed.write_bytes(b"replaced after verification")  # same path, other content
                code, out, _ = tscli.cli("--version")
                self.assertEqual((code, out.strip()), (0, version))
                ran = tscli.executable()
                self.assertEqual(os.listdir(ran.parent), [real.name])  # nothing else is loaded from there
                self.assertEqual(ran.parent.parent, Path(tscli.BINDIR))
                self.assertEqual(hashlib.sha256(ran.read_bytes()).hexdigest(), digest)
            finally:
                tscli._verified.pop(installed, None)
                tscli.EXE = real

    def test_copy_changed_before_hashing_is_refused(self):
        real, copyfile = tscli.EXE, tscli.shutil.copyfile

        def corrupting(src, dst):  # the copy differs from what was installed: the hash must be of the copy
            copyfile(src, dst)
            with open(dst, "ab") as f:
                f.write(b"\0")

        with tempfile.TemporaryDirectory() as d:
            installed = Path(d) / real.name
            copyfile(real, installed)
            tscli.EXE, tscli.shutil.copyfile = installed, corrupting
            try:
                with self.assertRaisesRegex(RuntimeError, "was not run"):
                    tscli.verify()
            finally:
                tscli.shutil.copyfile = copyfile
                tscli._verified.pop(installed, None)
                tscli.EXE = real

    def test_command_line_runs_only_the_private_copy(self):
        with tempfile.TemporaryDirectory() as d:
            root = copied_tree(Path(d) / "repo")
            hook, log = Path(d) / "hook", Path(d) / "argv0.txt"
            hook.mkdir()
            (hook / "sitecustomize.py").write_text(
                "import subprocess\n_init = subprocess.Popen.__init__\n"
                "def init(self, args, *a, **k):\n"
                f"    with open({str(log)!r}, 'a', encoding='utf-8') as f:\n"
                "        f.write(str(args[0]) + '\\n')\n"
                "    _init(self, args, *a, **k)\n"
                "subprocess.Popen.__init__ = init\n", encoding="utf-8")
            r = subprocess.run([sys.executable, str(root / "scripts/tscli.py"), "--version"], capture_output=True,
                               text=True, encoding="utf-8", env={**os.environ, "PYTHONPATH": str(hook)})
            ran = log.read_text(encoding="utf-8").splitlines()
            installed = root / tscli.EXE.relative_to(tscli.ROOT)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertGreaterEqual(len(ran), 2)  # the version check and the command itself
        for argv0 in ran:
            self.assertNotEqual(Path(argv0), installed)
            self.assertIn("tree-sitter-bin-", argv0)

    def test_popen_rejects_another_program(self):
        for kwargs in ({"executable": sys.executable}, {"shell": True}):
            with self.assertRaises(ValueError):
                tscli.popen("--version", **kwargs)

    def test_check_scripts_still_work(self):
        for script in ("check_samples.py", "check_spellings.py"):
            r = subprocess.run([sys.executable, str(SCRIPTS / script)], capture_output=True, text=True,
                               encoding="utf-8")
            self.assertEqual(r.returncode, 0, f"{script}: {r.stdout[-500:]}{r.stderr[-500:]}")

    def test_has_error_reads_the_root_line_only(self):
        # Recovery fixtures whose MISSING node the default output does not show, and valid inputs.
        corpus, _ = read_corpus()
        names = ["BS-EXP-002: unclosed parenthesis", "BS-STMT-001: assignment missing its value",
                 "BS-ARRAY-001: array literal missing its closing bracket",
                 "BS-AA-001: associative array missing its closing brace", "BS-LEX-005: one statement per line"]
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "input.brs"
            for name in names:
                path.write_bytes(corpus[name]["input"])
                self.assertEqual(tscli.has_error(path), tscli.cst(path)[0], name)
                self.assertEqual(tscli.has_error(path), ":error" in corpus[name]["attrs"], name)
            # Tree depth about 20,000: the full --cst output would be about 400 MB.
            path.write_bytes(("x = " + "+".join(["1"] * 20000)).encode())
            start = time.monotonic()
            self.assertFalse(tscli.has_error(path, timeout=30))
            self.assertLess(time.monotonic() - start, 10)

    def test_no_direct_cli_run(self):
        for path in sorted(SCRIPTS.glob("*.py")):
            if path.name not in ("tscli.py", "test_tscli.py"):
                self.assertEqual(launches(path.read_text(encoding="utf-8")), [], path.name)
        for mutant in ('subprocess.run(["npx", "tree-sitter", "test"])', "BIN = 'node_modules/tree-sitter-cli/tree-sitter.exe'",
                       "subprocess.run(['npm', 'test'])", 'p = f"{ROOT}/node_modules/.bin/tree-sitter"',
                       'subprocess.run("npm test", shell=True)', 'os.system("npm test")', 'subprocess.run(["npm.cmd", "test"])',
                       'shutil.which("tree-sitter.cmd")', 'subprocess.run([sys.executable, "-c", "x"])', "x = EXE"):
            self.assertNotEqual(launches(mutant), [], mutant)
        self.assertEqual(launches('subprocess.run(["git", "status"], capture_output=True)'), [])
        commands = ci_commands((SCRIPTS.parent / ".github/workflows/ci.yml").read_text(encoding="utf-8"))
        self.assertIn("python scripts/tscli.py test", commands)
        for command in commands:
            self.assertTrue(allowed(command), f"ci.yml runs a command outside the allowlist: {command}")
        for mutant in ("npm test", "npx tree-sitter test", "node_modules/.bin/tree-sitter test", "npm run generate",
                       "tree-sitter test", 'python -c "import os"', "python scripts/check_v0.py && npx tree-sitter test",
                       "python scripts/check_v0.py; npm test", "python scripts/check_v0.py | sh",
                       "python scripts/check_v0.py $(npx tree-sitter test)"):
            self.assertFalse(allowed(mutant), mutant)
        self.assertEqual(ci_commands("    steps:\n      - run: npx tree-sitter test\n"), ["npx tree-sitter test"])
        self.assertEqual(ci_commands("      - run: python scripts/check_v0.py\n          && npx tree-sitter test\n"),
                         ["python scripts/check_v0.py && npx tree-sitter test"])
        for unread in ("      - {name: x, run: npx tree-sitter test}\n", "      -   run: npx tree-sitter test\n",
                       '      - "run": npx tree-sitter test\n', "      - run : npx tree-sitter test\n"):
            with self.assertRaises(ValueError, msg=unread):
                ci_commands(unread)


LAUNCHERS = re.compile(r"\bEXE\b|tree-sitter-cli['\"]?\s*/|tree-sitter\.(exe|cmd)\b|['\"]tree-sitter['\"]|\.bin[/\\]"
                       r"|\bnpx\b|\bpnpm\b|\byarn\b|\bnpm(\.cmd)?\b|shutil\.which")


def launches(source):
    """Ways a script could start a program other than git: launcher names and paths anywhere in the text, and
    subprocess/os calls whose argv[0] is not the literal "git" or that use a shell."""
    found = [m.group(0) for m in LAUNCHERS.finditer(source)]
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call):
            continue
        name = ast.unparse(node.func)
        if name in ("os.system", "os.popen") or name.startswith(("os.spawn", "os.exec")):
            found.append(name)
        elif name.startswith("subprocess.") and name.split(".")[1] in ("run", "Popen", "call", "check_call",
                                                                           "check_output"):
            argv = node.args[0] if node.args else None
            first = argv.elts[0] if isinstance(argv, (ast.List, ast.Tuple)) and argv.elts else None
            if not (isinstance(first, ast.Constant) and first.value == "git") or any(
                    k.arg == "shell" for k in node.keywords):
                found.append(ast.unparse(node))
    return found


if __name__ == "__main__":
    unittest.main(verbosity=2)
