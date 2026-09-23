"""ADR-0004 spike criterion C4 (grammar-design §11): error recovery does not
swallow text outside a literal-false region.

Usage: python scripts/check_spike.py [--grammar-path=DIR]

For fixtures R1 and R2, parse the input and its repaired version (the malformed
line replaced by `x = 1`) with `--cst` (every node, with its has_error mark).
C4 holds when the repaired version has no error, every ERROR or MISSING node
lies within the malformed line, and every node that ends before that line or
starts after it has the same kind, range and has_error mark in both parses, so
an error hidden outside the line (a hidden MISSING node) also fails. R3 must
parse with an error. C1-C3 are the spike corpus fixtures; C5 is
scripts/check_incremental.py (E1-E6). Stdlib only.
"""
import sys
import tempfile
from pathlib import Path

from corpus import ROOT, read_corpus
from tscli import cst, cst_nodes

GRAMMAR = Path(next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--grammar-path=")), ROOT)).resolve()
MALFORMED = b"x = = 1"


def main():
    corpus, _ = read_corpus(GRAMMAR / "test/corpus")
    fail = []
    with tempfile.TemporaryDirectory() as d:
        for rid in ("R1", "R2"):
            name = next(n for n in corpus if n.startswith(f"BS-COND-007: spike {rid} "))
            text = corpus[name]["input"]
            row = text.split(b"\n").index(MALFORMED)
            bad, good = Path(d) / f"{rid}.brs", Path(d) / f"{rid}-repaired.brs"
            bad.write_bytes(text)
            good.write_bytes(text.replace(MALFORMED, b"x = 1"))
            broken, (repaired_error, repaired) = cst_nodes(cst(bad, cwd=GRAMMAR)[1]), cst(good, cwd=GRAMMAR)
            repaired = cst_nodes(repaired)
            if repaired_error:
                fail.append(f"{rid}: the repaired input has an error")
            errors = [n for n in broken if n[5] == "ERROR" or n[5].startswith("MISSING")]
            if not errors:
                fail.append(f"{rid}: no error node")
            for n in errors:
                if not (n[0] == row and n[2] == row):
                    fail.append(f"{rid}: {n} lies outside the malformed line {row}")
            outside = lambda ns: [n for n in ns if n[2:4] <= (row, 0) or n[:2] >= (row + 1, 0)]  # noqa: E731
            same = outside(broken) == outside(repaired)
            if not same:
                fail.append(f"{rid}: nodes outside line {row} differ from the repaired parse")
            print(f"{rid}: errors {errors}; nodes outside line {row}: {len(outside(broken))} "
                  f"{'equal' if same else 'DIFFERENT'}")
        name = next(n for n in corpus if n.startswith("BS-COND-007: spike R3 "))
        r3 = Path(d) / "R3.brs"
        r3.write_bytes(corpus[name]["input"])
        has_error, out = cst(r3, cwd=GRAMMAR)
        if not has_error:
            fail.append("R3: no error")
        print(f"R3: {len(cst_nodes(out))} nodes, error present: {has_error}")
    if fail:
        print("FAIL")
        for x in fail:
            print("  -", x)
        sys.exit(1)
    print("PASS")


if __name__ == "__main__":
    main()
