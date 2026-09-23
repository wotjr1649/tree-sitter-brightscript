"""Self-test of the verified CLI path in scripts/tscli.py (R1-06, S04-H5). Stdlib unittest.

Usage: python scripts/test_tscli.py

1. The recorded, pinned binary runs.
2. A binary whose SHA-256 differs from the record is never executed, by any
   entry point (subprocess is not called), including the command line
   `python scripts/tscli.py` run in a copied tree.
3. A binary replaced in place after verification is not run: every run
   executes the verified private copy (validation.md "Identity binding").
4. A binary reporting another version than the pin is refused.
5. The check scripts still work through the shared path.
6. No other script builds the binary path, and every command of a CI run
   step is on an allowlist, so the check does not depend on CI running
   check_generated.py first.
7. has_error() agrees with the full --cst root line, hidden MISSING
   included, and stays fast on a deep tree (S04-H5).
"""
import hashlib
import json
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
CI_ALLOWED = (r'npm ci|python scripts/[a-z0-9_]+\.py( \S+)*|git [a-z-]+( --?[a-z-]+)*'
              r'|test -z "\$\(git status --porcelain\)"')


def ci_commands(text):
    """Every command line of every `run:` step of a workflow (single-line and `|` block forms)."""
    lines, out = text.splitlines(), []
    for i, line in enumerate(lines):
        m = re.match(r"^(\s*)(?:- )?run:\s*(.*)$", line)
        if not m:
            continue
        if m.group(2) not in ("|", ">"):
            out.append(m.group(2).strip())
            continue
        for body in lines[i + 1:]:
            if body.strip() and len(body) - len(body.lstrip()) <= len(m.group(1)):
                break
            if body.strip():
                out.append(body.strip())
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
                self.assertNotEqual(ran.parent, installed.parent)
                self.assertEqual(hashlib.sha256(ran.read_bytes()).hexdigest(), digest)
            finally:
                tscli._verified.pop(installed, None)
                tscli.EXE = real

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
        # The binary path or a CLI launcher built outside tscli, in any quoting: tscli.EXE, a path into the
        # package directory, the binary's file name, a bare `tree-sitter` argument, npx, npm.
        direct = re.compile(r"\bEXE\b|tree-sitter-cli['\"]?\s*/|tree-sitter\.exe|['\"]tree-sitter['\"]"
                            r"|\.bin/tree-sitter|\bnpx\b|['\"]npm['\"]")
        for path in sorted(SCRIPTS.glob("*.py")):
            if path.name not in ("tscli.py", "test_tscli.py"):
                self.assertIsNone(direct.search(path.read_text(encoding="utf-8")), path.name)
        for mutant in ('["npx", "tree-sitter", "test"]', "['node_modules/tree-sitter-cli/tree-sitter.exe']",
                       "subprocess.run(['npm', 'test'])", 'f"{ROOT}/node_modules/.bin/tree-sitter"'):
            self.assertIsNotNone(direct.search(mutant), mutant)
        commands = ci_commands((SCRIPTS.parent / ".github/workflows/ci.yml").read_text(encoding="utf-8"))
        self.assertIn("python scripts/tscli.py test", commands)
        for command in commands:
            self.assertTrue(allowed(command), f"ci.yml runs a command outside the allowlist: {command}")
        for mutant in ("npm test", "npx tree-sitter test", "node_modules/.bin/tree-sitter test", "npm run generate",
                       "tree-sitter test", 'python -c "import os"'):
            self.assertFalse(allowed(mutant), mutant)
        self.assertEqual(ci_commands("    steps:\n      - run: npx tree-sitter test\n"), ["npx tree-sitter test"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
