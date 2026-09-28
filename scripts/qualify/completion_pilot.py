"""Fixed, bounded comparison of stock and an unadopted runtime candidate.

All process creation remains in run.py/tscli.py. A completed pilot is not a
release qualification and does not replace any historical failed record.
"""
import hashlib
import json
import signal
import statistics
import sys

import cases
import characterize
import completion_runtime
import gates
import gates_v4
import tscli

STRESS_CASES = ("L-ANON-1MiB", "L-WHILE-1MiB", "L-FOREACH-1MiB", "V-FLAT-1MiB", "V-LONGEXPR-1MiB")
API_CASES = ("A5-01-k01000", "A501J-k01000", "VALID-calls-004k")
API_OPS = ("QUERY_ONLY", "NAV_CURSOR", "NAV_FIELD", "NAV_INDEX")
# NAV_INDEX is the registered print-child workload, not an arbitrary-tree walker.
API_POINTS = tuple(("A5-01-number-k01000" if case == "VALID-calls-004k" and op == "NAV_INDEX" else case, op)
                   for case in API_CASES for op in API_OPS)
TOY_GRAMMAR = """module.exports = grammar({name: 'checkpoint_control', extras: $ => [/[ \\t]/], rules: {
  source_file: $ => repeat(seq($.identifier, '=', $.number, '\\n')),
  identifier: $ => /[a-z]+/, number: $ => /[0-9]+/
}});
"""


def digest(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=1) + "\n", encoding="utf-8")


def cleanup_ms(record):
    cl = record["events"]["cleanup"]
    return max(0, cl["tree_delete_ms"]) + cl["parser_delete_ms"]


def registered_runs():
    result = []
    for case in STRESS_CASES:
        result.extend((name, "PARSE", case, 0, f"pair{pair}") for pair in range(8)
                      for name in (("cand", "completion") if pair % 2 == 0 else ("completion", "cand")))
        result.extend((name, op, case, 0, "stress-api")
                      for op in (("NAV_CURSOR",) if case == "V-LONGEXPR-1MiB" else ("NAV_CURSOR", "QUERY_ONLY"))
                      for name in ("cand", "completion"))
        result.extend((name, op, case, 0, "allocation") for op in ("PARSE", "CANCEL_FIRST", "CANCEL_HALF")
                      for name in ("cand-alloc", "completion-alloc"))
        result.extend((name, "PARSE", case, budget, "timed-cancel") for budget in (100, 200)
                      for name in ("cand", "completion", "cand-alloc", "completion-alloc"))
    result.extend((name, op, case, 0, "public-api") for case, op in API_POINTS for name in ("cand", "completion"))
    return result


