"""Make a bounded, OS-neutral v0.1.4 native result from one host's verified records."""
import argparse
import hashlib
import json
import platform
import sys
from pathlib import Path

from check_oracle_pair import compare, stable_files

sys.path.insert(0, str(Path(__file__).resolve().parent / "qualify"))
import gates as registered

REQUIRED_GATES = (
    "B5-01-MEMORY", "B5-02-LIFECYCLE", "A5-01-COST", "CANCEL", "CANCEL-OVERSHOOT",
    "MAX-CALLBACK-GAP", "CLEANUP-ALL", "LARGE-INPUT", "QUERY-MALFORMED", "VALID-PARSE",
    "SEM-PUBLIC", "INCREMENTAL-REPAIR", "RESUME-RESET", "SUPPORT", "REGRESSION-SWEEP",
    "ABS-MEMORY", "RECOVERY-LOCALITY",
)


def registered_run_keys(v4=True):
    """Exact operation/input registration, preserving every one of the 1,533 v3 keys."""
    keys = set()

    def add(builds, ops, cases):
        keys.update(f"{b}|{o}|{c}" for b in builds for o in ops for c in cases)

    a5 = registered.A5_01 + registered.A501J
    ops = ("QUERY_ONLY", "NAV_CURSOR", "NAV_FIELD", "NAV_INDEX")
    valid = registered.A5_01 + [f"VALID-{f}-{k:03d}k" for f in registered.VALID_FAMILIES for k in (4, 16, 64, 256)]
    valid += ["W03-compact", "W03-program", "W03-program-crlf"]
    add(("cand", "bp"), ops, a5)
    add(("cand",), ("LIFECYCLE",), registered.B5_02 + registered.B5_02_NONPRINT)
    add(("cand",), ("PARSE",), registered.B5_01 + registered.CANCEL_SET + registered.LARGE_SET + registered.VALID_1MIB)
    add(("cand", "h"), ("PARSE",), valid)
    add(("cand",), ("PARSE",), [f"{f}-k{k:05d}" for f, _, _, _ in registered.cases.sweep_families()
                                  for k in (100, 400, 4000, 20000)])
    add(("cand",), ("QUERY_ONLY",), [f"{f}-k{k:05d}" for f in registered.QUERY_MALFORMED for k in (2000, 20000)])
    add(("cand-alloc",), ("PARSE",), registered.B5_01 + registered.LARGE_SET + registered.VALID_1MIB)
    add(("cand-rt0.25.1", "cand-rt0.26.13"), ("LIFECYCLE",),
        registered.B5_01 + registered.B5_02 + ["A5-01-k32000", "A5-01-number-k32000"])
    if v4:
        add(("aa-left", "aa-right"), ops, a5)
        add(("aa-left", "aa-right"), ("PARSE",), valid)
        add(("slow",), ("NAV_CURSOR",), ("A501J-k01000",))
        add(("cand", "cand-alloc"), ("CANCEL_FIRST", "CANCEL_HALF"), registered.CANCEL_ACTUAL)
    return keys


def read_json(path, limit=32 * 2**20):
    path = Path(path)
    if not path.is_file() or path.is_symlink() or path.stat().st_size > limit:
        raise ValueError(f"missing, linked or oversized record: {path.name}")
    return json.loads(path.read_text(encoding="utf-8"))


def signatures(path):
    path = Path(path)
    if not path.is_file() or path.is_symlink() or path.stat().st_size > 64 * 2**20:
        raise ValueError("missing or oversized runs record")
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        rec = json.loads(line)
        if rec["budget"] != 0 or not rec["completed"]:
            continue  # Timed cancellation is judged by its native gate on each OS.
        final, events = rec["final"], rec["events"]
        if not final or not final.get("final"):
            raise ValueError("completed native run has no final record")
        key = "|".join(map(str, (rec["build"], rec["op"], rec["case"])))
        fields = ("bytes", "cancelled", "has_error", "nodes", "errors", "missing", "max_depth",
                  "captures", "match_limit_exceeded")
        signature = {name: final[name] for name in fields}
        for event, names in (("query", ("captures", "zero_width_captures", "exceeded", "digest")),
                             ("navigation", ("visits", "field_calls", "child_calls", "digest"))):
            if event in events:
                signature[event] = {name: events[event][name] for name in names}
        if key in out and out[key] != signature:
            raise ValueError(f"non-deterministic native output: {key}")
        out[key] = signature
    if not out:
        raise ValueError("no deterministic native runs")
    return out


