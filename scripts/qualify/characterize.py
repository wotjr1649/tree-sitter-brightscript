"""Finite build/measurement diagnosis; never substitutes for qualification. Stdlib only."""
import hashlib
import json
import math
import os
import random
import re
from pathlib import Path

import gates

BASELINE = "b9eab178472c9a43914bd86eb9a14b8a16a9464e"  # peeled immutable v0.1.3


def first_callback_record(rec, length, allocator, progressed=False, *, response_ms=100):
    """Judge one diagnostic run by its own trigger, return, cleanup and supervisor evidence."""
    pe, cl = rec.get("events", {}).get("parse", {}), rec.get("events", {}).get("cleanup", {})
    final, report = rec.get("final") or {}, rec.get("report", {})
    times = [pe.get(k) for k in ("parse_ms", "request_ms", "budget_cross_ms")]
    cleanup = cl.get("parser_delete_ms")
    counts = [pe.get(k) for k in ("live_at_budget", "peak_after_budget", "live_at_return")]
    counts += [final.get(k) for k in ("allocator_peak_live", "allocations", "allocator_live_after")]
    counts.append(cl.get("peak_after_budget"))
    valid = (rec.get("completed") is True and report.get("termination_reason") == "COMPLETED"
             and report.get("exit_code_raw") == 0 and report.get("exit_confirmed") is True
             and type(report.get("active_processes")) is int and report["active_processes"] == 0
             and type(report.get("pid")) is int and report["pid"] > 0
             and type(report.get("creation_filetime", report.get("creation_monotonic_ns"))) is int
             and report.get("creation_filetime", report.get("creation_monotonic_ns")) > 0
             and all(gates.number(t) is not None for t in times + [cleanup])
             and all(type(c) is int and c >= 0 for c in counts)
             and pe.get("cancelled") is True and pe.get("cross_at_callback") is True
             and type(pe.get("callbacks")) is int and (pe["callbacks"] >= 2 if progressed else pe["callbacks"] == 1)
             and type(pe.get("callback_target")) is int and pe["callback_target"] == (0 if progressed else 1)
             and type(pe.get("budget_ms")) in (int, float) and pe["budget_ms"] == 0
             and final.get("final") is True and final.get("op") == ("CANCEL_HALF" if progressed else "CANCEL_FIRST")
             and type(final.get("bytes")) is int and final["bytes"] == length
             and final.get("cancelled") is True and type(final.get("has_error")) is int
             and final["has_error"] == -1 and final.get("parse_ms") == times[0]
             and cl.get("tree_delete_ms") == -1 and final.get("tree_delete_ms") == -1
             and final.get("parser_delete_ms") == cleanup
             and type(cl.get("allocator_live_after")) is int and cl["allocator_live_after"] == 0
             and final.get("allocator_live_after") == 0)
    if progressed:
        valid &= (all(type(pe.get(k)) is int and pe[k] >= 0 for k in
                      ("byte_target", "request_byte", "max_byte_before_request"))
                  and length > 1 and pe["byte_target"] == (length + 1) // 2
                  and pe["max_byte_before_request"] < pe["byte_target"] <= pe["request_byte"] < length)
    if valid:
        parse_ms, request, cross = times
        live, peak, returned, overall, allocations, _, cleanup_peak = counts
        valid = (0 <= request == cross <= parse_ms and peak >= max(live, returned)
                 and overall >= cleanup_peak >= peak)
        valid &= live > 0 and allocations > 0 if allocator else all(c == 0 for c in counts)
    if not valid:
        return {"pass": False, "status": "MEASUREMENT_INCONSISTENT"}
    latency, growth = parse_ms - request, cleanup_peak - live
    # The null tree sentinel is not negative cleanup time. Allocator timings are diagnostic only.
    passed = growth < 64 * gates.MIB if allocator else latency <= response_ms and cleanup <= response_ms
    return {"pass": passed, "status": "PASS" if passed else "FAIL", "return_after_request_ms": latency,
            "cleanup_ms": cleanup, "growth_after_request_bytes": growth}