def judge_record(rec):
    """Validate before aggregation; reuse the frozen per-record cancellation rules."""
    f, ev = rec.get("final") or {}, rec.get("events", {})
    pe, cl = ev.get("parse", {}), ev.get("cleanup", {})
    op, case, budget = (rec.get(k) for k in ("op", "case", "budget"))
    allocator = rec.get("build", "").endswith("alloc")
    invalid = {"pass": False, "valid": False, "status": "MEASUREMENT_INCONSISTENT"}
    try:
        length = len(cases.generate(case))
        cancelled = pe.get("cancelled")
        gaps = [pe.get(k) for k in ("head_gap_ms", "max_gap_ms", "tail_gap_ms", "max_gap_incl_edges_ms")]
        counters = [f.get(k) for k in ("nodes", "errors", "missing", "max_depth", "captures",
                                       "allocator_peak_live", "allocator_total", "allocations", "allocator_live_after")]
        valid = (type(cancelled) is bool and f.get("cancelled") is cancelled and f.get("op") == op
                 and f.get("bytes") == length and type(f.get("bytes")) is int
                 and pe.get("budget_ms") == budget and f.get("match_limit_exceeded") is False
                 and all(gates.number(t) is not None for t in gaps + [pe.get("parse_ms"), cl.get("parser_delete_ms")])
                 and max(gaps[:3]) == gaps[3] <= pe["parse_ms"] + .000001
                 and (cl.get("tree_delete_ms") == -1 if cancelled else gates.number(cl.get("tree_delete_ms")) is not None)
                 and all(type(n) is int and n >= 0 for n in counters)
                 and f.get("allocator_live_after") == cl.get("allocator_live_after") == 0
                 and all(f.get(k) == pe.get(k) for k in ("parse_ms", "max_gap_incl_edges_ms"))
                 and all(f.get(k) == cl.get(k) for k in ("tree_delete_ms", "parser_delete_ms")))
        if allocator:
            valid &= f.get("allocations", 0) > 0 and f.get("allocator_total", 0) >= f.get("allocator_peak_live", 0) > 0
        else:
            valid &= all(f.get(k) == 0 for k in ("allocator_peak_live", "allocator_total", "allocations"))
        if not valid:
            return invalid
        if budget:
            judged = gates_v4.timed_record(rec, case, budget, allocator)
            if allocator and judged.get("growth") is not None:
                peak, live = cl.get("peak_after_budget"), pe.get("live_at_budget")
                if (type(peak) is not int or not pe["peak_after_budget"] <= peak <= f["allocator_peak_live"]):
                    return invalid
                judged["growth_through_cleanup"] = peak - live
                judged["pass"] &= peak - live < 64 * gates.MIB
        elif op in ("CANCEL_FIRST", "CANCEL_HALF"):
            judged = characterize.first_callback_record(rec, length, allocator, progressed=op == "CANCEL_HALF")
        else:
            valid = characterize.work_signature(rec, op, case, expected_error=int(case.startswith("L-"))) is not None
            valid &= pe.get("request_ms") == pe.get("budget_cross_ms") == -1
            if op == "QUERY_ONLY":
                q = ev.get("query", {})
                valid &= f.get("captures") == q.get("captures") and gates.number(q.get("compile_ms")) is not None
            elif op.startswith("NAV_"):
                nav = ev.get("navigation", {})
                valid &= nav.get("op") == op
                if op == "NAV_INDEX":
                    valid &= nav.get("child_calls", 0) > 0 and nav.get("visits") == nav.get("field_calls") == 0
                else:
                    valid &= nav.get("visits", 0) > 0 and nav.get("visits") == f.get("nodes")
                    valid &= nav.get("field_calls") == (f.get("nodes") if op == "NAV_FIELD" else 0)
                    valid &= nav.get("child_calls") == 0
            judged = {"pass": valid, "status": "VALID" if valid else "MEASUREMENT_INCONSISTENT"}
        return {**judged, "valid": judged["status"] != "MEASUREMENT_INCONSISTENT"}
    except (KeyError, TypeError, ValueError):
        return invalid


def api_signature(record):
    final, events = record["final"], record["events"]
    fields = ("bytes", "cancelled", "has_error", "nodes", "errors", "missing", "max_depth", "captures",
              "match_limit_exceeded")
    result = {name: final[name] for name in fields}
    for event, names in (("query", ("captures", "zero_width_captures", "exceeded", "digest")),
                         ("navigation", ("visits", "field_calls", "child_calls", "digest"))):
        if event in events:
            result[event] = {name: events[event][name] for name in names}
    return result


def verify_semantics(r, result, check):
    out = r.lab.out
    # Exact trees, including ERROR fields, across the existing full tree registry.
    trees = cases.tree_compare()
    for offset in range(0, len(trees), 150):
        chunk = trees[offset:offset + 150]
        paths = [r.write_input(f"completion-trees/{offset+i:05d}.brs", data) for i, (_, data, _) in enumerate(chunk)]
        listing = r.write_list(f"completion-trees/{offset:05d}.txt", paths)
        old = gates.parse_dump(r.probe("cand", ["DUMPLIST", listing], f"completion-stock-trees-{offset}"))
        new = gates.parse_dump(r.probe("completion", ["DUMPLIST", listing], f"completion-trees-{offset}"))
        for (name, data, _), path in zip(chunk, paths):
            a, b = old.get(str(path)), new.get(str(path))
            check("tree-" + name, bool(a and b and a["complete"] and b["complete"] and a["root"] == b["root"]))
            result["native_tree_digests"].append({"name": name, "input_sha256": digest(data),
                "tree_sha256": digest(json.dumps(b["root"], ensure_ascii=False, separators=(",", ":")).encode("utf-8"))})
        write_json(out / "completion-pilot.json", result)

    original = r.probes["cand"]
    try:
        for name in ("cand", "completion"):
            r.probes["cand"] = original if name == "cand" else r.probes["completion"]
            for fn in (gates.incremental_repair, gates.resume_and_two):
                evidence = fn(r)
                check(name + "-" + evidence["gate"], evidence["status"] == "PASS", evidence=evidence)
    finally:
        r.probes["cand"] = original


