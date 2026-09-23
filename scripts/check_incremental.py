"""W10 incremental edits (V5), docs/validation/workload-matrix.md.

Usage: python scripts/check_incremental.py [--only=I01,E3,...] [--no-spike] [--grammar-path=DIR]

For each script, parse the base text with `tree-sitter parse --edits` (every edit
is followed by an incremental reparse) and compare the final tree with a fresh
parse of the final text: the default output (named nodes, fields, ranges) and
the `--cst` output (every node) must be identical, and the final text must parse
with no error (root has_error unset, hidden MISSING included). Edits use the CLI
form `row,column deleted inserted` on the current text; inserted text is passed
literally (newline and CR bytes included). Bases I01-I12 are corpus fixture
inputs; E1-E6 are the ADR-0004 spike scripts (grammar-design §11), run unless
--no-spike. A script whose base fixture is absent, or an --only name that
matches no script, fails. Stdlib only.
"""
import sys
import tempfile
from pathlib import Path

from corpus import ROOT, read_corpus
from tscli import has_error, parse

# The catalogue describes I01-I12 in words; these are the concrete edits.
SCRIPTS = {
    "I01": ("BS-LEX-009: blank lines around and inside blocks", ["4,3 0 y", "4,3 1 "]),
    "I02": ("BS-LEX-005: one statement per line", ["0,5 1 ", "0,5 0 \n"]),
    "I03": ("BS-LEX-010: colon-separated statements", ["0,3 0  : z = 3", "0,3 8 "]),
    "I04": ("BS-STMT-007: single-line IF with THEN",
            ["0,16 20 \nprint 1\nend if", '0,16 15 print "out of range"']),
    "I05": ("BS-STMT-010: block IF with ELSE IF and ELSE", ["5,19 7 ", "5,19 0 \nend if", "2,0 30 "]),
    "I06": ("BS-LIT-016: doubled quotation marks", ['1,5 0 ""', "1,5 2 "]),
    "I07": ("BS-LEX-012: apostrophe comment lines", ["2,0 0 '", "2,0 1 "]),
    "I08": ("BS-LEX-014: identifiers beginning with rem", ["0,3 0  ", "0,3 1 "]),
    "I09": ("BS-EXP-007: optional chaining chain",
            ["0,9 1 ", "0,12 1 ", "0,16 1 ", "0,20 1 ", "0,9 0 ?", "0,13 0 ?", "0,18 0 ?", "0,23 0 ?"]),
    "I10": ("BS-AA-003: multi-line associative array with commas", ["1,10 1 ", "1,10 0 ,"]),
    "I11": ("BS-LEX-006: mixed LF and CRLF line endings", ["0,5 1 ", "0,5 0 \r"]),
    "I12": ("BS-COND-002: #if around statements", ["1,19 8 ", "1,19 0 \n#end if"]),
}
SPIKE_BASE = b"x = 1\n#if false\n    This is prose.\n#end if\nfunction foo() as void\nend function"
SPIKE = {
    "E1": ["2,12 5 text"],
    "E2": ["1,0 0 y = 2\n"],
    "E3": ["4,0 0 z = 3\n"],
    "E4": ["3,0 8 ", "3,0 0 #end if\n"],
    "E5": ["1,4 5 true", "1,4 4 false"],
    "E6": ["3,0 0 #else\nx = 2\n"],
}


def apply(text, edit):
    """Apply one CLI edit string to bytes, exactly as parse.rs does."""
    position, deleted, inserted = edit.split(" ", 2)
    row, column = (int(x) for x in position.split(","))
    lines = text.split(b"\n")
    offset = sum(len(l) + 1 for l in lines[:row]) + column
    return text[:offset] + inserted.encode("utf-8") + text[offset + int(deleted):]


GRAMMAR = Path(next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--grammar-path=")), ROOT)).resolve()


def run(name, base, edits, tmp):
    base_file, final_file = tmp / f"{name}-base.brs", tmp / f"{name}-final.brs"
    base_file.write_bytes(base)
    final = base
    for e in edits:
        final = apply(final, e)
    final_file.write_bytes(final)
    edit_args = [a for e in edits for a in ("--edits", e)]
    problems = []
    for mode in ([], ["--cst"]):
        incremental = parse(base_file, *mode, *edit_args, cwd=GRAMMAR).replace(str(base_file), "FILE")
        fresh = parse(final_file, *mode, cwd=GRAMMAR).replace(str(final_file), "FILE")
        if incremental != fresh:
            problems.append(f"incremental != fresh{' (cst)' if mode else ''}")
    if has_error(final_file, cwd=GRAMMAR):
        problems.append("final text does not parse cleanly")
    return problems


def main():
    only = next((a.split("=", 1)[1].split(",") for a in sys.argv if a.startswith("--only=")), None)
    corpus, _ = read_corpus(GRAMMAR / "test/corpus")
    scripts = {k: (corpus[b]["input"], e) for k, (b, e) in SCRIPTS.items() if b in corpus}
    missing = sorted(set(SCRIPTS) - set(scripts))
    if "--no-spike" not in sys.argv:
        scripts.update({k: (SPIKE_BASE, e) for k, e in SPIKE.items()})
    fail = [f"{k}: base fixture absent from the corpus" for k in missing]
    fail += [f"--only {k}: no such script" for k in only or () if k not in scripts]
    with tempfile.TemporaryDirectory() as d:
        for name, (base, edits) in sorted(scripts.items()):
            if only and name not in only:
                continue
            problems = run(name, base, edits, Path(d))
            print(f"{name}: {'FAIL ' + '; '.join(problems) if problems else 'PASS'}")
            fail += [f"{name}: {p}" for p in problems]
    if fail:
        print("FAIL")
        for x in fail:
            print("  -", x)
        sys.exit(1)
    print("PASS")


if __name__ == "__main__":
    main()