def first_callback_control(r, progressed=False, *, response_ms=100):
    points, all_ids = [], []
    op, tag = ("CANCEL_HALF", "half") if progressed else ("CANCEL_FIRST", "first")
    for case in gates.CANCEL_ACTUAL:
        plain = [r.run("cand", op, case, 0, tag=f"{tag}{i}") for i in range(6)]
        alloc = r.run("cand-alloc", op, case, 0, tag=f"{tag}-alloc")
        judged = [first_callback_record(x, len(gates.cases.generate(case)), i == 6, progressed, response_ms=response_ms)
                  for i, x in enumerate(plain + [alloc])]
        ids = [gates.run_id(x) for x in plain + [alloc]]
        all_ids.extend(ids)
        points.append({"case": case, "source_sha": gates.cases.RECORDED["cases"][case], "run_ids": ids,
                       "judged": judged, "pass": len(set(ids)) == 7 and all(x["pass"] for x in judged)})
    return {"pass": len(set(all_ids)) == 49 and all(p["pass"] for p in points), "points": points}


def same_binary_control(r, seed):
    """A/A checks repeatability at equal input size, not absolute growth or safety."""
    image, query = r.probes["cand"]
    r.probes.update({"aa-left": (image, query), "aa-right": (image, query)})
    rng, points = random.Random(seed), []
    for case in gates.A5_01 + gates.A501J:
        for op, metric in (("QUERY_ONLY", gates.m_query), ("NAV_CURSOR", gates.m_nav),
                           ("NAV_FIELD", gates.m_nav), ("NAV_INDEX", gates.m_nav)):
            def checked_metric(record):
                try:
                    value = metric(record)
                except (KeyError, TypeError):
                    return float("inf")
                return value if gates.number(value) is not None and value > 0 else float("inf")

            meds, recs = gates.paired(r, "aa-left", "aa-right", op, case, 5, checked_metric, rng)
            if meds is None:
                points.append({"case": case, "op": op, "pass": False, "censored": True})
                continue
            signatures = []
            records = recs["aa-left"] + recs["aa-right"]
            valid = all(gates.number(checked_metric(record)) is not None for record in records)
            for record in records:
                final = {k: v for k, v in record["final"].items() if not k.endswith("_ms")}
                event = record["events"].get("query" if op == "QUERY_ONLY" else "navigation", {})
                fields = ("captures", "zero_width_captures") if op == "QUERY_ONLY" else (
                    "visits", "field_calls", "child_calls")
                digest = event.get("digest")
                valid &= isinstance(digest, str) and re.fullmatch(r"[0-9a-f]{16}", digest) is not None
                valid &= all(type(event.get(k)) is int and event[k] >= 0 for k in fields)
                if op == "QUERY_ONLY":
                    valid &= event.get("exceeded") is False
                valid &= (record["final"].get("final") is True and record["final"].get("cancelled") is False
                          and record["final"].get("has_error") == 0 and type(record["final"].get("bytes")) is int
                          and record["final"]["bytes"] > 0)
                work = {k: event.get(k) for k in (*fields, "digest")}
                signatures.append(json.dumps([final, work], sort_keys=True))
            left, right = meds["aa-left"], meds["aa-right"]
            valid &= all(gates.number(v) is not None and v > 0 for v in (left, right))
            ratio = max(left, right) / min(left, right) if valid else None
            same = len(set(signatures)) == 1
            points.append({"case": case, "op": op, "left_ms": left, "right_ms": right,
                           "observed_count": {side: len(series) for side, series in recs.items()},
                           "symmetric_ratio": ratio, "same_work": same,
                           "pass": valid and same and ratio <= 1.5})
    return {"image_sha256": hashlib.sha256(Path(image).read_bytes()).hexdigest(),
            "query_sha256": hashlib.sha256(Path(query).read_bytes()).hexdigest(),
            "pass": all(p["pass"] for p in points), "points": points}


