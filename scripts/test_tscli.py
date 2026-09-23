"""Self-test of the verified CLI path in scripts/tscli.py (R1-06, S04-H5). Stdlib unittest.

Usage: python scripts/test_tscli.py

1. The recorded, pinned binary runs.
2. A binary whose SHA-256 differs from the record is never executed, by any
   entry point (subprocess is not called).
3. The check scripts still work through the shared path.
4. No other script or CI step runs the CLI directly, so the check does not
   depend on CI running check_generated.py first.
5. has_error() agrees with the full --cst root line, hidden MISSING
   included, and stays fast on a deep tree (S04-H5).
"""
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
        # The binary path built outside tscli: tscli.EXE, a join onto the package directory, a bare name.
        direct = re.compile(r"\bEXE\b|tree-sitter-cli\"\s*/|\"tree-sitter(\.exe)?\"|\.bin/tree-sitter")
        for path in sorted(SCRIPTS.glob("*.py")):
            if path.name not in ("tscli.py", "test_tscli.py"):
                self.assertIsNone(direct.search(path.read_text(encoding="utf-8")), path.name)
        ci = (SCRIPTS.parent / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        self.assertIsNone(re.search(r"^\s*(run: )?(npx )?tree-sitter ", ci, re.M), "ci.yml runs the CLI directly")


if __name__ == "__main__":
    unittest.main(verbosity=2)