def build_candidate(r, runtime_root, runtime_objects, grammar_objects, make_probe):
    lab, here = r.lab, cases.ROOT / "scripts/qualify"
    out, build = lab.out, lab.out / "build"
    candidate = completion_runtime.candidate_bytes((runtime_root / "lib/src/parser.c").read_bytes())
    parser = build / "completion-parser.c"
    parser.write_bytes(candidate)
    (build / "completion-parser-controls.c").write_bytes(completion_runtime.controls_bytes(candidate))
    candidate_object = build / "completion-parser.o"
    lab.compile("completion-parser", ["-O2", "-Wall", "-Wextra", "-Werror", "-I", runtime_root / "lib/include",
        "-I", runtime_root / "lib/src", "-c", parser], candidate_object)
    if sum(p.name == "parser.o" for p in runtime_objects) != 1:
        raise ValueError("runtime object registration differs")
    variant_objects = [candidate_object if p.name == "parser.o" else p for p in runtime_objects]
    for name, alloc in (("completion", False), ("completion-alloc", True)):
        r.probes[name] = (make_probe(name, grammar_objects, variant_objects, runtime_root,
                                     alloc=alloc, scheduled=True), r.query)
    return variant_objects


GAP_BUILDS = ("cand", "cand-diagnostic", "completion", "completion-diagnostic")


def gap_registration():
    return [(name, "PARSE", "L-WHILE-1MiB", 0, f"gap{round}") for round in range(16)
            for name in GAP_BUILDS[round % 4:] + GAP_BUILDS[:round % 4]] + [
                (name, "NAV_CURSOR", "L-WHILE-1MiB", 0, "gap-api") for name in GAP_BUILDS]


def gap_record(rec):
    if not judge_record(rec)["pass"]:
        return False
    d, pe, f = rec["events"].get("diagnostic"), rec["events"]["parse"], rec["final"]
    if not rec["build"].endswith("-diagnostic"):
        return d is None
    if not isinstance(d, dict) or any(gates.number(d.get(k)) is None for k in (
            "parse_cpu_ms", "cleanup_cpu_ms", "gap_wall_ms", "gap_cpu_ms")):
        return False
    if (abs(d["gap_wall_ms"] - pe["max_gap_incl_edges_ms"]) > .000002
            or d["gap_cpu_ms"] > d["parse_cpu_ms"] + .000002
            or any(type(d.get(k)) is not int or not 0 <= d[k] <= f["bytes"] for k in ("gap_from_byte", "gap_to_byte"))
            or type(d.get("gap_edge")) is not int or type(d.get("gap_ordinal")) is not int
            or type(pe.get("callbacks")) is not int or pe["callbacks"] < 1):
        return False
    edge, ordinal = d["gap_edge"], d["gap_ordinal"]
    return ((edge == 0 and ordinal == 1 and d["gap_from_byte"] == 0
             and abs(d["gap_wall_ms"] - pe["head_gap_ms"]) <= .000002)
            or (edge == 1 and 2 <= ordinal <= pe["callbacks"]
                and abs(d["gap_wall_ms"] - pe["max_gap_ms"]) <= .000002)
            or (edge == 2 and ordinal == pe["callbacks"] + 1 and d["gap_to_byte"] == f["bytes"]
                and abs(d["gap_wall_ms"] - pe["tail_gap_ms"]) <= .000002))


