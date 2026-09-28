"""Finite build/measurement diagnosis; never substitutes for qualification. Stdlib only."""
import hashlib
import json
import os
import random
import re
from pathlib import Path

import gates

BASELINE = "b9eab178472c9a43914bd86eb9a14b8a16a9464e"  # peeled immutable v0.1.3
SWEEP = ("SW-print20-f282a-eof", "SW-return20-7ba3a402a7d3c-nl", "SW-while20-25e2a-eof")


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


def run(runners, identity, out, seed):
    trial = int(os.environ.get("TSQ_TRIAL", "1"))
    if trial not in (1, 2, 3):
        raise ValueError("TSQ_TRIAL must be 1, 2 or 3")
    order = list(runners)
    random.Random(seed + trial).shuffle(order)
    result = {"release_verdict": "HOLD", "complete": False, "purpose": "characterization-only", "identity": identity,
              "trial": trial, "order": order, "profiles": {}}
    for name in order:
        r = runners[name]
        control = same_binary_control(r, seed + trial)
        results = []
        for measure in (lambda: gates.a5_01_cost(r, seed), lambda: gates.valid_parse(r, seed),
                        lambda: gates.gaps_and_cleanup(r), lambda: gates.cancel(r)):
            measured = measure()
            results.extend(measured if isinstance(measured, list) else [measured])
            print(f"CHARACTERIZATION {name}: {results[-1]['gate']} {results[-1]['status']}", flush=True)
        sweep = []
        for family in SWEEP:
            series = {k: gates.timed(r, "cand", "PARSE", f"{family}-k{k:05d}", r.cost_samples, gates.m_parse)
                      for k in (100, 400, 4000, 20000)}
            times = {k: gates.med(values) if values else None for k, (values, _) in series.items()}
            sweep.append({"family": family, "median_ms": times})
        result["profiles"][name] = {"measured_samples": r.cost_samples, "warmup": 1,
                                    "same_binary_control": control, "v3_results": results, "sweep_diagnosis": sweep}
        result["input_sha256"] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                  for p in sorted((out / "inputs").glob("*.brs"))}
        (out / "characterization.json").write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    if (out / "runs.jsonl").stat().st_size > 64 * 2**20:
        raise RuntimeError("characterization raw evidence exceeds 64 MiB; cohort incomplete")
    result["complete"] = True
    (out / "characterization.json").write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    print("CHARACTERIZATION_RECORDED release=HOLD", flush=True)
