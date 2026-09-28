"""v4 measurement contract. Keep v3 judgements and raw failures intact (native-v4-plan.md)."""
import random

import characterize as paired
import gates

A5_GROUPS = [(gates.A5_01[:6], [1000, 2000, 4000, 8000, 16000, 32000]),
             (gates.A5_01[6:], [1000, 2000, 4000, 8000, 16000, 32000]),
             (gates.A501J, [1000, 2000, 4000, 8000])]
VALID_GROUPS = A5_GROUPS[:2] + [([f"VALID-{f}-{k:03d}k" for k in (4, 16, 64, 256)], [4, 16, 64, 256])
                                    for f in gates.VALID_FAMILIES]
VALID_GROUPS += [(["W03-compact", "W03-program", "W03-program-crlf"], [])]
A5_OPS = ("QUERY_ONLY", "NAV_CURSOR", "NAV_FIELD", "NAV_INDEX")


def unique(records, count):
    ids = [gates.run_id(r) for r in records]
    return len(ids) == count and len(set(ids)) == count and all("None" not in i for i in ids)


def controls(r, seed):
    """One fixed 3,328-execution control set shared by all three performance gates."""
    if hasattr(r, "v4_controls"):
        return r.v4_controls
    start, rng, points = len(r.lab.runs), random.Random(seed), []
    r.probes.update({"aa-left": r.probes["cand"], "aa-right": r.probes["cand"]})
    for groups, ops in ((A5_GROUPS, A5_OPS), (VALID_GROUPS, ("PARSE",))):
        for members, _ in groups:
            for op in ops:
                data = paired.measure_rounds(r, ("aa-left", "aa-right"), members, op, rng)
                points.extend(paired.cost_points(data, ("aa-left", "aa-right"), members, op, aa=True))
    members = ["A501J-k01000"]
    data = paired.measure_rounds(r, ("slow", "cand"), members, "NAV_CURSOR", rng)
    slow = paired.cost_points(data, ("slow", "cand"), members, "NAV_CURSOR")[0]
    detected = (slow["valid"] and slow["same_work"] and slow["paired_ratio"] > 1.5
                and all(t >= 2 for t in data[("slow", members[0])]["values"]))
    complete = unique(r.lab.runs[start:], 3328) and len(points) == 103
    r.v4_controls = {"pass": complete and detected and all(p["pass"] for p in points),
                     "complete": complete, "aa": points, "slow_control": slow, "slow_detected": detected}
    return r.v4_controls


def performance(r, seed, valid=False):
    control = controls(r, seed)
    start, rng, points = len(r.lab.runs), random.Random(seed), []
    groups, ops, reference, bound, floor = (VALID_GROUPS, ("PARSE",), "h", 1.2, "none") if valid else (
        A5_GROUPS, A5_OPS, "bp", 1.5, "a5")
    for members, sizes in groups:
        for op in ops:
            data = paired.measure_rounds(r, ("cand", reference), members, op, rng)
            points.extend(paired.cost_points(data, ("cand", reference), members, op))
            if sizes:
                points.extend(paired.growth_points(data, members, sizes, op, bound, floor))
    complete = unique(r.lab.runs[start:], 1248 if valid else 2048)
    result = gates.result("VALID-PARSE" if valid else "A5-01-COST",
                          complete and control["pass"] and all(p["pass"] for p in points), points,
                          ["v4: 1 warmup + 15 independent cold rounds; paired ratios; v3 numeric bounds/floors"])
    result.update(controls=control, complete=complete)
    return result


def sweep(r, seed):
    control = controls(r, seed)
    start, rng, points = len(r.lab.runs), random.Random(seed), []
    for family, _, unit, _ in gates.cases.sweep_families():
        sizes = [100, 400, 4000, 20000]
        members = [f"{family}-k{k:05d}" for k in sizes]
        first = len(r.lab.runs)
        data = paired.measure_rounds(r, ("cand",), members, "PARSE", rng)
        work_valid = all(data[("cand", case)]["valid"] for case in members)
        growth = paired.growth_points(data, members, sizes, "PARSE", 1.5, "sweep")
        records = r.lab.runs[first:]
        peaks = {case: [x["report"].get("peak_commit_bytes") for x in records if x["case"] == case]
                 for case in members}
        memory_valid = all(len(values) == 16 and all(gates.number(v) is not None for v in values)
                           for values in peaks.values())
        delta = max(peaks[members[-1]]) - max(peaks[members[0]]) if memory_valid else None
        points.append({"family": family, "growth": growth, "memory_growth": delta,
                       "peak_memory": {c: max(v) for c, v in peaks.items()} if memory_valid else {},
                       "kl002": unit in gates.KL002_UNITS,
                       "pass": work_valid and memory_valid and delta < 64 * gates.MIB and all(p["pass"] for p in growth)})
    complete = len(points) == 297 and unique(r.lab.runs[start:], 19008)
    result = gates.result("REGRESSION-SWEEP", complete and control["pass"] and all(p["pass"] for p in points), points,
                          ["v4: all 297 families, all 16 cold rounds; original memory and growth bounds/floors"])
    result.update(controls=control, complete=complete)
    return result


