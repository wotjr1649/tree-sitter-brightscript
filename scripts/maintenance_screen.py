"""Finite Session 07 sources and independent expectations; no process launcher.

Native execution uses the existing qualification probe and supervisor. This
screen is not a replacement for corpus, full qualification, or Roku evidence.
"""
import hashlib
import json

OUTPUT_BYTES = 8 * 2**20
MAX_NODES = 100000


def sources():
    rows = []

    def add(case_id, text, ids, expected, named=None):
        data = text.encode("utf-8") if isinstance(text, str) else text
        if len(data) > 65536:
            raise ValueError("screen input too large")
        rows.append({"case_id": case_id, "data": data, "origin_bs_ids": ids,
                     "expected_class": expected, "expected_named": named,
                     "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data),
                     "operations": ["DUMP", "RUN_QUERY_ONLY", "TWO"], "parse_calls": 4})

    root = [("source_file", "-", None)]
    assign = root + [("assignment_statement", "-", None), ("identifier", "left", "x")]
    binop = [("binary_expression", "right", None), ("number", "left", "1"),
             ("binary_expression", "right", None), ("number", "left", "2"), ("number", "right", "3")]
    add("TEST-01-precedence", "x = 1 + 2 * 3\n", ["BS-EXP-013", "BS-EXP-014"], "VALID", assign + binop)
    add("TEST-01-power", "x = 1 ^ 2 ^ 3\n", ["BS-EXP-011"], "VALID", assign + binop)
    add("TEST-01-print", "print 1 + 2 * 3;\n", ["BS-STMT-024", "BS-STMT-026"], "VALID",
        root + [("print_statement", "-", None), ("binary_expression", "-", None),
                ("number", "left", "1"), ("binary_expression", "right", None),
                ("number", "left", "2"), ("number", "right", "3")])
    add("TEST-01-if", "if a then\nprint 1\nend if\n", ["BS-STMT-007"], "VALID",
        root + [("if_statement", "-", None), ("identifier", "condition", "a"), ("block", "consequence", None),
                ("print_statement", "-", None), ("number", "-", "1")])
    add("TEST-01-postfix", "x = a.b(1)[2]\n", ["BS-EXP-003", "BS-EXP-004", "BS-EXP-005"], "VALID",
        assign + [("index_expression", "right", None), ("call_expression", "object", None),
                  ("identifier", "object", "a"), ("identifier", "property", "b"),
                  ("argument_list", "arguments", None), ("number", "-", "1"), ("number", "index", "2")])
    add("TEST-01-attribute", "x = a@b\n", ["BS-EXP-006"], "VALID",
        assign + [("attribute_expression", "right", None), ("identifier", "object", "a"), ("identifier", "attribute", "b")])
    for i, token in enumerate(("&hff0000ff", "&h00ff00ff", "&h0000ffff")):
        add(f"TEST-01-hex-{i}", f"x = {token}\n", ["BS-LIT-006"], "VALID", assign + [("number", "right", token)])
    for name, source, rid in (
        ("optional-target", "a?[0] = 1\n", "BS-EXP-008"),
        ("optional-call", "f?(1)\n", "BS-EXP-009"),
        ("while-next", "while true\nprint 1\nnext\n", "BS-STMT-017"),
        ("catch-value", "try\nprint 1\ncatch 1\nend try\n", "BS-ERR-003"),
        ("const-number", "#const a = 4\n", "BS-COND-013")):
        add("TEST-01-" + name, source, [rid], "INVALID")
    # A unit is one punctuation character here; 15/16/17 is not the number
    # of multi-token '+f([)' repetitions in the historical safety replay.
    for size in (15, 16, 17):
        for tail_id, tail in (("eof", ""), ("lf", "\n"), ("crlf", "\r\n"),
                              ("closer", " end if\n"), ("rem", " REM note\n"),
                              ("suffix", "\nsub Kept()\nend sub\n")):
            add(f"TEST-03-{size}-{tail_id}", "x = ) " + "*" * size + tail, [], "RECOVERY")
    for depth in (1, 2, 3):
        for bad in (False, True):
            for double in (False, True):
                body = '{ key: ' * depth + ('"a" "b"' if bad else '"a"') + ' }' * depth
                text = "x = " + body + "\n" + ("z = )\n" if double else "") + "sub Kept()\nend sub\n"
                named = assign[:]
                if not bad and not double:
                    for level in range(depth):
                        named += [("associative_array_literal", "right" if level == 0 else "value", None),
                                  ("associative_array_entry", "-", None), ("identifier", "key", "key")]
                    named += [("string", "value", '"a"'), ("function_declaration", "-", None),
                              ("identifier", "name", "Kept"), ("parameter_list", "parameters", None),
                              ("block", "body", None)]
                add(f"UP-01-aa-{depth}-{int(bad)}-{int(double)}", text,
                    ["BS-AA-001", "BS-AA-002"], "RECOVERY" if bad or double else "VALID",
                    None if bad or double else named)
    for word in ("ifx", "rem1", "remark", "endforx", "while1", "functionx", "truex", "catcher", "_if"):
        add("UP-02-name-" + word, word + " = 1\n", ["BS-LEX-026", "BS-LEX-014"], "VALID",
            root + [("assignment_statement", "-", None), ("identifier", "left", word), ("number", "right", "1")])
    add("UP-02-rem-comment", "REM note\nx = 1\n", ["BS-LEX-013", "BS-LEX-014"], "VALID",
        root + [("comment", "-", "REM note"), ("assignment_statement", "-", None),
                ("identifier", "left", "x"), ("number", "right", "1")])
    add("UP-02-function-member", "x = a.function\n", ["BS-LEX-024"], "VALID",
        assign + [("member_expression", "right", None), ("identifier", "object", "a"),
                  ("identifier", "property", "function")])
    add("UP-02-directive", "#const flag = true\n#if flag\nx = 1\n#end if\n", ["BS-COND-001", "BS-COND-002"], "VALID",
        root + [("const_directive", "-", None), ("identifier", "name", "flag"), ("true", "value", "true"),
                ("if_directive", "-", None), ("identifier", "condition", "flag"), ("block", "consequence", None),
                ("assignment_statement", "-", None), ("identifier", "left", "x"), ("number", "right", "1")])
    for source in ("# if true\nx = 1\n# endif\n", "#ifx true\n", "x = a.rem\n"):
        add("UP-02-observe-" + str(len(rows)), source, ["BS-COND-009", "BS-LEX-014"], "OBSERVATION_ONLY")
    if len(rows) > 200 or len({r["case_id"] for r in rows}) != len(rows):
        raise ValueError("screen inventory")
    return rows