def paired_estimates(left, right):
    """16 intact rounds, first warmup excluded. Both estimands are retained."""
    if len(left) != 16 or len(right) != 16 or any(gates.number(x) is None or x <= 0 for x in left + right):
        return {"valid": False}
    ratios = [a / b for a, b in zip(left[1:], right[1:])]
    if any(gates.number(x) is None or x <= 0 for x in ratios):
        return {"valid": False}
    paired, lm, rm = gates.med(ratios), gates.med(left[1:]), gates.med(right[1:])
    if gates.number(lm / rm) is None or lm / rm <= 0:
        return {"valid": False}
    return {"valid": True, "ratios": ratios, "paired_ratio": paired, "legacy_ratio": lm / rm,
            "left_median_ms": lm, "right_median_ms": rm}


def work_signature(rec, op, case, *, expected_error=None):
    """Validate each native result, including warmup, before using its metric."""
    f, pe = rec.get("final") or {}, rec.get("events", {}).get("parse", {})
    report = rec.get("report", {})
    valid = (rec.get("completed") is True and report.get("exit_confirmed") is True
             and report.get("termination_reason") == "COMPLETED"
             and type(report.get("exit_code_raw")) is int and report["exit_code_raw"] == 0
             and type(report.get("pid")) is int and report["pid"] > 0
             and type(report.get("creation_filetime", report.get("creation_monotonic_ns"))) is int
             and report.get("creation_filetime", report.get("creation_monotonic_ns")) > 0
             and type(report.get("active_processes")) is int and report["active_processes"] == 0
             and f.get("final") is True and f.get("op") == op and f.get("cancelled") is False
             and pe.get("cancelled") is False and pe.get("budget_ms") == 0
             and type(f.get("has_error")) is int
             and f["has_error"] == (int(case.startswith("SW-")) if expected_error is None else expected_error)
             and type(f.get("bytes")) is int and f["bytes"] > 0
             and gates.number(pe.get("parse_ms")) is not None and pe["parse_ms"] > 0
             and type(f.get("parse_ms")) in (int, float) and f["parse_ms"] == pe["parse_ms"])
    signature = [f.get("bytes"), f.get("has_error")]
    if op != "PARSE":
        ev = rec.get("events", {}).get("query" if op == "QUERY_ONLY" else "navigation", {})
        fields = ("captures", "zero_width_captures") if op == "QUERY_ONLY" else ("visits", "field_calls", "child_calls")
        valid &= isinstance(ev.get("digest"), str) and re.fullmatch(r"[0-9a-f]{16}", ev["digest"]) is not None
        valid &= all(type(ev.get(k)) is int and ev[k] >= 0 for k in fields)
        valid &= op != "QUERY_ONLY" or ev.get("exceeded") is False
        key = "query_ms" if op == "QUERY_ONLY" else "navigation_ms"
        valid &= (gates.number(ev.get(key)) is not None and ev[key] > 0
                  and type(f.get(key)) in (int, float) and f[key] == ev[key])
        signature += [ev.get(k) for k in (*fields, "digest")]
    return json.dumps(signature) if valid else None


