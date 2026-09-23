"""V0 generated-artifact checks (ADR-0002; validation.md V0 checklist item 6).

Usage: python scripts/check_generated.py [--no-regenerate]

1. The generator is pinned exactly (package.json, lockfile, installed CLI version).
2. The installed CLI binary's SHA-256 equals the decompressed release asset
   recorded for this platform in docs/provenance/upstream-sources.md; the
   binary is not run before this holds (scripts/tscli.py `verify`, the check
   every script's CLI run passes through).
3. No external scanner exists (ADR-0005), and src/ holds only the files the
   generator writes.
4. Unless --no-regenerate: `tree-sitter generate --abi 15` run twice reproduces
   every file under src/ byte for byte (drift and determinism).
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

if (SRC / "scanner.c").exists():
    fail.append("src/scanner.c exists without an accepted scanner ADR (ADR-0005)")
GENERATED = {"parser.c", "grammar.json", "node-types.json", "tree_sitter/alloc.h", "tree_sitter/array.h",
             "tree_sitter/parser.h"}
if stray := sorted({p.relative_to(SRC).as_posix() for p in SRC.rglob("*") if p.is_file()} - GENERATED):
    fail.append(f"src/ holds files the generator does not write: {stray}")
if re.search(r"^\s*externals\s*:", (ROOT / "grammar.js").read_text(encoding="utf-8"), re.M):
    fail.append("grammar.js declares externals (ADR-0005)")


def snapshot():
    return {p.relative_to(SRC).as_posix(): p.read_bytes() for p in sorted(SRC.rglob("*")) if p.is_file()}


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

print(f"generator: {version}; binary {asset} {digest}")
if fail:
    print("FAIL")
    for x in fail:
        print("  -", x)
    sys.exit(1)
print("PASS")
