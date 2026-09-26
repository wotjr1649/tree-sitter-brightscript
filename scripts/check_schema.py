"""Schema reconciliation (WP17): docs/specs/tree-schema.md vs src/node-types.json.

Usage: python scripts/check_schema.py [--print-catalogue]

1. Planned schema: every planned node, supertype, field (name, named and
   anonymous types, optional/multiple) and unnamed-children entry equals the
   generated node-types.json, and no unplanned public node exists. Extras are
   never listed as children in node-types.json, so a planned `comment` child
   is not compared.
2. Spelling table: every token named in its "recoverable from" column (and,
   for an operator token, every spelling) is a node type in node-types.json.
3. Catalogue: the "Catalogue" section equals the table generated from
   node-types.json (--print-catalogue prints it). Stdlib only.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs/specs/tree-schema.md"
EXTRAS = {"comment"}
fail = []


def section(text, heading):
    m = re.search(rf"^(#+) {re.escape(heading)}\s*$", text, re.M)
    rest = text[m.end():]
    n = re.search(rf"^#{{1,{len(m.group(1))}}} ", rest, re.M)
    return rest[: n.start()] if n else rest


def rows(block):
    lines = [l for l in block.splitlines() if l.startswith("|")][2:]
    return [[c.strip() for c in l.strip().split("|")[1:-1]] for l in lines]


def mult(marker):
    return {"": (False, True), "?": (False, False), "*": (True, False), "+": (True, True)}[marker]


nt = json.loads((ROOT / "src/node-types.json").read_text(encoding="utf-8"))
actual = {n["type"]: n for n in nt if n["named"]}
supertypes = {k: sorted(s["type"] for s in v["subtypes"]) for k, v in actual.items() if "subtypes" in v}
nodes = {k: v for k, v in actual.items() if k not in supertypes}
doc = DOC.read_text(encoding="utf-8")
planned = section(doc, "Planned public schema")

# Supertypes.
for name, subs, *_ in rows(section(planned, "Supertypes")):
    name = name.strip("`")
    want = sorted(re.findall(r"`([a-z_]+)`", subs))
    if supertypes.get(name) != want:
        fail.append(f"supertype {name}: planned {want} != generated {supertypes.get(name)}")
if len(rows(section(planned, "Supertypes"))) != len(supertypes):
    fail.append("supertype count differs")

# Nodes, fields and unnamed children.
known = set(nodes) | set(supertypes)
planned_nodes = set()
for cols in rows(section(planned, "Planned nodes")):
    names = re.findall(r"`([a-z_]+)`", cols[0])
    planned_nodes |= set(names)
    fields = {}
    for fname, spec, marker in re.findall(r"`([a-z_]+): ([^`]+)`([?*+]?)", cols[1]):
        tokens = spec.replace(",", " ").split()
        # `or` separates named types; in an operator list it is the operator.
        if any(t.rstrip("?*+") in known for t in tokens):
            tokens = [t for t in tokens if t != "or"]
        # A trailing ? * + is a multiplicity marker only on a named type (`++` is an operator).
        inner = [t[-1] if t[-1] in "?*+" and t[:-1] in known else "" for t in tokens]
        tokens = [t[:-1] if m else t for t, m in zip(tokens, inner)]
        if any(inner):
            multiple = any(m in "*+" for m in inner if m)
            required = not all(m in "?*" for m in inner)
        else:
            multiple, required = mult(marker)
        fields[fname] = (sorted(t for t in tokens if t in known),
                         sorted(t for t in tokens if t not in known), multiple, required)
    # Unnamed children: every backticked type in the cell, with one multiplicity marker after the last.
    children = None
    kinds = [k for k in re.findall(r"`([a-z_]+)`", cols[2]) if k not in EXTRAS]
    m = re.search(r"`([?*+]?)(?!.*`)", cols[2])
    if kinds:
        children = (sorted(kinds), *mult(m.group(1) if m else ""))
    for name in names:
        node = nodes.get(name)
        if node is None:
            fail.append(f"planned node missing from node-types.json: {name}")
            continue
        got = {}
        for f, v in node.get("fields", {}).items():
            got[f] = (sorted(t["type"] for t in v["types"] if t["named"]),
                      sorted(t["type"] for t in v["types"] if not t["named"]), v["multiple"], v["required"])
        for f in sorted(set(got) | set(fields)):
            if got.get(f) != fields.get(f):
                fail.append(f"{name}.{f}: planned {fields.get(f)} != generated {got.get(f)}")
        c = node.get("children")
        got_children = (sorted(t["type"] for t in c["types"]), c["multiple"], c["required"]) if c else None
        if got_children != children:
            fail.append(f"{name} children: planned {children} != generated {got_children}")
for extra in sorted(set(nodes) - planned_nodes):
    fail.append(f"unplanned public node: {extra}")
planned_fields = [c[0].strip("`") for c in rows(section(planned, "Fields"))]
actual_fields = sorted({f for n in nodes.values() for f in n.get("fields", {})})
if sorted(planned_fields) != actual_fields:
    fail.append(f"field names: planned {sorted(planned_fields)} != generated {actual_fields}")

# Spelling table: every token the recoverable-from column names (and, for an
# operator token, every spelling) is a node type in node-types.json.
anonymous = {n["type"] for n in nt if not n["named"]}
spelling_tokens = 0
for construct, spellings, _, recoverable in rows(section(planned, "Spelling and normalization")):
    if "anonymous" not in recoverable:
        continue
    names = re.findall(r"`([^`]+)`", recoverable)
    if "operator token" in recoverable:
        names += re.findall(r"`([^`]+)`", spellings)
    for name in names:
        spelling_tokens += 1
        if name not in anonymous and name not in known:
            fail.append(f"spelling table ({construct}): `{name}` is not a node type in node-types.json")


# Catalogue generated from node-types.json.
def fmt_types(v):
    return " \\| ".join(t["type"] if t["named"] else f'"{t["type"]}"' for t in v["types"])


def catalogue():
    out = ["| Node | Fields | Children |", "|---|---|---|"]
    for name in sorted(nodes):
        n = nodes[name]
        fields = ", ".join(
            f"`{f}{('+' if v['required'] else '*') if v['multiple'] else ('' if v['required'] else '?')}: {fmt_types(v)}`"
            for f, v in sorted(n.get("fields", {}).items())) or "—"
        c = n.get("children")
        kids = (f"`{fmt_types(c)}`{('+' if c['required'] else '*') if c['multiple'] else ''}" if c else "—")
        kind = " (extra)" if n.get("extra") else ""
        out.append(f"| `{name}`{kind} | {fields} | {kids} |")
    out.append("")
    for name in sorted(supertypes):
        out.append(f"Supertype `{name}`: " + ", ".join(f"`{s}`" for s in supertypes[name]) + ".")
        out.append("")
    out.append(f"Counts: {len(nodes)} named node types, {len(supertypes)} supertypes, "
               f"{len(actual_fields)} field names.")
    return "\n".join(out)


if "--print-catalogue" in sys.argv:
    sys.stdout.buffer.write((catalogue() + "\n").encode("utf-8"))
    sys.exit(0)
if catalogue() not in section(doc, "Catalogue"):
    fail.append("the Catalogue section differs from node-types.json (run with --print-catalogue)")

print(f"generated: {len(nodes)} named node types, {len(supertypes)} supertypes, {len(actual_fields)} fields; "
      f"planned: {len(planned_nodes)} nodes, {len(planned_fields)} fields; spelling-table tokens: {spelling_tokens}")
if fail:
    print("FAIL")
    for x in fail:
        print("  -", x)
    sys.exit(1)
print("PASS")
