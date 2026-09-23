"""W03 composite samples (V3, V10), docs/validation/workload-matrix.md.

Usage: python scripts/check_samples.py
Every test/samples/*.brs parses without ERROR or MISSING, in at most 1 s of
parse time as reported by `tree-sitter parse --time`. Stdlib only.
"""
import re
import subprocess
import sys

from corpus import ROOT

EXE = ROOT / "node_modules/tree-sitter-cli" / ("tree-sitter.exe" if sys.platform == "win32" else "tree-sitter")
LIMIT_MS = 1000.0


def main():
    samples = sorted((ROOT / "test/samples").glob("*.brs"))
    fail = []
    for path in samples:
        r = subprocess.run([str(EXE), "parse", "--time", str(path)], cwd=ROOT, capture_output=True, timeout=60)
        out = r.stdout.decode("utf-8")
        ms = re.search(r"Parse:\s+([\d.]+) ms", out)
        problems = []
        if r.returncode or "ERROR" in out or "MISSING" in out:
            problems.append("ERROR or MISSING")
        if not ms or float(ms.group(1)) > LIMIT_MS:
            problems.append(f"parse time {ms.group(1) if ms else '?'} ms")
        rel = path.relative_to(ROOT).as_posix()
        print(f"{rel}: {ms.group(1) if ms else '?'} ms {'FAIL ' + ', '.join(problems) if problems else 'PASS'}")
        fail += [f"{rel}: {p}" for p in problems]
    if not samples:
        fail.append("no samples")
    if fail:
        print("FAIL")
        sys.exit(1)
    print("PASS")


if __name__ == "__main__":
    main()
