"""V0 static checks (docs/validation/validation.md, V0 checklist 1-5).

Usage: python scripts/check_v0.py
Checklist item 6 (regeneration drift, no scanner) is scripts/check_generated.py.
Stdlib only; exits non-zero on any failure.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ("_ref/", "docs/prompts/", "docs/plans/", "artifacts/", ".work/")
GENERATED = ("src/parser.c", "src/grammar.json", "src/node-types.json",
             "src/tree_sitter/parser.h", "src/tree_sitter/alloc.h", "src/tree_sitter/array.h")
fail = []


def git(*args):
    out = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    return [line for line in out.stdout.split("\n") if line]


tracked = set(git("ls-files"))
staged = set(git("diff", "--cached", "--name-only"))
untracked = set(git("ls-files", "--others", "--exclude-standard"))
files = sorted(tracked | staged | untracked)

# 1. No local-only content tracked, staged or left unignored.
for f in files:
    if f.startswith(LOCAL):
        fail.append(f"local-only path tracked/staged/unignored: {f}")

# 2. Local-only paths are ignored; generated sources and the lockfile are not.
for p in LOCAL:
    if not git("check-ignore", "--no-index", p + "probe"):
        fail.append(f"not ignored: {p}")
for p in GENERATED + ("package-lock.json",):
    if git("check-ignore", "--no-index", p):
        fail.append(f"ignored but must be tracked: {p}")
    elif (ROOT / p).exists() and p not in tracked | staged:
        fail.append(f"generated/lock file exists but is not tracked or staged: {p}")

# 3. Relative Markdown links and anchors resolve.
def slug(heading):
    h = re.sub(r"[`*_]", "", heading.strip().lower())
    h = re.sub(r"[^\w\- ]", "", h)
    return h.replace(" ", "-")


existing = [f for f in files if (ROOT / f).is_file()]
anchors = {}
for f in existing:
    if f.endswith(".md"):
        text = (ROOT / f).read_text(encoding="utf-8")
        anchors[f] = {slug(m.group(1)) for m in re.finditer(r"^#+ (.+)$", text, re.M)}
for f in anchors:
    text = re.sub(r"```.*?```", "", (ROOT / f).read_text(encoding="utf-8"), flags=re.S)
    for m in re.finditer(r"\]\(([^)\s]+)\)", text):
        target = m.group(1)
        if re.match(r"[a-z]+:", target):
            continue
        path, _, frag = target.partition("#")
        dest = ((ROOT / f).parent / path).resolve() if path else (ROOT / f).resolve()
        if not dest.exists():
            fail.append(f"{f}: broken link {target}")
        elif frag:
            rel = dest.relative_to(ROOT).as_posix()
            if rel in anchors and frag not in anchors[rel]:
                fail.append(f"{f}: broken anchor {target}")

# 4. License metadata is MIT everywhere it appears; versions agree.
if not (ROOT / "LICENSE").read_text(encoding="utf-8").startswith("MIT License"):
    fail.append("LICENSE is not the MIT License")
pkg = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
ts = json.loads((ROOT / "tree-sitter.json").read_text(encoding="utf-8"))
lock = json.loads((ROOT / "package-lock.json").read_text(encoding="utf-8"))
for where, value in (("package.json", pkg.get("license")),
                     ("tree-sitter.json", ts["metadata"].get("license")),
                     ("package-lock.json", lock["packages"][""].get("license"))):
    if value != "MIT":
        fail.append(f"{where}: license {value!r} is not MIT")
if pkg.get("version") != ts["metadata"]["version"]:
    fail.append(f"version mismatch: package.json {pkg.get('version')} vs tree-sitter.json {ts['metadata']['version']}")
if any(ts.get("bindings", {}).values()):
    fail.append("tree-sitter.json enables a language binding (architecture: none initially)")

# 5. No CR bytes and a final newline, except paths whose `text` attribute is unset
#    (byte fixtures). Generator-owned files are exempt from the final-newline rule;
#    item 6 checks them byte for byte against regeneration instead.
out = subprocess.run(["git", "check-attr", "-z", "--stdin", "text"], cwd=ROOT,
                     input="\0".join(existing).encode("utf-8"), capture_output=True).stdout.decode("utf-8")
parts = out.split("\0")
binary = {parts[i] for i in range(0, len(parts) - 2, 3) if parts[i + 2] == "unset"}
for f in existing:
    if f in binary:
        continue
    data = (ROOT / f).read_bytes()
    if b"\r" in data:
        fail.append(f"CR byte in {f}")
    if data and not data.endswith(b"\n") and f not in GENERATED:
        fail.append(f"no final newline in {f}")

print(f"files checked: {len(existing)} (byte-exempt: {len(binary)})")
if fail:
    print("FAIL")
    for x in fail:
        print("  -", x)
    sys.exit(1)
print("PASS")