def gap_diagnostic(r, identity, runtime_root, runtime_objects, grammar_objects, make_probe):
    """One finite follow-up to macOS pilot failure; CPU is never a release metric."""
    variant = build_candidate(r, runtime_root, runtime_objects, grammar_objects, make_probe)
    for name, objects in (("cand-diagnostic", runtime_objects), ("completion-diagnostic", variant)):
        r.probes[name] = (make_probe(name, grammar_objects, objects, runtime_root, scheduled=True, diagnostic=True), r.query)
    identity.update(protocol="completion-gap-diagnostic-v1", qualification=False, gates=[],
        runtime_candidate={"variant": completion_runtime.VARIANT, "base_parser_sha256": completion_runtime.BASE_SHA256,
                           "candidate_parser_sha256": completion_runtime.CANDIDATE_SHA256},
        diagnostic_plan={"rounds": 16, "case": "L-WHILE-1MiB", "builds": GAP_BUILDS, "parse_rows": 64,
                         "nav_rows": 4, "order": "rotate builds by round modulo four", "limit_ms": 100})
    identity["probes"].update({name: digest(r.probes[name][0].read_bytes()) for name in GAP_BUILDS})
    write_json(r.lab.out / "identity.json", identity)
    r.runtime_build = "completion-gap-diagnostic-v1-stock-and-explicit-candidate"
    result = {"qualification": False, "release_verdict": "HOLD", "complete": False, "observations": [], "api": []}
    ids, plan = set(), gap_registration()
    for expected in plan:
        name, op, case, budget, tag = expected
        rec = r.run(name, op, case, budget, tag)
        registration = tuple(rec.get(k) for k in ("build", "op", "case", "budget", "tag"))
        run_id = gates.run_id(rec)
        valid = gap_record(rec) and registration == expected and run_id not in ids
        ids.add(run_id)
        result["observations"].append({"registration": registration, "run_id": run_id, "valid": valid,
            "gap_ms": rec["events"].get("parse", {}).get("max_gap_incl_edges_ms"),
            "diagnostic": rec["events"].get("diagnostic")})
        if valid and op == "NAV_CURSOR":
            result["api"].append(api_signature(rec))
        write_json(r.lab.out / "completion-gap.json", result)
        if not valid:
            raise RuntimeError("completion gap diagnostic invalid record: " + str(registration))
    result["complete"] = (len(ids) == len(result["observations"]) == len(plan) == 68
                          and len(result["api"]) == 4 and all(x == result["api"][0] for x in result["api"]))
    result["diagnostic_over_100ms"] = [x for x in result["observations"] if x["registration"][1] == "PARSE"
                                      and x["diagnostic"] is not None and x["gap_ms"] > 100]
    write_json(r.lab.out / "completion-gap.json", result)
    print("COMPLETION_GAP_DIAGNOSTIC_COMPLETE" if result["complete"] else "COMPLETION_GAP_DIAGNOSTIC_INCOMPLETE", flush=True)
    return 0 if result["complete"] else 1