def edits():
    bases = [b"x = 1\r\nprint x\r\n", b"\xef\xbb\xbfx = 1\n", 'print "한글"\n'.encode(),
             b'x = "a"\n', b"x = 1 'note\n", b"REM note\nx = 1\n", b"#if true\nx = 1\n#end if\n",
             b"if a then\nx = 1\nend if\n", b"x = ) " + b"*" * 16 + b"\nx = 1\n", b"x = [1, 2]\n"]
    # Byte boundaries deliberately include BOM/UTF-8 interiors; such intermediate
    # text is observation-only, while inverse edits must restore the exact tree.
    offsets = [7, 1, 8, 6, 7, 2, 4, 7, 21, 7]
    rows = []
    for i, (base, offset) in enumerate(zip(bases, offsets)):
        script = [(offset, 1, b"@"), (len(base) - 1, 0, b" ")]
        final = apply_edits(base, script)
        rows.append({"case_id": f"TEST-02-{i:02d}", "data": base, "edits": script,
                     "final_data": final, "parse_calls": 2 + 2 * len(script),
                     "origin_bs_ids": ["BS-LEX-006", "BS-LEX-033", "BS-COND-008"],
                     "operations": ["INCREMENTAL_WITH_INVERSE_REPAIR"]})
    return rows


def apply_edits(base, script):
    text = base
    if len(script) > 8:
        raise ValueError("too many edits")
    for offset, removed, inserted in script:
        if (type(offset) is not int or type(removed) is not int or type(inserted) is not bytes
                or offset < 0 or removed < 0 or offset + removed > len(text)):
            raise ValueError("invalid byte edit")
        text = text[:offset] + inserted + text[offset + removed:]
        if len(text) > 65536:
            raise ValueError("edit output too large")
    return text


