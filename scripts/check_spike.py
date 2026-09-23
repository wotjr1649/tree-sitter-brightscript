"""ADR-0004 spike criterion C4 (grammar-design §11): error recovery does not
swallow text outside a literal-false region.

Usage: python scripts/check_spike.py [--grammar-path=DIR]

For fixtures R1 and R2, parse the input and its repaired version (the malformed
line replaced by `x = 1`). C4 holds when every ERROR or MISSING node lies within
the malformed line and every node that starts after that line has the same type
and the same start and end row and column in both parses. R3 must parse with an
error and without a crash. C1-C3 are the spike corpus fixtures; C5 is
scripts/check_incremental.py (E1-E6). Stdlib only.
"""
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from corpus import ROOT, read_corpus

EXE = ROOT / "node_modules/tree-sitter-cli" / ("tree-sitter.exe" if sys.platform == "win32" else "tree-sitter")
GRAMMAR = Path(next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--grammar-path=")), ROOT)).resolve()
NODE = re.compile(r"\((MISSING \S+|\S+) \[(\d+), (\d+)\] - \[(\d+), (\d+)\]")
MALFORMED = b"x = = 1"


def nodes(path):
    r = subprocess.run([str(EXE), "parse", "-p", str(GRAMMAR), str(path)], cwd=GRAMMAR, capture_output=True, timeout=60)
    tree = "\n".join(l for l in r.stdout.decode("utf-8").splitlines() if "\tParse:" not in l)
    return [(m.group(1), *(int(x) for x in m.groups()[1:])) for m in NODE.finditer(tree)]


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
            broken, repaired = nodes(bad), nodes(good)
            errors = [n for n in broken if n[0] == "ERROR" or n[0].startswith("MISSING")]
            if not errors:
                fail.append(f"{rid}: no error node")
            for n in errors:
                if not (n[1] == row and n[3] == row):
                    fail.append(f"{rid}: {n} lies outside the malformed line {row}")
            after = lambda ns: [n for n in ns if n[1] > row]  # noqa: E731
            if after(broken) != after(repaired):
                fail.append(f"{rid}: nodes after line {row} differ from the repaired parse")
            print(f"{rid}: errors {errors}; nodes after line {row}: {len(after(broken))} "
                  f"{'equal' if after(broken) == after(repaired) else 'DIFFERENT'}")
        name = next(n for n in corpus if n.startswith("BS-COND-007: spike R3 "))
        r3 = Path(d) / "R3.brs"
        r3.write_bytes(corpus[name]["input"])
        found = nodes(r3)
        has_error = any(n[0] == "ERROR" or n[0].startswith("MISSING") for n in found)
        if not has_error:
            fail.append("R3: no error node")
        print(f"R3: {len(found)} nodes, error present: {has_error}")
    if fail:
        print("FAIL")
        for x in fail:
            print("  -", x)
        sys.exit(1)
    print("PASS")


if __name__ == "__main__":
    main()