def incremental_signatures(points):
    out = []
    for point in points:
        if not point["pass"]:
            raise ValueError("incremental point failed")
        if "result" in point:
            out.append({"case": point["case"], "pass": True,
                        "result": {k: v for k, v in point["result"].items() if not k.endswith("_ms")}})
        elif point["case"] in ("comparator self-test 1", "comparator self-test 2") and point.get("detected") is True:
            out.append({"case": point["case"], "pass": True, "detected": True})
        else:
            raise ValueError("unknown incremental evidence shape")
    if len(out) != 30 or [p["case"] for p in out if "detected" in p] != [
            "comparator self-test 1", "comparator self-test 2"]:
        raise ValueError("incremental evidence is incomplete")
    return out


def build(qualification, oracle_a, oracle_b):
    q = Path(qualification)
    identity = read_json(q / "identity.json", 2**20)
    gate_record = read_json(q / "gates.json")
    if gate_record["identity"] != identity or not identity["git_clean"] or identity.get("protocol") != "v4":
        raise ValueError("qualification identity is incomplete or dirty")
    gates = gate_record["results"]
    if tuple(g["gate"] for g in gates) != REQUIRED_GATES or any(g["status"] != "PASS" for g in gates):
        raise ValueError("a required native gate is missing, reordered or not PASS")
    count, content_sha = compare(oracle_a, oracle_b)
    _, oracle = stable_files(oracle_a)
    oracle_id = oracle["identity"]
    if oracle_id["grammar_commit"] != identity["git_head"]:
        raise ValueError("oracle and qualification commits differ")
    for name, digest in oracle_id["generated_files"].items():
        if identity["candidate"].get(name) != digest:
            raise ValueError(f"oracle and qualification source differ: {name}")
    sem = gates[REQUIRED_GATES.index("SEM-PUBLIC")]["points"][0]
    trees = sem.get("native_tree_digests")
    if not isinstance(trees, list) or len(trees) != 2811:
        raise ValueError("native SEM-PUBLIC tree digest set is incomplete")
    incremental = gates[REQUIRED_GATES.index("INCREMENTAL-REPAIR")]["points"]
    edits = incremental_signatures(incremental)
    with (q / "runs.jsonl").open(encoding="utf-8") as runs_file:
        first_run = json.loads(runs_file.readline())
    return {
        "common": {
            "commit": identity["git_head"], "candidate": identity["candidate"],
            "lane_sources": identity["lane_sources"],
            "protocol": identity["protocol"], "runtime": identity["runtime"], "support": identity["support"], "seed": identity["seed"],
            "gate_statuses": [g["gate"] for g in gates],
            "oracle_cases": count, "oracle_workload": oracle_id["workload"],
            "oracle_content_sha256": content_sha, "native_trees": trees,
            "native_runs": signatures(q / "runs.jsonl"), "incremental": edits,
        },
        "host": {
            "platform": oracle_id["platform"], "architecture": platform.machine().lower(),
            "hosted_run": identity.get("hosted_run"),
            "runner_image": identity["runner_image"],
            "cc_sha256": identity["cc_sha256"],
            "cli_binary_sha256": oracle_id["cli_binary_sha256"],
            "supervisor_kind": identity["supervisor_kind"],
            "supervisor_sha256": identity.get("supervisor_sha256"),
            "probe_sha256": identity["probes"],
            "memory_metric": first_run["report"].get("memory_metric", "windows_private_commit"),
            "identity_sha256": hashlib.sha256((q / "identity.json").read_bytes()).hexdigest(),
            "gates_sha256": hashlib.sha256((q / "gates.json").read_bytes()).hexdigest(),
            "runs_sha256": hashlib.sha256((q / "runs.jsonl").read_bytes()).hexdigest(),
        },
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--qualification", required=True)
    parser.add_argument("--oracle-a", required=True)
    parser.add_argument("--oracle-b", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    result = build(args.qualification, args.oracle_a, args.oracle_b)
    out = Path(args.out)
    if out.exists():
        raise SystemExit("evidence output already exists")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"NATIVE_EVIDENCE_PASS gates={len(result['common']['gate_statuses'])} "
          f"trees={len(result['common']['native_trees'])} oracle={result['common']['oracle_cases']}")
