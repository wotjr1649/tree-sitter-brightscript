"""V0 generated-artifact checks (ADR-0002; validation.md V0 checklist item 6).

Usage: python scripts/check_generated.py [--no-regenerate]

1. The generator is pinned exactly (package.json, lockfile, installed CLI version).
2. The installed CLI binary's SHA-256 equals the decompressed release asset
   recorded for this platform in docs/provenance/upstream-sources.md; the
   binary is not run before this holds (scripts/tscli.py `verify`, the check
   every script's CLI run passes through).
3. src/ holds only the files the generator writes and the hand-written
   src/scanner.c, which exists exactly when grammar.js declares `externals` and
   ADR-0008 (the error-recovery scanner) is accepted. The scanner includes only
   tree_sitter/parser.h and tree_sitter/alloc.h (its one-byte state is allocated
   with the runtime's `ts_calloc`) and calls no other allocator and no printing,
   environment or file function (ADR-0008 decisions 5 and 6; a guard against
   regressions, not a proof).
4. Unless --no-regenerate: `tree-sitter generate --abi 15` run twice reproduces
   every generated file under src/ byte for byte (drift and determinism); the
   scanner is not generated and is hashed separately.
Stdlib only; exits non-zero on any failure.
"""
import hashlib
import json
import re
import sys

from tscli import ROOT, cli, verify

SRC = ROOT / "src"
fail = []

pkg = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
lock = json.loads((ROOT / "package-lock.json").read_text(encoding="utf-8"))
pinned = pkg.get("devDependencies", {}).get("tree-sitter-cli", "")
if not re.fullmatch(r"\d+\.\d+\.\d+", pinned):
    fail.append(f"tree-sitter-cli is not pinned to an exact version: {pinned!r}")
locked = lock["packages"].get("node_modules/tree-sitter-cli", {}).get("version")
if locked != pinned:
    fail.append(f"lockfile tree-sitter-cli {locked} != package.json {pinned}")

try:
    asset, digest, version = verify()
except RuntimeError as e:
    print("FAIL")
    for x in [*fail, str(e)]:
        print("  -", x)
    sys.exit(1)

GENERATED = {"parser.c", "grammar.json", "node-types.json", "tree_sitter/alloc.h", "tree_sitter/array.h",
             "tree_sitter/parser.h"}
SCANNER = SRC / "scanner.c"
ADR = ROOT / "docs/design/decisions/ADR-0008-error-recovery-scanner.md"
has_externals = bool(re.search(r"^\s*externals\s*:", (ROOT / "grammar.js").read_text(encoding="utf-8"), re.M))
if SCANNER.exists() != has_externals:
    fail.append("src/scanner.c and an `externals` list in grammar.js must exist together")
if SCANNER.exists():
    if not (ADR.is_file() and re.search(r"^Status: Accepted", ADR.read_text(encoding="utf-8"), re.M)):
        fail.append("src/scanner.c exists without the accepted ADR-0008")
    code = SCANNER.read_text(encoding="utf-8")
    if set(re.findall(r'^\s*#\s*include\s*[<"]([^>"]+)[>"]', code, re.M)) - {"tree_sitter/parser.h",
                                                                         "tree_sitter/alloc.h"}:
        fail.append("src/scanner.c includes something other than tree_sitter/parser.h and tree_sitter/alloc.h")
    if found := sorted(set(re.findall(r"\b(malloc|calloc|realloc|free|printf|fprintf|puts|getenv|fopen)\b", code))):
        fail.append(f"src/scanner.c calls functions ADR-0008 excludes: {found}")
allowed = GENERATED | ({"scanner.c"} if SCANNER.exists() else set())
if stray := sorted({p.relative_to(SRC).as_posix() for p in SRC.rglob("*") if p.is_file()} - allowed):
    fail.append(f"src/ holds files that are neither generated nor the scanner: {stray}")


def snapshot():
    return {p.relative_to(SRC).as_posix(): p.read_bytes() for p in sorted(SRC.rglob("*"))
            if p.is_file() and p.relative_to(SRC).as_posix() in GENERATED}


def diff(a, b):
    return sorted(k for k in a.keys() | b.keys() if a.get(k) != b.get(k))


if "--no-regenerate" not in sys.argv and not fail:
    before = snapshot()
    runs = []
    for _ in range(2):
        code, _, err = cli("generate", "--abi", "15", timeout=600)
        if code:
            fail.append(f"generate failed: {err.strip()}")
            break
        runs.append(snapshot())
    if len(runs) == 2:
        if d := diff(before, runs[0]):
            fail.append(f"drift: regeneration changed {d}")
        if d := diff(runs[0], runs[1]):
            fail.append(f"non-deterministic generation: {d}")
    for name, data in sorted(snapshot().items()):
        print(f"{hashlib.sha256(data).hexdigest()}  src/{name}")
if SCANNER.exists():
    print(f"{hashlib.sha256(SCANNER.read_bytes()).hexdigest()}  src/scanner.c (hand-written, ADR-0008)")

print(f"generator: {version}; binary {asset} {digest}")
if fail:
    print("FAIL")
    for x in fail:
        print("  -", x)
    sys.exit(1)
print("PASS")
