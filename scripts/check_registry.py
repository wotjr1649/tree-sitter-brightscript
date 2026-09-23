"""Registry, corpus and fixture-catalogue consistency.

Usage: python scripts/check_registry.py [--complete]

Checks docs/specs/language-conformance.md (IDs, statuses, evidence, fixture
naming, coverage claims, summary), the requirement-schema mapping in
docs/specs/tree-schema.md, the fixture catalogue in
docs/validation/workload-matrix.md, and test/corpus/**:
  - every corpus test is a registry fixture and appears once;
  - its input bytes equal the catalogue input exactly;
  - where the catalogue states a complete tree, the corpus expectation equals it;
  - `:error` only on negative, recovery and active-KL fixtures; `:skip` only under a KL;
  - a `covered` requirement has a rule and all of its fixtures present.
--complete additionally requires every registry fixture to be in the corpus.
The research-inventory and ambiguity reconciliations need the local `_ref/`
workspace and are skipped when it is absent (CI). Stdlib only.
"""
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

from corpus import CORPUS, read_corpus

ROOT = Path(__file__).resolve().parents[1]
REG = ROOT / "docs/specs/language-conformance.md"
VAL = ROOT / "docs/validation/validation.md"
WM = ROOT / "docs/validation/workload-matrix.md"
TS = ROOT / "docs/specs/tree-schema.md"
AMB = ROOT / "_ref/normative/roku-docs/notes/ambiguities.md"
INV = ROOT / "_ref/normative/roku-docs/notes/syntax-inventory.md"

AREAS = ["LEX", "LIT", "TYPE", "EXP", "STMT", "FUNC", "ARRAY", "AA", "ERR", "COND"]
STATUSES = ["documented", "provisional", "tolerated", "unresolved", "invalid", "out-of-scope", "retired"]
COVERAGE = ["none", "partial", "covered"]
FIX_RE = re.compile(r"`(BS-[A-Z]+-\d{3}): ([^`]+)`")
fail = []


def cells(line):
    return [c.strip() for c in line.strip().split("|")[1:-1]]


def section(text, heading):
    """Body of a heading up to the next heading of the same or a higher level."""
    m = re.search(rf"^(#+) {re.escape(heading)}\s*$", text, re.M)
    if not m:
        return ""
    rest = text[m.end():]
    n = re.search(rf"^#{{1,{len(m.group(1))}}} ", rest, re.M)
    return rest[: n.start()] if n else rest


def table_rows(block):
    return [cells(r) for r in [l for l in block.splitlines() if l.startswith("|")][2:]]


def sexp(text):
    """Normalise an S-expression as the Tree-sitter test runner does."""
    text = "\n".join(l for l in text.splitlines() if not l.strip().startswith(";"))
    return re.sub(r"\s+\)", ")", re.sub(r"\s+", " ", text)).strip()


