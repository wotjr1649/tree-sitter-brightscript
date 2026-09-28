"""Finite build/measurement diagnosis; never substitutes for qualification. Stdlib only."""
import hashlib
import json
import os
import random

import gates

BASELINE = "b9eab178472c9a43914bd86eb9a14b8a16a9464e"  # peeled immutable v0.1.3
SWEEP = ("SW-print20-f282a-eof", "SW-return20-7ba3a402a7d3c-nl", "SW-while20-25e2a-eof")


def run(runners, identity, out, seed):
    trial = int(os.environ.get("TSQ_TRIAL", "1"))
    if trial not in (1, 2, 3):
        raise ValueError("TSQ_TRIAL must be 1, 2 or 3")
    order = list(runners)
    random.Random(seed + trial).shuffle(order)
    result = {"release_verdict": "HOLD", "purpose": "characterization-only", "identity": identity,
              "trial": trial, "order": order, "profiles": {}}
    for name in order:
        r = runners[name]
        results = []
        for measure in (lambda: gates.a5_01_cost(r, seed), lambda: gates.valid_parse(r, seed),
                        lambda: gates.gaps_and_cleanup(r), lambda: gates.cancel(r)):
            measured = measure()
            results.extend(measured if isinstance(measured, list) else [measured])
            print(f"CHARACTERIZATION {name}: {results[-1]['gate']} {results[-1]['status']}", flush=True)
        sweep = []
        for family in SWEEP:
            series = {k: gates.timed(r, "cand", "PARSE", f"{family}-k{k:05d}", 5, gates.m_parse)
                      for k in (100, 400, 4000, 20000)}
            times = {k: gates.med(values) if values else None for k, (values, _) in series.items()}
            sweep.append({"family": family, "median_ms": times})
        result["profiles"][name] = {"v3_results": results, "sweep_diagnosis": sweep}
        result["input_sha256"] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                  for p in sorted((out / "inputs").glob("*.brs"))}
        (out / "characterization.json").write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    print("CHARACTERIZATION_RECORDED release=HOLD", flush=True)