def measure_rounds(r, sides, members, op, rng):
    """Every size once per side per round; shared middle-size observations are not rerun."""
    records = {side: {case: [] for case in members} for side in sides}
    for i in range(16):
        order = list(members)
        rng.shuffle(order)
        for case in order:
            builds = list(sides)
            rng.shuffle(builds)
            for side in builds:
                records[side][case].append(r.run(side, op, case, 0, tag=f"round{i}"))
    metric = {"PARSE": gates.m_parse, "QUERY_ONLY": gates.m_query,
              "NAV_CURSOR": gates.m_nav, "NAV_FIELD": gates.m_nav, "NAV_INDEX": gates.m_nav}[op]
    points = {}
    for side in sides:
        for case in members:
            series = records[side][case]
            signatures = [work_signature(x, op, case) for x in series]
            values = []
            for record in series:
                try:
                    values.append(metric(record))
                except (KeyError, TypeError):
                    values.append(None)
            identities = [gates.run_id(x) for x in series]
            valid = (len(series) == 16 and len(set(identities)) == 16
                     and all("None" not in identity for identity in identities)
                     and [x["tag"] for x in series] == [f"round{i}" for i in range(16)]
                     and None not in signatures and len(set(signatures)) == 1
                     and all(gates.number(v) is not None and v > 0 for v in values)
                     and all(x["final"]["bytes"] == len(r.input(case).read_bytes()) for x in series))
            points[(side, case)] = {"valid": valid, "values": values, "signature": signatures[0],
                                    "run_ids": identities}
    return points


def cost_points(data, sides, members, op, aa=False):
    points = []
    for case in members:
        left, right = (data[(s, case)] for s in sides)
        e = paired_estimates(left["values"], right["values"])
        same = left["signature"] == right["signature"] and left["signature"] is not None
        valid = left["valid"] and right["valid"] and e["valid"] and same
        p = {"case": case, "op": op, "same_work": same, "valid": valid,
             "run_ids": {sides[0]: left["run_ids"], sides[1]: right["run_ids"]}, **e}
        # Never let the numeric-only validity overwrite record/work validity.
        p["valid"] = valid
        if valid:
            new, old = e["paired_ratio"], e["legacy_ratio"]
            applicable = aa or e["right_median_ms"] >= gates.FLOOR_MS
            if aa:
                new, old = max(new, 1 / new), max(old, 1 / old)
            p.update(applicable=applicable, pass_=not applicable or new <= 1.5,
                     legacy_pass=not applicable or old <= 1.5)
        else:
            p.update(pass_=False, legacy_pass=False)
        p["pass"] = p.pop("pass_")
        points.append(p)
    return points


def growth_points(data, members, sizes, op, limit, floor):
    points = []
    edges = [(1, 3), (2, 3)] if floor == "sweep" else [(len(members) - 3, len(members) - 2),
                                                        (len(members) - 2, len(members) - 1)]
    for a, b in edges:
        small, large = (data[("cand", members[i])] for i in (a, b))
        e = paired_estimates(large["values"], small["values"])
        valid = small["valid"] and large["valid"] and e["valid"]
        p = {"small": members[a], "large": members[b], "op": op, "limit": limit, "floor": floor, **e}
        p["valid"] = valid
        if valid:
            scale = max(e["right_median_ms"], gates.FLOOR_MS) / e["right_median_ms"] if floor == "sweep" else 1
            new = math.log(e["paired_ratio"] / scale) / math.log(sizes[b] / sizes[a])
            old = math.log(e["legacy_ratio"] / scale) / math.log(sizes[b] / sizes[a])
            applicable = floor != "a5" or e["left_median_ms"] >= gates.FLOOR_MS
            p.update(floor_scale=scale, paired_exponent=new, legacy_exponent=old, applicable=applicable,
                     pass_=not applicable or new <= limit, legacy_pass=not applicable or old <= limit)
        else:
            p.update(pass_=False, legacy_pass=False)
        p["pass"] = p.pop("pass_")
        points.append(p)
    return points


