"""Owner-selected v6 cooperative completion; retain complete v5 and 100 ms judgements."""
import hashlib
import json
from itertools import islice
from pathlib import Path

import gates
import gates_v4

PROTOCOL = "v6"
V5_SHA256 = "9056d84a249e809b3c11feaad07881f3bfa043201b852e94549a009bb64e0381"
LIMIT_MS = 250
CONTRACT = {
    "callback_gap_ms": LIMIT_MS,
    "timed_return_over_budget_ms": LIMIT_MS,
    "trigger_to_return_ms": LIMIT_MS,
    "tree_and_parser_delete_ms": LIMIT_MS,
}
SPEC = {"protocol": PROTOCOL, "limits_ms": CONTRACT,
        "overshoot_collection": "v3: three extra runs at 80..120 ms or above 100 ms",
        "actual_cancellation": "every issued timed cancellation request and all FIRST/HALF controls",
        "timed_normal_completion": "no request, correct result, plain return <= B+250; NOT_TRIGGERED, never cancellation coverage",
        "timed_memory": "elapsed budget still requires observed growth in the fixed six allocator samples; missing observation fails",
        "overshoot_semantics": "return within budget + allowance; natural completion is not actual-cancellation evidence"}
SHA256 = hashlib.sha256(json.dumps(SPEC, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
IDENTITY = {"spec": SPEC, "sha256": SHA256}
GATES = {"CANCEL", "CANCEL-OVERSHOOT", "MAX-CALLBACK-GAP", "CLEANUP-ALL"}


def require_identity(identity):
    if identity.get("protocol") != PROTOCOL or identity.get("response_policy") != IDENTITY:
        raise ValueError("unapproved or missing v6 response policy")


def require_results(results):
    for result in results:
        if result["gate"] in GATES:
            legacy = result.get("legacy_v4_1_100ms", {})
            v5 = result.get("legacy_v5_250ms", {})
            if (result.get("response_policy_sha256") != SHA256 or legacy.get("gate") != result["gate"]
                    or legacy.get("status") not in ("PASS", "FAIL") or v5.get("gate") != result["gate"]
                    or v5.get("status") not in ("PASS", "FAIL") or v5.get("response_policy_sha256") != V5_SHA256):
                raise ValueError("response gate policy or historical judgement missing")


def require_raw_results(path, results):
    """Recompute active and both historical verdicts from the raw segment; no native execution."""
    path = Path(path)
    if not path.is_file() or path.is_symlink() or path.stat().st_size > 64 * 2**20:
        raise ValueError("missing, linked or oversized response raw records")
    case, budget, _ = gates.CANCEL_POINTS[0]
    first = ("cand", "PARSE", case, budget, "rep0")
    maximum = (278 + len(gates.CANCEL_SET + gates.LARGE_SET) * len(gates.BUDGETS) * 4
               + len(gates.CANCEL_SET + gates.LARGE_SET + gates.VALID_1MIB) * 4)
    with path.open(encoding="utf-8") as source:
        rows = (json.loads(line) for line in source)
        start = next((r for r in rows if tuple(r.get(k) for k in ("build", "op", "case", "budget", "tag")) == first), None)
        if start is None:
            raise ValueError("response raw registration missing")
        replay = Replay([start, *islice(rows, maximum - 1)])
    actual = []
    for judge in (gates_v4.cancel, gates.overshoot, gates.gaps_and_cleanup):
        result = evaluate(replay, judge)
        actual.extend(result if isinstance(result, list) else [result])
    expected = [x for x in results if x["gate"] in GATES]
    if json.loads(json.dumps(actual)) != expected:
        raise ValueError("response raw replay differs from active or historical judgement")


def valid_record(record):
    """Reject invalid individual timings before a maximum could conceal them."""
    f, ev, report = record.get("final") or {}, record.get("events", {}), record.get("report", {})
    pe, cl = ev.get("parse", {}), ev.get("cleanup", {})
    cancelled = pe.get("cancelled")
    gaps = [pe.get(k) for k in ("head_gap_ms", "max_gap_ms", "tail_gap_ms", "max_gap_incl_edges_ms")]
    try:
        return bool(record.get("completed") is True and report.get("termination_reason") == "COMPLETED"
            and type(report.get("exit_code_raw")) is int and report["exit_code_raw"] == 0
            and report.get("exit_confirmed") is True and type(report.get("active_processes")) is int
            and report["active_processes"] == 0
            and type(report.get("pid")) is int and report["pid"] > 0
            and type(report.get("creation_filetime", report.get("creation_monotonic_ns"))) is int
            and report.get("creation_filetime", report.get("creation_monotonic_ns")) > 0
            and f.get("final") is True and f.get("op") == record["op"] and type(cancelled) is bool
            and gates.result_check(record, record["case"], len(gates.cases.generate(record["case"]))) == "OK"
            and type(record["budget"]) is int and gates.number(pe.get("budget_ms")) == record["budget"]
            and all(gates.number(x) is not None for x in gaps + [pe.get("parse_ms"), cl.get("parser_delete_ms")])
            and max(gaps[:3]) == gaps[3] <= pe["parse_ms"] + .000001
            and (cl.get("tree_delete_ms") == -1 if cancelled else gates.number(cl.get("tree_delete_ms")) is not None)
            and all(type(f.get(k)) in (int, float) and f[k] == pe.get(k) for k in ("parse_ms", "max_gap_incl_edges_ms"))
            and all(type(f.get(k)) in (int, float) and f[k] == cl.get(k) for k in ("tree_delete_ms", "parser_delete_ms"))
            and type(f.get("allocator_live_after")) is int and type(cl.get("allocator_live_after")) is int
            and f["allocator_live_after"] == cl["allocator_live_after"] == 0)
    except (KeyError, TypeError, ValueError):
        return False


def overshoot_record(record):
    """The inherited OVERSHOOT purpose bounds return time; CANCEL proves actual cancellation."""
    reached, status, _, parse_ms, _ = gates.budget_run(record, record["budget"])
    pe = record["events"]["parse"]
    valid = (status != "MEASUREMENT_INCONSISTENT" and gates.uninstrumented(record)
             and (not pe["cross_at_callback"] or pe["cancelled"]))
    passed = valid and parse_ms <= record["budget"] + LIMIT_MS
    return {"pass": passed, "status": ("INVALID" if not valid else "CANCELLED" if pe["cancelled"] else
             "NATURAL_WITHIN_RETURN_BOUND" if reached else "NATURAL_BEFORE_BUDGET"), "parse_ms": parse_ms}


class Recording:
    def __init__(self, runner):
        self.runner, self.lab, self.records = runner, runner.lab, []

    def run(self, *args, **kwargs):
        record = self.runner.run(*args, **kwargs)
        self.records.append(record)  # Full return records; lab.runs compacts budget-zero rows.
        if not valid_record(record):
            raise ValueError("invalid response measurement; raw execution retained")
        return record


class Replay:
    def __init__(self, records):
        self.records, self.runs, self.lab = records, [], self

    def run(self, build, op, case, budget, tag=""):
        if len(self.runs) >= len(self.records):
            raise ValueError("historical response replay requested an extra execution")
        record = self.records[len(self.runs)]
        if tuple(record[k] for k in ("build", "op", "case", "budget", "tag")) != (build, op, case, budget, tag):
            raise ValueError("historical response registration changed")
        self.runs.append(record)
        return record


def evaluate(runner, judge):
    """Collect once; retain v6, historical v5 at 250 ms and v4.1 at 100 ms."""
    recording = Recording(runner)
    options = {"allow_natural": True} if judge is gates_v4.cancel else {}
    current = judge(recording, response_ms=LIMIT_MS, **options)
    v5_replay = Replay(recording.records)
    v5_result = judge(v5_replay, response_ms=LIMIT_MS)
    replay = Replay(recording.records)
    historical = judge(replay)  # Default remains exactly the historical 100 ms policy.
    if len(replay.runs) != len(recording.records) or len(v5_replay.runs) != len(recording.records):
        raise ValueError("historical response replay did not consume every execution")
    active = current if isinstance(current, list) else [current]
    old = historical if isinstance(historical, list) else [historical]
    v5 = v5_result if isinstance(v5_result, list) else [v5_result]
    if [x["gate"] for x in active] != [x["gate"] for x in old] or [x["gate"] for x in v5] != [x["gate"] for x in old]:
        raise ValueError("response gate registration changed")
    for result, prior_v5, previous in zip(active, v5, old):
        if result["gate"] == "CANCEL-OVERSHOOT":
            judged = [overshoot_record(x) for x in recording.records]
            result["individual_runs"] = judged
            prior_v5["individual_runs"] = judged
            if not all(x["pass"] for x in judged):
                result["status"] = prior_v5["status"] = "FAIL"
        prior_v5.update(response_policy_sha256=V5_SHA256, legacy_v4_1_100ms=previous)
        prior_v5["notes"].append("v5: owner-selected 250 ms response policy; historical 100 ms verdict retained separately")
        result.update(response_policy_sha256=SHA256, legacy_v4_1_100ms=previous, legacy_v5_250ms=prior_v5)
        result["notes"].append("v6: bounded natural completion is NOT_TRIGGERED; actual requests, FIRST/HALF and memory remain required")
    require_results(active)
    return current