# ---------------------------------------------------------------- registry
text = REG.read_text(encoding="utf-8")
rows, fixtures = {}, {}  # fixtures: name -> (id, "positive" | "negative/recovery")
status_count = defaultdict(Counter)
for area in AREAS:
    block = section(text, area)
    if not block:
        fail.append(f"missing registry section {area}")
        continue
    expected = 1
    for c in table_rows(block):
        if len(c) != 11:
            fail.append(f"{area}: row has {len(c)} cells: {c[:1]}")
            continue
        rid, req, ev, since, st, gram, pos, neg, cov, kl, notes = c
        if not re.fullmatch(rf"BS-{area}-\d{{3}}", rid):
            fail.append(f"bad id {rid} in {area}")
        if int(rid[-3:]) != expected:
            fail.append(f"{rid}: expected BS-{area}-{expected:03d} (allocation order)")
        expected = int(rid[-3:]) + 1
        if rid in rows:
            fail.append(f"duplicate id {rid}")
        rows[rid] = dict(req=req, ev=ev, st=st, gram=gram, pos=pos, neg=neg, cov=cov, kl=kl)
        status_count[area][st] += 1
        if st not in STATUSES:
            fail.append(f"{rid}: bad status {st}")
        if cov not in COVERAGE:
            fail.append(f"{rid}: bad coverage {cov}")
        if not ev:
            fail.append(f"{rid}: empty evidence")
        if not re.fullmatch(r"baseline|unknown|\d+(\.\d+)?", since):
            fail.append(f"{rid}: bad since {since}")
        pos_f, neg_f = FIX_RE.findall(pos), FIX_RE.findall(neg)
        for fid, name in pos_f + neg_f:
            if fid != rid:
                fail.append(f"{rid}: fixture cites {fid}")
            full = f"{fid}: {name}"
            if full in fixtures:
                fail.append(f"duplicate fixture {full}")
            fixtures[full] = (rid, "positive" if (fid, name) in pos_f else "negative/recovery")
        rows[rid]["fixtures"] = [f"{i}: {n}" for i, n in pos_f + neg_f]
        keys = set(re.findall(r"\b(LR|SS|PS|EVT|RW|CC|EH|RN|CA|RF)\b", ev))
        has_rule = not gram.startswith("none")
        if st in ("documented", "provisional", "tolerated"):
            if not has_rule or not pos_f:
                fail.append(f"{rid}: {st} needs a grammar rule and a positive fixture")
        if st == "documented" and not keys:
            fail.append(f"{rid}: documented without a Level 1 page key")
        if st == "invalid" and (not keys or not neg_f or pos_f):
            fail.append(f"{rid}: invalid needs Level 1 evidence and only negative fixtures")
        if st == "unresolved" and (pos_f or neg_f or has_rule):
            fail.append(f"{rid}: unresolved must have no rule and no corpus fixture")
        if st == "out-of-scope" and (has_rule or neg_f or (pos_f and "(guard)" not in pos)):
            fail.append(f"{rid}: out-of-scope must have no rule and only guard fixtures")
        if st == "tolerated" and (("Level 4" not in ev and "Level 2" not in ev) or "Non-normative" not in req):
            fail.append(f"{rid}: tolerated needs L2/L4 evidence and a non-normative mark")
        if cov == "covered":
            if st not in ("documented", "provisional", "tolerated", "invalid"):
                fail.append(f"{rid}: {st} row cannot be covered")
            if gram.startswith("planned:") or not has_rule:
                fail.append(f"{rid}: covered but its grammar rule is still planned or none")

# Registry summary table.
tot = Counter()
cols = ["documented", "provisional", "tolerated", "unresolved", "invalid", "out-of-scope"]
for c in table_rows(section(text, "Registry summary")):
    area = c[0].strip("*")
    nums = [int(x.strip("*")) for x in c[1:]]
    if area == "Total":
        if nums != [len(rows)] + [tot[s] for s in cols]:
            fail.append(f"registry summary total {nums} != actual")
        continue
    if nums != [sum(status_count[area].values())] + [status_count[area][s] for s in cols]:
        fail.append(f"registry summary {area} {nums} != actual")
    for s in cols:
        tot[s] += status_count[area][s]

# Local-only reconciliations.
if AMB.exists() and INV.exists():
    inv_ids = re.findall(r"^\| ((?:LEX|LIT|TYP|EXP|ASN|STM|FUN|ARR|ERR|CC|LINE)-\d\d) \|",
                         INV.read_text(encoding="utf-8"), re.M)
    inv_rows = [c for c in table_rows(section(text, "Research inventory → requirements"))
                if len(c) == 3 and re.fullmatch(r"[A-Z]+-\d\d", c[0])]
    if sorted(c[0] for c in inv_rows) != sorted(inv_ids):
        fail.append("research inventory reconciliation does not match _ref inventory")
    for c in inv_rows:
        for ref in re.findall(r"BS-[A-Z]+-\d{3}", c[2]):
            if ref not in rows:
                fail.append(f"inventory {c[0]} cites unknown {ref}")
    amb_ids = set(re.findall(r"^## (AMB-\d\d)", AMB.read_text(encoding="utf-8"), re.M))
    amb_rows = [c[0] for c in table_rows(section(text, "Ambiguities → dispositions")) if c and c[0].startswith("AMB-")]
    if sorted(amb_rows) != sorted(amb_ids):
        fail.append("ambiguity reconciliation does not match _ref ambiguities")
    reconciliation = f"inventory {len(inv_rows)}, ambiguities {len(amb_rows)}"
