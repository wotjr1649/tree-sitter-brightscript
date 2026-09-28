"""Finite build/measurement diagnosis; never substitutes for qualification. Stdlib only."""
import hashlib
import json
import os
import random
import re
from pathlib import Path

import gates

BASELINE = "b9eab178472c9a43914bd86eb9a14b8a16a9464e"  # peeled immutable v0.1.3


def first_callback_record(rec, length, allocator):
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
             and type(pe.get("callbacks")) is int and pe["callbacks"] == 1
             and type(pe.get("callback_target")) is int and pe["callback_target"] == 1
             and type(pe.get("budget_ms")) in (int, float) and pe["budget_ms"] == 0
             and final.get("final") is True and final.get("op") == "CANCEL_FIRST"
             and type(final.get("bytes")) is int and final["bytes"] == length
             and final.get("cancelled") is True and type(final.get("has_error")) is int
             and final["has_error"] == -1 and final.get("parse_ms") == times[0]
             and cl.get("tree_delete_ms") == -1 and final.get("tree_delete_ms") == -1
             and final.get("parser_delete_ms") == cleanup
             and type(cl.get("allocator_live_after")) is int and cl["allocator_live_after"] == 0
             and final.get("allocator_live_after") == 0)
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
    passed = growth < 64 * gates.MIB if allocator else latency <= 100 and cleanup <= 100
    return {"pass": passed, "status": "PASS" if passed else "FAIL", "return_after_request_ms": latency,
            "cleanup_ms": cleanup, "growth_after_request_bytes": growth}


def first_callback_control(r):
    points, all_ids = [], []
    for case in gates.CANCEL_ACTUAL:
        plain = [r.run("cand", "CANCEL_FIRST", case, 0, tag=f"first{i}") for i in range(6)]
        alloc = r.run("cand-alloc", "CANCEL_FIRST", case, 0, tag="first-alloc")
        judged = [first_callback_record(x, len(gates.cases.generate(case)), i == 6)
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


def run(r, identity, out):
    trial = int(os.environ.get("TSQ_TRIAL", "1"))
    if trial not in (1, 2, 3):
        raise ValueError("TSQ_TRIAL must be 1, 2 or 3")
    result = {"release_verdict": "HOLD", "complete": False, "purpose": "characterization-only", "identity": identity,
              "trial": trial, "first_callback_control": first_callback_control(r)}
    result["input_sha256"] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in sorted((out / "inputs").glob("*.brs"))}
    (out / "characterization.json").write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    if (out / "runs.jsonl").stat().st_size > 64 * 2**20:
        raise RuntimeError("characterization raw evidence exceeds 64 MiB; cohort incomplete")
    result["complete"] = True
    (out / "characterization.json").write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    print("CHARACTERIZATION_RECORDED release=HOLD", flush=True)
    return 0 if result["first_callback_control"]["pass"] else 1
