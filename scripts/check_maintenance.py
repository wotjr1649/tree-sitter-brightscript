"""Strict version-only component comparison for ADR-0009.
Usage: python scripts/check_maintenance.py [--baseline=v0.1.0]
No parser bytes are rewritten. JSON comparison permits only the enumerated pointers.
"""
import copy
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
COMPONENTS = ("grammar.js", "src/parser.c", "src/scanner.c", "src/grammar.json", "src/node-types.json",
              "src/tree_sitter/alloc.h", "src/tree_sitter/array.h", "src/tree_sitter/parser.h",
              "queries/highlights.scm", "tree-sitter.json", "package.json", "package-lock.json", "LICENSE")
POINTERS = {"package.json": (("version",),), "package-lock.json": (("version",), ("packages", "", "version")),
            "tree-sitter.json": (("metadata", "version"),)}
METADATA = b"    .metadata = {\n      .major_version = 0,\n      .minor_version = 1,\n      .patch_version = 0,\n    },"
LANGUAGE = b"const TSLanguage *tree_sitter_brightscript(void)"

def digest(data):
    return hashlib.sha256(data).hexdigest()

def unique_json(data):
    def pairs(values):
        out = {}
        for k, v in values:
            if k in out:
                raise ValueError("duplicate JSON key")
            out[k] = v
        return out
    return json.loads(data, object_pairs_hook=pairs)

def parser_delta(old, new):
    if old.count(METADATA) != 1 or len(re.findall(rb"\.metadata\s*=", old)) != 1:
        return False
    if old.find(METADATA) < old.find(LANGUAGE) or LANGUAGE not in old:
        return False
    return new == old.replace(METADATA, METADATA.replace(b".patch_version = 0", b".patch_version = 1"), 1)

def compare(old, new):
    if set(old) != set(COMPONENTS) or set(new) != set(COMPONENTS):
        raise ValueError("component inventory differs")
    changed = []
    for name in COMPONENTS:
        a, b = old[name], new[name]
        if name == "src/parser.c":
            if not parser_delta(a, b): raise ValueError("parser delta outside unique version metadata")
        elif name in POINTERS:
            before, after = unique_json(a), unique_json(b)
            normalized = copy.deepcopy(after)
            for pointer in POINTERS[name]:
                x, y = before, normalized
                for key in pointer[:-1]: x, y = x[key], y[key]
                key = pointer[-1]
                if x[key] != "0.1.0" or y[key] != "0.1.1": raise ValueError("unexpected version")
                y[key] = x[key]
            # JSON booleans and numbers must stay distinct (Python True == 1).
            if json.dumps(normalized, sort_keys=True, allow_nan=False) != json.dumps(before, sort_keys=True, allow_nan=False):
                raise ValueError("unexpected JSON pointer delta: " + name)
        elif a != b:
            raise ValueError("frozen component differs: " + name)
        if a != b: changed.append(name)
    return {"changed":changed,"old_components":{n:digest(old[n]) for n in COMPONENTS},
            "candidate_components":{n:digest(new[n]) for n in COMPONENTS},
            "K0":digest("".join(f"{digest(old[n])}  {n}\n" for n in COMPONENTS).encode()),
            "K1":digest("".join(f"{digest(new[n])}  {n}\n" for n in COMPONENTS).encode()),
            "algorithm":"SHA256 of ordered '<component sha256>  <path>\\n' UTF-8 lines",
            "claim":"observed exact metadata-only source delta; not universal behavioural equivalence"}

def main():
    base = next((x.split("=",1)[1] for x in sys.argv[1:] if x.startswith("--baseline=")), "v0.1.0")
    if not re.fullmatch(r"[A-Za-z0-9._/-]+", base): raise ValueError("invalid ref")
    old = {}
    for name in COMPONENTS:
        r = subprocess.run(["git", "show", f"{base}:{name}"], cwd=ROOT, capture_output=True, check=True, timeout=30)
        old[name] = r.stdout
    result = compare(old, {n:(ROOT/n).read_bytes() for n in COMPONENTS})
    print(json.dumps(result, indent=2))
    return 0

if __name__ == "__main__":
    sys.exit(main())