else:
    reconciliation = "skipped (_ref/ absent)"

# Known limitations: only active KLs may carry :error on positive fixtures or :skip.
kl_fixtures = set()
kl_defined = set()
for c in table_rows(section(VAL.read_text(encoding="utf-8"), "Failures and known limitations")):
    if len(c) == 5 and re.fullmatch(r"KL-\d{3}", c[0]):
        kl_defined.add(c[0])
        if c[1].startswith("active"):
            kl_fixtures |= {f"{i}: {n}" for i, n in FIX_RE.findall(c[4])}
for rid, r in rows.items():
    for k in re.findall(r"\bKL-\d{3}\b", r["kl"]):
        if k not in kl_defined:
            fail.append(f"{rid}: {k} not defined in validation.md")

# ------------------------------------------------------------ tree schema
ts = TS.read_text(encoding="utf-8")
need = {r for r, v in rows.items() if v["st"] in ("documented", "provisional", "tolerated")}
mrows = [c for c in table_rows(section(ts, "Requirement ↔ schema mapping")) if len(c) == 3 and c[0].startswith("BS-")]
if sorted(c[0] for c in mrows) != sorted(need):
    fail.append("requirement-schema mapping rows differ from documented/provisional/tolerated requirements")
cat = Counter(c[1] for c in mrows)
m = re.search(r"Mapped: (\d+) \(S (\d+), N (\d+), L (\d+)\)", ts)
if not m or [int(x) for x in m.groups()] != [len(mrows), cat["S"], cat["N"], cat["L"]]:
    fail.append(f"schema mapping counts line wrong; actual {len(mrows)} {dict(cat)}")

# -------------------------------------------------------------- catalogue
def decode(cell):
    if cell == "(empty)":
        return b""
    m = re.fullmatch(r"`([^`]*)`", cell)
    if not m:
        return None
    s = m.group(1).replace("↵", "\n").replace("␍", "\r").replace("⇥", "\t")
    return s.replace("‹BOM›", "﻿").encode("utf-8")


def full_tree(cell):
    m = re.fullmatch(r"(?:\(token\) )?`(\(source_file[^`]*)`", cell)
    return sexp(m.group(1)) if m and "…" not in m.group(1) else None


# ADR-0004 status line decides which literal-false column applies.
adr4 = (ROOT / "docs/design/decisions/ADR-0004-conditional-compilation-representation.md").read_text(encoding="utf-8")
status = re.search(r"^Status: (.+)$", adr4, re.M).group(1)
SPIKE = "V1" if "adopted (V1)" in status else "V2" if "adopted (V2)" in status else "FAIL" if "failed" in status else None
if SPIKE is None:
    fail.append(f"ADR-0004 status does not state the spike outcome: {status}")
