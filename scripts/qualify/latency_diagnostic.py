"""Fixed CPU/wall observation plan. Completion is never a qualification verdict."""
import json
import math

CASES = [f"{name}-1MiB" for name in ("L-WHILE", "L-FOREACH", "L-ANON", "V-FLAT", "V-LONGEXPR")]
BUILDS = ["cand", "cand-diagnostic", "cand-alloc", "cand-alloc-diagnostic"]


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
