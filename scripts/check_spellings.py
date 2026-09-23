"""W05 equivalent spellings (V3), docs/validation/workload-matrix.md.

Usage: python scripts/check_spellings.py
Every spelling of a pair (or group) parses with no error (root has_error
unset, hidden MISSING included), and the trees are identical after removing anonymous nodes and ranges
(`tree-sitter parse --no-ranges`). The last pair compares the LF and CRLF
composite samples. Stdlib only.
"""
import sys
import tempfile
from pathlib import Path

from corpus import ROOT
from tscli import cst, parse

PAIRS = {
    "BS-LEX-001 keyword case": ["IF x THEN PRINT 1", "if x then print 1"],
    "BS-LEX-031, BS-STMT-024 print / ?": ["print 1", "? 1"],
    "BS-STMT-010, 022 end if": ["if x then\n  y = 1\nend if", "if x then\n  y = 1\nendif", "if x then\n  y = 1\nend   if"],
    "BS-STMT-010 else if": ["if a then\n  x = 1\nelse if b then\n  x = 2\nend if",
                            "if a then\n  x = 1\nelseif b then\n  x = 2\nend if"],
    "BS-STMT-013 end for / next": ["for i = 1 to 2\n  x = i\nend for\nfor each v in list\nend for",
                                   "for i = 1 to 2\n  x = i\nnext\nfor each v in list\nnext"],
    "BS-STMT-020 while": ["while x\n  exit while\nend while", "while x\n  exitwhile\nendwhile"],
    "BS-FUNC-003 function and sub": ["function f()\nend function\nsub s()\nend sub",
                                     "function f()\nendfunction\nsub s()\nendsub"],
    "BS-ERR-001 end try": ["try\ncatch e\nend try", "try\ncatch e\nendtry"],
    "BS-LEX-012, 013 comments": ["' x", "REM x"],
    "BS-ARRAY-005 dim": ["dim a[5]", "dim a(5)"],
}
FILES = {"BS-LEX-006 LF / CRLF": ["test/samples/program.brs", "test/samples/program-crlf.brs"]}


def tree(path):
    return parse(path, "--no-ranges"), not cst(path)[0]


def main():
    fail = []
    with tempfile.TemporaryDirectory() as d:
        groups = {}
        for name, texts in PAIRS.items():
            paths = []
            for i, text in enumerate(texts):
                p = Path(d) / f"{len(groups)}-{i}.brs"
                p.write_bytes(text.encode("utf-8"))
                paths.append(p)
            groups[name] = paths
        groups.update({k: [ROOT / f for f in v] for k, v in FILES.items()})
        for name, paths in groups.items():
            results = [tree(p) for p in paths]
            problems = []
            if not all(ok for _, ok in results):
                problems.append("ERROR or MISSING")
            if len({t for t, _ in results}) != 1:
                problems.append("trees differ")
            print(f"{name}: {'FAIL ' + ', '.join(problems) if problems else 'PASS'}")
            fail += [f"{name}: {p}" for p in problems]
    if fail:
        print("FAIL")
        sys.exit(1)
    print("PASS")


if __name__ == "__main__":
    main()