catalogue = {}  # name -> dict(input=bytes, trees=set|None, error=bool)
for c in table_rows(section(WM.read_text(encoding="utf-8"), "Corpus fixture catalogue")):
    m = re.fullmatch(r"`(BS-[A-Z]+-\d{3}: [^`]+)`", c[0]) if c else None
    if not m:
        continue
    name, data = m.group(1), decode(c[1])
    if data is None:
        fail.append(f"catalogue input not decodable: {name}")
        continue
    entry = dict(input=data, trees=None, error=len(c) == 2)
    if len(c) == 3:
        entry["error"] = c[2] == "`:error`"
        tree = full_tree(c[2])
        entry["trees"] = {tree} if tree else None
    elif len(c) == 4:  # literal-false table: the column of the ADR-0004 spike outcome
        cell = c[3] if SPIKE == "FAIL" else c[2]
        if cell == "same as PASS":
            cell = c[2]
        tree = full_tree(cell)
        if tree and SPIKE == "V2":
            tree = sexp(re.sub(r"\(inactive_text( \(comment\))+\)", "(inactive_text)", tree))
        entry["trees"] = {tree} if tree else None
        entry["error"] = cell.startswith("`:error`")
        entry["error_allowed"] = entry["error"]
    if name in catalogue:
        fail.append(f"duplicate catalogue row {name}")
    catalogue[name] = entry
if set(catalogue) != set(fixtures):
    fail.append(f"catalogue vs registry: missing {sorted(set(fixtures) - set(catalogue))} "
                f"extra {sorted(set(catalogue) - set(fixtures))}")

# ----------------------------------------------------------------- corpus
corpus, duplicates = read_corpus(CORPUS) if CORPUS.exists() else ({}, [])
for name in duplicates:
    fail.append(f"corpus test appears twice: {name}")
for name, t in corpus.items():
    if t["input"] is None:
        fail.append(f"{t['file']}: {name}: no divider")
        t["input"], t["expected"] = b"", ""
    t["tree"] = sexp(t["expected"])

for name, t in corpus.items():
    if name not in fixtures:
        fail.append(f"corpus test is not a registry fixture: {name} ({t['file']})")
        continue
    rid, kind = fixtures[name]
    entry = catalogue.get(name)
    if entry and t["input"] != entry["input"]:
        fail.append(f"input differs from catalogue: {name}\n      corpus    {t['input']!r}\n      catalogue {entry['input']!r}")
    has_error, skipped = ":error" in t["attrs"], ":skip" in t["attrs"]
    if skipped and name not in kl_fixtures:
        fail.append(f":skip without an active KL: {name}")
    if kind == "negative/recovery" and not has_error:
        fail.append(f"negative/recovery fixture lacks :error: {name}")
    if kind == "positive" and has_error and name not in kl_fixtures:
        if not (entry and entry.get("error_allowed")):
            fail.append(f"positive fixture asserts :error without an active KL: {name}")
    if entry and entry["error"] and not has_error:
        fail.append(f"catalogue expects :error: {name}")
    if has_error and t["tree"]:
        fail.append(f":error fixture has an expected tree: {name}")
    if not has_error and entry and entry["trees"] and t["tree"] not in entry["trees"]:
        fail.append(f"expected tree differs from catalogue: {name}\n      corpus    {t['tree']}\n      catalogue {sorted(entry['trees'])}")

missing = sorted(set(fixtures) - set(corpus))
for rid, r in rows.items():
    if r["cov"] == "covered":
        absent = [f for f in r["fixtures"] if f not in corpus or ":skip" in corpus[f]["attrs"]]
        if absent:
            fail.append(f"{rid}: covered but fixtures absent or skipped: {absent}")
if "--complete" in sys.argv and missing:
    fail.append(f"{len(missing)} registry fixtures missing from the corpus: {missing}")

covered = Counter(r["cov"] for r in rows.values())
print(f"requirements: {len(rows)} {dict(sum(status_count.values(), Counter()))}")
print(f"coverage: {dict(covered)}")
print(f"registry fixtures: {len(fixtures)} {dict(Counter(k for _, k in fixtures.values()))}; "
      f"catalogue rows: {len(catalogue)}")
print(f"corpus tests: {len(corpus)}; registry fixtures missing from corpus: {len(missing)}")
print(f"schema mapping: {len(mrows)} {dict(cat)}; reconciliation: {reconciliation}")
if fail:
    print("FAIL")
    for x in fail:
        print("  -", x)
    sys.exit(1)
print("PASS")