def run(r, identity, runtime_root, runtime_objects, grammar_objects, make_probe):
    lab, here = r.lab, cases.ROOT / "scripts/qualify"
    out, build = lab.out, lab.out / "build"
    build_candidate(r, runtime_root, runtime_objects, grammar_objects, make_probe)
    identity.update(protocol="completion-pilot-v1", qualification=False, gates=[],
        runtime_candidate={"variant": completion_runtime.VARIANT, "base_parser_sha256": completion_runtime.BASE_SHA256,
            "candidate_parser_sha256": completion_runtime.CANDIDATE_SHA256,
            "controls_parser_sha256": digest((build / "completion-parser-controls.c").read_bytes())},
        pilot_plan={"stress_cases": STRESS_CASES, "timing_pairs": 8, "api_points": API_POINTS,
            "timed_budgets_ms": [100, 200], "expected_run_rows": 192,
            "tree_compare_count": cases.RECORDED["tree_compare_count"], "recovery_inputs": 33,
            "known_unresolved": "Prior stock/chunk V-LONGEXPR-1MiB QUERY_ONLY watchdogs; not repeated or superseded."})
    identity["probes"].update({name: digest(r.probes[name][0].read_bytes()) for name in ("completion", "completion-alloc")})
    write_json(out / "identity.json", identity)
    r.runtime_build = "completion-pilot-v1-stock-and-explicit-candidate"
    result = {"qualification": False, "release_verdict": "HOLD", "complete": False,
              "checks": [], "timings": [], "api_signatures": [], "native_tree_digests": [], "records": []}
    write_json(out / "completion-pilot.json", result)

    def check(name, passed, **detail):
        result["checks"].append({"name": name, "pass": bool(passed), **detail})
        if not passed:
            write_json(out / "completion-pilot.json", result)
            raise RuntimeError("completion pilot check failed: " + name)

    # Synthetic scanner-free grammar and exact checkpoint state controls.
    toy = out / "toy"
    toy.mkdir()
    (toy / "grammar.js").write_text(TOY_GRAMMAR, encoding="utf-8")
    write_json(toy / "tree-sitter.json", {"grammars": [{"name": "checkpoint_control", "scope": "source.control", "path": "."}],
                                         "metadata": {"version": "0.0.0", "license": "MIT"}, "bindings": {}})
    code, stdout, stderr = tscli.cli("generate", "--abi", "15", cwd=toy, timeout=120)
    (out / "generation.log").write_text(stdout + stderr, encoding="utf-8")
    check("toy-generation", code == 0)
    toy_object = build / "completion-toy.o"
    lab.compile("completion-toy", ["-O2", "-I", toy / "src", "-c", toy / "src/parser.c"], toy_object)
    controls = build / ("completion-controls.exe" if sys.platform == "win32" else "completion-controls")
    links = ["-lpsapi", "-Wl,--no-insert-timestamp"] if sys.platform == "win32" else []
    lab.compile("completion-controls", ["-O2", "-Wall", "-Wextra", "-Werror", "-I", build, "-I", runtime_root / "lib/include",
        "-I", runtime_root / "lib/src", here / "completion_controls.c", toy_object, *grammar_objects,
        *[p for p in runtime_objects if p.name != "parser.o"], *links], controls)
    exits = ({"uaf": {0xc0000005}, "double-free": {3, 0xc0000409}, "normal": {0}} if sys.platform == "win32" else
             {"uaf": {-signal.SIGSEGV, -signal.SIGBUS}, "double-free": {-signal.SIGABRT}, "normal": {0}})
    for mode in ("uaf", "double-free", "normal"):
        report, text = lab.supervise("completion-controls-" + mode, [controls, *([] if mode == "normal" else [mode])])
        marker = ("CHECKPOINT_CONTROLS_PASS 52" if mode == "normal" else
                  "CONTROL_UAF_ARMED" if mode == "uaf" else "CONTROL_DOUBLE_FREE_ARMED")
        if mode == "normal":
            (out / "controls-result.txt").write_text(text, encoding="utf-8")
        check("controls-" + mode, report["termination_reason"] == "COMPLETED" and report["exit_code_raw"] in exits[mode]
              and marker in text and (mode != "double-free" or "a->live" in text), report=report)

    def observed(build_name, op, case, budget, tag):
        rec = r.run(build_name, op, case, budget, tag)
        registration = tuple(rec.get(k) for k in ("build", "op", "case", "budget", "tag"))
        judged = judge_record(rec)
        result["records"].append({"registration": registration, "run_id": gates.run_id(rec), **judged})
        check("valid-" + "-".join(map(str, registration)), judged["valid"]
              and registration == registered_runs()[len(result["records"]) - 1], judgement=judged)
        return rec

    def compare_api(op, case, tag):
        a = observed("cand", op, case, 0, tag)
        b = observed("completion", op, case, 0, tag)
        left, right = api_signature(a), api_signature(b)
        check("api-" + op + "-" + case, left == right)
        result["api_signatures"].append({"op": op, "case": case, "signature": right})

    recovery = sorted((cases.ROOT / "test/recovery").glob("*.brs"))
    check("recovery-registration", len(recovery) == 33)
    for fixture in recovery:
        a = r.probe("cand", ["DUMP", fixture], "completion-stock-" + fixture.stem)
        b = r.probe("completion", ["DUMP", fixture], "completion-candidate-" + fixture.stem)
        check("recovery-" + fixture.name, a == b)

    for case in STRESS_CASES:
        rows = []
        for pair in range(8):
            for name in (("cand", "completion") if pair % 2 == 0 else ("completion", "cand")):
                rows.append(observed(name, "PARSE", case, 0, f"pair{pair}"))
        point = {"case": case, "builds": {}}
        for name in ("cand", "completion"):
            selected = [rec for rec in rows if rec["build"] == name]
            point["builds"][name] = {"parse_median_ms": statistics.median(gates.m_parse(x) for x in selected),
                "max_gap_ms": max(x["events"]["parse"]["max_gap_incl_edges_ms"] for x in selected),
                "max_cleanup_ms": max(cleanup_ms(x) for x in selected)}
        result["timings"].append(point)
        compare_api("NAV_CURSOR", case, "stress-api")
        if case != "V-LONGEXPR-1MiB":
            compare_api("QUERY_ONLY", case, "stress-api")
        for op in ("PARSE", "CANCEL_FIRST", "CANCEL_HALF"):
            pair = [observed(name, op, case, 0, "allocation") for name in ("cand-alloc", "completion-alloc")]
            fields = ("allocator_peak_live", "allocator_total", "allocations", "allocator_live_after")
            check("allocator-" + op + "-" + case, all(pair[0]["final"][k] == pair[1]["final"][k] for k in fields)
                  and all(x["final"]["allocator_live_after"] == 0 for x in pair)
                  and (op == "PARSE" or all(x["events"]["parse"]["cancelled"] for x in pair)))
        for budget in (100, 200):
            for name in ("cand", "completion", "cand-alloc", "completion-alloc"):
                rec = observed(name, "PARSE", case, budget, "timed-cancel")
                if name.endswith("alloc"):
                    check("timed-allocator-" + name + "-" + case + "-" + str(budget), rec["final"]["allocator_live_after"] == 0)
        write_json(out / "completion-pilot.json", result)
        print("COMPLETION_PILOT_STRESS_COMPLETE " + case, flush=True)
    for case, op in API_POINTS:
        compare_api(op, case, "public-api")

    verify_semantics(r, result, check)
    check("run-registration", [x["registration"] for x in result["records"]] == registered_runs()
          and len({x["run_id"] for x in result["records"]}) == 192 and len(lab.runs) == 192)
    result["candidate_response_observations_pass"] = all(
        point["builds"]["completion"]["max_gap_ms"] <= 100
        and point["builds"]["completion"]["max_cleanup_ms"] <= 100 for point in result["timings"])
    result["complete"] = True
    result["candidate_records_pass"] = all(x["pass"] for x in result["records"] if x["registration"][0].startswith("completion"))
    result["baseline_records_pass"] = all(x["pass"] for x in result["records"] if x["registration"][0].startswith("cand"))
    result["timed_growth_observations"] = []
    for name in ("cand", "completion"):
        for case in STRESS_CASES:
            for budget in (100, 200):
                point = [x for x in result["records"] if x["registration"] in (
                    (name, "PARSE", case, budget, "timed-cancel"), (name + "-alloc", "PARSE", case, budget, "timed-cancel"))]
                observed_growth = len(point) == 2 and (not point[0].get("reached") or point[1].get("growth") is not None)
                result["timed_growth_observations"].append({"build": name, "case": case, "budget": budget,
                                                           "pass": observed_growth})
    result["pilot_pass"] = (all(x["pass"] for x in result["checks"]) and result["candidate_response_observations_pass"]
                            and result["candidate_records_pass"] and all(x["pass"] for x in result["timed_growth_observations"]
                                                                         if x["build"] == "completion"))
    write_json(out / "completion-pilot.json", result)
    print("COMPLETION_PILOT_PASS" if result["pilot_pass"] else "COMPLETION_PILOT_FAIL", flush=True)
    return 0 if result["pilot_pass"] else 1
