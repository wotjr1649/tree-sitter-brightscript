"""Discriminating controls for the strict maintenance comparator; no native process."""
import copy
import json
from pathlib import Path

import check_maintenance as m

def main():
    old = {n:(m.ROOT/n).read_bytes() for n in m.COMPONENTS}
    # The same controls work before and after the metadata bump.
    if b".patch_version = 1" in old["src/parser.c"]:
        old["src/parser.c"] = old["src/parser.c"].replace(b".patch_version = 1", b".patch_version = 0")
    for n, pointers in m.POINTERS.items():
        value = m.unique_json(old[n])
        for pointer in pointers:
            x = value
            for k in pointer[:-1]: x = x[k]
            x[pointer[-1]] = "0.1.0"
        old[n] = json.dumps(value).encode()
    new = copy.deepcopy(old)
    new["src/parser.c"] = old["src/parser.c"].replace(m.METADATA, m.METADATA.replace(b".patch_version = 0", b".patch_version = 1"))
    for n, pointers in m.POINTERS.items():
        value = m.unique_json(new[n])
        for pointer in pointers:
            x = value
            for k in pointer[:-1]: x = x[k]
            x[pointer[-1]] = "0.1.1"
        new[n] = json.dumps(value).encode()
    assert len(m.compare(old,new)["changed"]) == 4
    mutants=[]
    for n in ("grammar.js","src/scanner.c","queries/highlights.scm","src/node-types.json","src/grammar.json","src/tree_sitter/parser.h"):
        t=copy.deepcopy(new);t[n]+=b" ";mutants.append((n,t))
    for name,before,after in (
        ("table",b"ts_parse_table",b"tx_parse_table"),
        ("table value",b"[ts_builtin_sym_end] = ACTIONS(1)",b"[ts_builtin_sym_end] = ACTIONS(2)"),
        ("scanner map",b"ts_external_scanner_symbol_map",b"tx_external_scanner_symbol_map"),
        ("scanner map value",b"[ts_external_token__recovery_run] = sym__recovery_run",b"[ts_external_token__recovery_run] = sym__recovery_newline"),
        ("ABI",b"#define LANGUAGE_VERSION 15",b"#define LANGUAGE_VERSION 14"),
        ("outside whitespace",b"#include",b" #include"),
        ("major",b".major_version = 0",b".major_version = 1"),
        ("missing metadata",b".metadata = {",b".removed_metadata = {"),
        ("duplicate metadata",b".metadata = {",b".metadata = {}, .metadata = {")):
        assert before in new["src/parser.c"], name
        t=copy.deepcopy(new);t["src/parser.c"]=t["src/parser.c"].replace(before,after,1);mutants.append((name,t))
    t=copy.deepcopy(new);j=m.unique_json(t["package.json"]);j["private"]=False;t["package.json"]=json.dumps(j).encode();mutants.append(("private",t))
    t=copy.deepcopy(new);j=m.unique_json(t["package.json"]);j["private"]=1;t["package.json"]=json.dumps(j).encode();mutants.append(("private JSON type",t))
    t=copy.deepcopy(new);j=m.unique_json(t["tree-sitter.json"]);j["bindings"]["c"]=0;t["tree-sitter.json"]=json.dumps(j).encode();mutants.append(("binding JSON type",t))
    t=copy.deepcopy(new);assert b'"private": true' in t["package.json"]
    t["package.json"]=t["package.json"].replace(b'"private": true',b'"private":  true',1);mutants.append(("JSON whitespace",t))
    t=copy.deepcopy(new);j=m.unique_json(t["package.json"])
    t["package.json"]=json.dumps(dict(reversed(list(j.items())))).encode();mutants.append(("JSON key order",t))
    t=copy.deepcopy(new);t["queries/highlights.scm"]=t["queries/highlights.scm"].replace(b"@keyword",b"@constant",1);mutants.append(("query capture",t))
    t=copy.deepcopy(new);nodes=m.unique_json(t["src/node-types.json"]);node=next(n for n in nodes if n.get("fields"))
    field=next(iter(node["fields"]));node["fields"][field+"_changed"]=node["fields"].pop(field)
    t["src/node-types.json"]=json.dumps(nodes).encode();mutants.append(("node field",t))
    t=copy.deepcopy(new);t["package.json"]=b'{"version":"0.1.1","version":"0.1.0"}';mutants.append(("duplicate JSON",t))
    for name,t in mutants:
        try:m.compare(old,t)
        except (ValueError,KeyError):pass
        else:raise AssertionError("accepted "+name)
    print(json.dumps({"assessment":"PASS","legal_version_only":1,"mutants_rejected":len(mutants)}))

if __name__ == "__main__":
    main()