def timed_record(rec, case, budget, allocator):
    """A late natural return never supplies cancellation evidence, including warmup and allocator."""
    report, final = rec.get("report", {}), rec.get("final") or {}
    pe, cl = rec.get("events", {}).get("parse", {}), rec.get("events", {}).get("cleanup", {})
    reached, status, growth, parse_ms, cleanup = gates.budget_run(rec, budget)
    valid = (rec.get("completed") is True and report.get("termination_reason") == "COMPLETED"
             and type(report.get("exit_code_raw")) is int and report["exit_code_raw"] == 0
             and report.get("exit_confirmed") is True and type(report.get("active_processes")) is int
             and report["active_processes"] == 0 and type(report.get("pid")) is int and report["pid"] > 0
             and type(report.get("creation_filetime", report.get("creation_monotonic_ns"))) is int
             and report.get("creation_filetime", report.get("creation_monotonic_ns")) > 0
             and status not in ("MEASUREMENT_INCONSISTENT", "NOT_RUN_BUDGET_REACHED_UNOBSERVED")
             and gates.result_check(rec, case, len(gates.cases.generate(case))) == "OK"
             and final.get("final") is True and final.get("op") == "PARSE"
             and all(type(final.get(k)) in (int, float) and final[k] == value for k, value in (
                 ("parse_ms", parse_ms), ("tree_delete_ms", cl.get("tree_delete_ms")),
                 ("parser_delete_ms", cl.get("parser_delete_ms"))))
             and type(cl.get("allocator_live_after")) is int and cl["allocator_live_after"] == 0
             and final.get("allocator_live_after") == 0
             and (allocator or gates.uninstrumented(rec)))
    if not valid:
        return {"pass": False, "status": "MEASUREMENT_INCONSISTENT"}
    cancelled = pe["cancelled"]
    passed = (cancelled if reached else not cancelled and parse_ms < budget)
    passed &= growth is None or growth < 64 * gates.MIB
    if not allocator:
        passed &= parse_ms <= budget + 100 and cleanup <= 100
    return {"pass": passed, "status": "CANCELLED" if cancelled else "NATURAL_BEFORE_BUDGET" if not reached else
            "LATE_NATURAL", "reached": reached, "growth": growth, "parse_ms": parse_ms, "cleanup_ms": cleanup}


def cancel(r):
    start = len(r.lab.runs)
    legacy = gates.cancel(r)
    records = r.lab.runs[start:]
    points = []
    for case, budget, _ in gates.CANCEL_POINTS:
        series = [x for x in records if x["case"] == case and x["budget"] == budget]
        expected = [("cand", f"rep{i}") for i in range(6)] + [("cand-alloc", "alloc")]
        judged = [timed_record(x, case, budget, x["build"] == "cand-alloc") for x in series]
        registered = [(x["build"], x["tag"]) for x in series] == expected
        growth_observed = (registered and (not any(p.get("reached") for p in judged[:6])
                                          or judged[-1].get("growth") is not None))
        points.append({"case": case, "budget": budget, "judged": judged,
                       "pass": registered and growth_observed and all(p["pass"] for p in judged)})
    first = paired.first_callback_control(r)
    half = paired.first_callback_control(r, progressed=True)
    complete = unique(r.lab.runs[start:], 203)
    ok = (complete and all(p["safety"] == "PASS" for p in legacy["points"])
          and all(p["pass"] for p in points) and first["pass"] and half["pass"])
    result = gates.result("CANCEL", ok, points, ["v4: retain all 15 timed points and legacy SAFETY; "
                          "require FIRST and HALF for all seven families, independent of timed coverage"])
    result.update(complete=complete, legacy=legacy, first_callback_control=first, progressed_control=half)
    return result