def check_dump(text, data, expected_class, expected_named=None):
    if (type(text) is not str or len(text) > OUTPUT_BYTES or len(text.encode("utf-8")) > OUTPUT_BYTES
            or text.count("\n") > MAX_NODES + 3):
        raise ValueError("dump output bound")
    lines = text.splitlines()
    if not lines or lines[-1] != "DUMP_DONE\t0" or not lines[0].startswith("F\t"):
        raise ValueError("missing dump completion")
    header = lines[0].split("\t")
    h = 14695981039346656037
    for b in data:
        h = ((h ^ b) * 1099511628211) & ((1 << 64) - 1)
    if len(header) != 4 or int(header[2]) != len(data) or header[3] != f"{h:016x}":
        raise ValueError("source fidelity differs")
    nodes, stack, named = [], [], []
    for line in lines[1:-2]:
        fields = line.split("\t")
        if len(fields) != 7 or fields[0] != "N":
            raise ValueError("malformed node")
        _, depth, kind, field, start, end, flags = fields
        depth, start, end, flags = map(int, (depth, start, end, flags))
        if (not 0 <= start <= end <= len(data) or not 0 <= depth <= len(stack)
                or not 0 <= flags <= 31 or flags & 2 and start != end):
            raise ValueError("invalid span/depth/missing")
        del stack[depth:]
        if stack and not stack[-1][0] <= start <= end <= stack[-1][1]:
            raise ValueError("child outside parent")
        if nodes and depth == 0:
            raise ValueError("duplicate root")
        stack.append((start, end))
        nodes.append((depth, kind, field, start, end, flags))
        if flags & 1:
            named.append((kind, field, data[start:end].decode("utf-8", errors="replace")))
        elif expected_class.startswith("VALID") and field == "operator":
            if kind.casefold() != data[start:end].decode("utf-8").casefold():
                raise ValueError("operator kind/source span differs")
    trailer = lines[-2].split("\t")
    if len(trailer) != 3 or trailer[0] != "END" or int(trailer[1]) != len(nodes) or not nodes:
        raise ValueError("node inventory differs")
    if nodes[0][0] != 0 or nodes[0][4] != len(data):
        raise ValueError("wrong root/EOF")
    error = bool(nodes[0][5] & 16)
    if expected_class.startswith("VALID") and (error or any(n[5] & 6 for n in nodes)):
        raise ValueError("valid source has ERROR/MISSING")
    if expected_class in ("INVALID", "RECOVERY") and not error:
        raise ValueError("malformed source has no ERROR/MISSING")
    if expected_named is not None:
        if len(named) != len(expected_named):
            raise ValueError("named node count differs")
        for got, want in zip(named, expected_named):
            if got[:2] != tuple(want[:2]) or want[2] is not None and got[2] != want[2]:
                raise ValueError("ordered public tree/field/text differs: " + repr((got, want)))
    declarations = [n for n in nodes if n[1] == "function_declaration"]
    errors = [n for n in nodes if n[5] & 6]
    return {"nodes": len(nodes), "has_error": error, "declarations": len(declarations),
            "declarations_inside_error": sum(any(e[3] <= n[3] and e[4] >= n[4] for e in errors) for n in declarations),
            "tree_sha256": hashlib.sha256(text.encode()).hexdigest()}


def check_query(final, data):
    if (final.get("final") is not True or final.get("op") != "QUERY_ONLY" or final.get("bytes") != len(data)
            or final.get("cancelled") is not False or type(final.get("has_error")) is not int
            or final.get("has_error") not in (0, 1)
            or final.get("match_limit_exceeded") is not False or type(final.get("captures")) is not int
            or final["captures"] < 0):
        raise ValueError("partial/inconsistent query")


def public_manifest():
    rows = [{k: v for k, v in row.items() if k != "data"} for row in sources()]
    edit_rows = [{"case_id": r["case_id"], "sha256": hashlib.sha256(r["data"]).hexdigest(),
                  "bytes": len(r["data"]), "edits": [(o, d, b.hex()) for o, d, b in r["edits"]],
                  "parse_calls": r["parse_calls"], "operations": r["operations"]} for r in edits()]
    return {"schema": "S07-SCREEN-r1", "sources": rows, "edit_scripts": edit_rows,
            "expected_probe_children": len(rows) * 3 + len(edit_rows) + 2,
            "expected_parser_calls": sum(r["parse_calls"] for r in rows + edit_rows) + 12,
            "controls": "two native planted comparator differences, 6 parse calls each",
            "limits": {"worker": 1, "commit_bytes": 512 * 2**20, "watchdog_ms": 15000,
                       "output_bytes": OUTPUT_BYTES, "dump_nodes": MAX_NODES},
            "expectations": "L1 and retained grammar/tree contracts; recovery locality observations are not new syntax policy"}


if __name__ == "__main__":
    print(json.dumps(public_manifest(), indent=2))
