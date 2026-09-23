"""V0 generated-artifact checks (ADR-0002; validation.md V0 checklist item 6).

Usage: python scripts/check_generated.py [--no-regenerate]

1. The generator is pinned exactly (package.json, lockfile, installed CLI version).
2. The installed CLI binary's SHA-256 equals the decompressed release asset
   recorded for this platform in docs/provenance/upstream-sources.md; the
   binary is not run before this holds.
3. No external scanner exists (ADR-0005), and src/ holds only the files the
   generator writes.
4. Unless --no-regenerate: `tree-sitter generate --abi 15` run twice reproduces
   every file under src/ byte for byte (drift and determinism).
Stdlib only; exits non-zero on any failure.
"""
import hashlib
import json
import platform
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
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

exe = ROOT / "node_modules/tree-sitter-cli" / ("tree-sitter.exe" if sys.platform == "win32" else "tree-sitter")
if not exe.is_file():
    print(f"FAIL\n  - generator binary missing: {exe} (run npm ci)")
    sys.exit(1)

os_name = {"win32": "windows", "linux": "linux", "darwin": "macos"}.get(sys.platform, sys.platform)
arch = {"amd64": "x64", "x86_64": "x64", "arm64": "arm64", "aarch64": "arm64"}.get(platform.machine().lower(), platform.machine().lower())
asset = f"tree-sitter-{os_name}-{arch}"
sources = (ROOT / "docs/provenance/upstream-sources.md").read_text(encoding="utf-8")
recorded = {m.group(1): m.group(3) for m in re.finditer(
    r"\| `(tree-sitter-[a-z0-9]+-[a-z0-9]+)\.gz` \| `([0-9a-f]{64})` \| `([0-9a-f]{64})` \|", sources)}
digest = hashlib.sha256(exe.read_bytes()).hexdigest()
if asset not in recorded:
    fail.append(f"no recorded binary identity for {asset} in upstream-sources.md (installed SHA-256 {digest})")
elif recorded[asset] != digest:
    fail.append(f"{asset}: installed binary SHA-256 {digest} != recorded {recorded[asset]}")
if recorded.get(asset) != digest:
    print("FAIL (the binary was not run)")
    for x in fail:
        print("  -", x)
    sys.exit(1)
version = subprocess.run([str(exe), "--version"], capture_output=True, text=True).stdout.strip()
if version != f"tree-sitter {pinned}":
    fail.append(f"installed CLI reports {version!r}, pinned {pinned}")

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
        r = subprocess.run([str(exe), "generate", "--abi", "15"], cwd=ROOT, capture_output=True, text=True)
        if r.returncode:
            fail.append(f"generate failed: {r.stderr.strip()}")
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