def paired_diagnosis(r, seed):
    rng, aa, cost, growth = random.Random(seed), [], [], []
    r.probes.update({"aa-left": r.probes["cand"], "aa-right": r.probes["cand"]})
    a5 = [(gates.A5_01[:6], [1000, 2000, 4000, 8000, 16000, 32000]),
          (gates.A5_01[6:], [1000, 2000, 4000, 8000, 16000, 32000]),
          (gates.A501J, [1000, 2000, 4000, 8000])]
    valid = a5[:2] + [([f"VALID-{f}-{k:03d}k" for k in (4, 16, 64, 256)], [4, 16, 64, 256])
                       for f in gates.VALID_FAMILIES]
    valid += [(["W03-compact", "W03-program", "W03-program-crlf"], [])]
    for groups, ops, ref, bound, floor in ((a5, ("QUERY_ONLY", "NAV_CURSOR", "NAV_FIELD", "NAV_INDEX"), "bp", 1.5, "a5"),
                                          (valid, ("PARSE",), "h", 1.2, "none")):
        for members, sizes in groups:
            for op in ops:
                a = measure_rounds(r, ("aa-left", "aa-right"), members, op, rng)
                aa.extend(cost_points(a, ("aa-left", "aa-right"), members, op, aa=True))
                d = measure_rounds(r, ("cand", ref), members, op, rng)
                cost.extend(cost_points(d, ("cand", ref), members, op))
                if sizes:
                    growth.extend(growth_points(d, members, sizes, op, bound, floor))
                print(f"PAIRED_DIAGNOSIS {members[0]} {op}", flush=True)
    for family in ("SW-print20-f282a-eof", "SW-return20-7ba3a402a7d3c-nl", "SW-while20-25e2a-eof"):
        sizes = [100, 400, 4000, 20000]
        members = [f"{family}-k{k:05d}" for k in sizes]
        d = measure_rounds(r, ("cand",), members, "PARSE", rng)
        growth.extend(growth_points(d, members, sizes, "PARSE", 1.5, "sweep"))
    slow_case = ["A501J-k01000"]
    d = measure_rounds(r, ("slow", "cand"), slow_case, "NAV_CURSOR", rng)
    slow = cost_points(d, ("slow", "cand"), slow_case, "NAV_CURSOR")[0]
    # Detection counts only if the same work completed and the measured ratio itself rejects the delay.
    slow_detected = slow["valid"] and slow["same_work"] and slow["paired_ratio"] > 1.5
    slow_detected &= all(v >= 2 for v in d[("slow", slow_case[0])]["values"])
    ids = [gates.run_id(x) for x in r.lab.runs]
    complete = (len(ids) == 6816 and len(set(ids)) == len(ids) and all("None" not in i for i in ids)
                and all(p["valid"] for p in aa + cost + growth) and slow["valid"])
    return {"aa": aa, "cost": cost, "growth": growth, "slow_control": slow, "slow_detected": slow_detected,
            "complete": complete, "native_runs": len(ids),
            "controls_pass": complete and slow_detected and all(p["pass"] for p in aa),
            "paired_performance_pass": all(p["pass"] for p in cost + growth)}


def run(r, identity, out):
    trial = int(os.environ.get("TSQ_TRIAL", "1"))
    if trial not in (1, 2, 3):
        raise ValueError("TSQ_TRIAL must be 1, 2 or 3")
    result = {"release_verdict": "HOLD", "complete": False, "purpose": "characterization-only", "identity": identity,
              "trial": trial, "first_callback_control": first_callback_control(r),
              "progressed_control": first_callback_control(r, progressed=True)}
    result["input_sha256"] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in sorted((out / "inputs").glob("*.brs"))}
    (out / "characterization.json").write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    if (out / "runs.jsonl").stat().st_size > 64 * 2**20:
        raise RuntimeError("characterization raw evidence exceeds 64 MiB; cohort incomplete")
    ids = [gates.run_id(x) for x in r.lab.runs]
    expected = {case + ".brs": gates.cases.RECORDED["cases"][case] for case in gates.CANCEL_ACTUAL}
    result["complete"] = (len(ids) == 98 and len(set(ids)) == 98 and all("None" not in i for i in ids)
                          and result["input_sha256"] == expected)
    result["runs_sha256"] = hashlib.sha256((out / "runs.jsonl").read_bytes()).hexdigest()
    (out / "characterization.json").write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    print("CHARACTERIZATION_RECORDED release=HOLD", flush=True)
    return 0 if (result["complete"] and result["first_callback_control"]["pass"]
                 and result["progressed_control"]["pass"]) else 1
