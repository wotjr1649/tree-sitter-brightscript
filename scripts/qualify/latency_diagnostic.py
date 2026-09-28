"""Fixed CPU/wall observation plan. Completion is never a qualification verdict."""
import json
import math
import datetime as dt
import time
import hashlib

import gates

CASES = [f"{name}-1MiB" for name in ("L-WHILE", "L-FOREACH", "L-ANON", "V-FLAT", "V-LONGEXPR")]
BUILDS = ["cand", "cand-diagnostic", "cand-alloc", "cand-alloc-diagnostic"]
WITNESSES = {
    "SW-y203d205b-2920else20-colon-k00400": "098af1c08e174926c2984393d2a7322b50a57c55f1d6bd033989b2b52d1d7ae8",
    "SW-3f20-5b12c-eof-k00400": "6a74157f694f43d4018c0b6d8306a198a73394ae4a92f5d16a1009b19b7eb3ad",
}


def witness_inputs(r):
    inputs = {}
    for case, expected in WITNESSES.items():
        data = r.input(case).read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise ValueError("witness input differs from registration: " + case)
        inputs[case] = {"bytes": len(data), "sha256": expected}
    return inputs


def witness_record(rec, case, length):
    p, report, f = rec.get("events", {}).get("parse", {}), rec.get("report", {}), rec.get("final") or {}
    return bool(rec.get("completed") is True and rec.get("build") == "cand" and rec.get("case") == case
        and rec.get("op") == f.get("op") == "PARSE" and type(rec.get("budget")) is int and rec["budget"] == 0
        and f.get("final") is True and f.get("cancelled") is False and p.get("cancelled") is False
        and type(f.get("bytes")) is int and gates.result_check(rec, case, length) == "OK"
        and gates.uninstrumented(rec) and "diagnostic" not in rec["events"]
        and gates.number(p.get("budget_ms")) == 0 and p.get("request_ms") == p.get("budget_cross_ms") == -1
        and all(type(p.get(k)) is int and p[k] == 0 for k in ("callback_target", "byte_target"))
        and report.get("termination_reason") == "COMPLETED" and report.get("exit_confirmed") is True
        and type(report.get("exit_code_raw")) is int and report["exit_code_raw"] == 0
        and type(report.get("active_processes")) is int and report["active_processes"] == 0
        and all(gates.number(report.get(k)) is not None for k in ("user_cpu_ms", "kernel_cpu_ms"))
        and gates.number(p.get("parse_ms")) is not None and gates.number(f.get("parse_ms")) is not None
        and f["parse_ms"] == p["parse_ms"]
        and gates.number(p.get("max_gap_incl_edges_ms")) is not None
        and gates.number(f.get("max_gap_incl_edges_ms")) is not None
        and f.get("max_gap_incl_edges_ms") == p["max_gap_incl_edges_ms"]
        and p["max_gap_incl_edges_ms"] <= p["parse_ms"] + 0.000002)


def witness(r, out):
    inputs = witness_inputs(r)
    started_utc, start = dt.datetime.now(dt.timezone.utc).isoformat(), time.monotonic()
    points = []
    for rep in range(5000):
        for case in WITNESSES:
            rec = r.run("cand", "PARSE", case, 0, f"witness{rep}")
            p, report = rec["events"].get("parse", {}), rec["report"]
            valid = witness_record(rec, case, inputs[case]["bytes"])
            points.append({"case": case, "rep": rep, "observation_complete": bool(valid),
                           "parse_ms": p.get("parse_ms"), "gap_ms": p.get("max_gap_incl_edges_ms"),
                           "user_cpu_ms": report.get("user_cpu_ms"), "kernel_cpu_ms": report.get("kernel_cpu_ms")})
        if (rep + 1) % 500 == 0:
            print("LATENCY_WITNESS_RECORDED", len(points), flush=True)
    complete = (witness_inputs(r) == inputs and len(points) == 10000
                and all(p["observation_complete"] for p in points))
    (out / "latency-diagnostic.json").write_text(json.dumps({"qualification": False,
        "started_utc": started_utc, "duration_seconds": time.monotonic() - start, "inputs": inputs,
        "observations_complete": complete, "observations": points}, indent=1) + "\n", encoding="utf-8")
    print("WITNESS_COMPLETE" if complete else "WITNESS_INCOMPLETE", flush=True)
    return 0 if complete else 1


def run(r, out):
    observations = []
    for case in CASES:
        for budget in (0, 100, 200):
            for rep in range(4):
                # Balance ordering without dropping warmups, maxima or failed records.
                for build in BUILDS if rep % 2 == 0 else reversed(BUILDS):
                    rec = r.run(build, "PARSE", case, budget, f"diagnostic{rep}")
                    d, p = rec["events"].get("diagnostic"), rec["events"].get("parse", {})
                    valid = rec["completed"] and rec["final"] and rec["final"].get("final") is True
                    if build.endswith("-diagnostic"):
                        valid = (valid and isinstance(d, dict) and
                                 all(type(d.get(k)) in (float, int) and math.isfinite(d[k]) and d[k] >= 0
                                     for k in ("parse_cpu_ms", "cleanup_cpu_ms", "gap_wall_ms", "gap_cpu_ms")) and
                                 abs(d["gap_wall_ms"] - p.get("max_gap_incl_edges_ms", -1)) <= 0.000002 and
                                 d.get("gap_edge") in (0, 1, 2) and
                                 type(d.get("gap_ordinal")) is int and 1 <= d["gap_ordinal"] <= p["callbacks"] + 1)
                    else:
                        valid = valid and d is None
                    observations.append({"build": build, "case": case, "budget": budget, "rep": rep,
                                         "observation_complete": bool(valid)})
        print("LATENCY_DIAGNOSTIC_RECORDED", case, flush=True)
    complete = len(observations) == 240 and all(x["observation_complete"] for x in observations)
    (out / "latency-diagnostic.json").write_text(json.dumps({"qualification": False,
        "observations_complete": complete, "observations": observations}, indent=1) + "\n", encoding="utf-8")
    print("DIAGNOSTIC_COMPLETE" if complete else "DIAGNOSTIC_INCOMPLETE", flush=True)
    return 0 if complete else 1
