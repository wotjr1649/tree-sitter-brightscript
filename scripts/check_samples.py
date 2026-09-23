"""W03 composite samples (V3, V10), docs/validation/workload-matrix.md.

Usage: python scripts/check_samples.py
The catalogued samples exist and are the only ones; program-crlf.brs is the
CRLF byte copy of program.brs; every sample parses with no error (root
has_error unset, hidden MISSING included) in at most 1 s of parse time as
reported by `tree-sitter parse --time`. Stdlib only.
"""
import re
import sys

from corpus import ROOT
from tscli import cst

SAMPLES = ["compact.brs", "program-crlf.brs", "program.brs"]
LIMIT_MS = 1000.0


def main():
    fail = []
    found = sorted(p.name for p in (ROOT / "test/samples").glob("*.brs"))
    if found != SAMPLES:
        fail.append(f"samples {found} differ from the catalogue {SAMPLES}")
    lf, crlf = (ROOT / "test/samples/program.brs").read_bytes(), (ROOT / "test/samples/program-crlf.brs").read_bytes()
    if b"\r" in lf or crlf != lf.replace(b"\n", b"\r\n"):
        fail.append("program-crlf.brs is not the CRLF byte copy of the LF program.brs")
    for name in SAMPLES:
        path = ROOT / "test/samples" / name
        has_error, out = cst(path, "--time")
        ms = re.search(r"Parse:\s+([\d.]+) ms", out)
        problems = []
        if has_error:
            problems.append("ERROR or MISSING")
        if not ms or float(ms.group(1)) > LIMIT_MS:
            problems.append(f"parse time {ms.group(1) if ms else '?'} ms")
        print(f"test/samples/{name}: {ms.group(1) if ms else '?'} ms {'FAIL ' + ', '.join(problems) if problems else 'PASS'}")
        fail += [f"{name}: {p}" for p in problems]
    if fail:
        print("FAIL")
        for x in fail:
            print("  -", x)
        sys.exit(1)
    print("PASS")


if __name__ == "__main__":
    main()
