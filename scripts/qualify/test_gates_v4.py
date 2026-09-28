"""Synthetic judgement controls for v4, not parser performance evidence."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

import gates
import gates_v4
from test_characterize import cancellation_record
from run import Runner, retained_run


class Records:
    def __init__(self, defect=None):
        self.defect, self.lab, self.runs = defect, self, []
        self.probes = {"cand": ("image", "query")}

    def input(self, case):
        return self

    def read_bytes(self):
        return b"a\n"

    def run(self, build, op, case, budget, tag=""):
        n = len(self.runs) + 1
        t = 3. if build == "slow" else 1.
        if self.defect == "aa" and build == "aa-right":
            t = 2.
        if self.defect == "slow" and build == "slow":
            t = 1.
        if self.defect == "candidate" and build == "cand" and op == "PARSE" and case.startswith("VALID-"):
            t = 2.
        r = {"completed": True, "build": build, "op": op, "case": case, "budget": budget, "tag": tag,
             "report": {"pid": n, "creation_filetime": 1, "exit_confirmed": True, "active_processes": 0,
                        "termination_reason": "COMPLETED", "exit_code_raw": 0, "peak_commit_bytes": 1024},
             "final": {"final": True, "op": op, "cancelled": False, "has_error": int(case.startswith("SW-")),
                       "bytes": 2, "parse_ms": t, "query_ms": t, "navigation_ms": t},
             "events": {"parse": {"cancelled": False, "budget_ms": 0, "parse_ms": t},
                        "query": {"query_ms": t, "captures": 1, "zero_width_captures": 0,
                                  "exceeded": False, "digest": "a" * 16},
                        "navigation": {"navigation_ms": t, "visits": 1, "field_calls": 0,
                                       "child_calls": 0, "digest": "a" * 16}}}
        if self.defect == "memory" and case.startswith("SW-") and case.endswith("k20000") and tag == "round0":
            r["report"]["peak_commit_bytes"] += 64 * gates.MIB
        if case.startswith("SW-") and case.endswith("k00100"):
            if self.defect == "small-warmup" and tag == "round0":
                r["completed"] = False
            if self.defect == "small-measured" and tag == "round7":
                r["final"] = None
        if self.defect == "duplicate" and n == 3328:
            r["report"]["pid"] = 1
        self.runs.append(r)
        return r


class Cancellation:
    def __init__(self, defect=None):
        self.defect, self.lab, self.runs = defect, self, []

    def run(self, build, op, case, budget, tag=""):
        r = cancellation_record(build == "cand-alloc")
        n, length = len(self.runs) + 1, len(gates.cases.generate(case))
        r.update(build=build, op=op, case=case, budget=budget, tag=tag)
        r["report"]["pid"] = n
        r["final"].update(bytes=length, op=op)
        pe, cl, final = r["events"]["parse"], r["events"]["cleanup"], r["final"]
        if budget:
            pe.update(parse_ms=budget - 1., budget_ms=budget, cancelled=False, budget_cross_ms=-1.,
                      cross_at_callback=False, live_at_budget=0, peak_after_budget=0)
            cl["tree_delete_ms"] = 1.
            final.update(parse_ms=budget - 1., cancelled=False, has_error=0 if case in gates.VALID_1MIB else 1,
                         tree_delete_ms=1.)
            if self.defect == "late" and n == 1:
                pe["parse_ms"] = final["parse_ms"] = budget
            if self.defect == "warmup-cleanup" and n == 1:
                cl["parser_delete_ms"] = final["parser_delete_ms"] = 101.
            if self.defect == "warmup-memory" and n == 1:
                pe.update(parse_ms=budget + 1., cancelled=True, budget_cross_ms=budget, cross_at_callback=True)
                cl["tree_delete_ms"] = -1.
                final.update(parse_ms=budget + 1., cancelled=True, has_error=-1, tree_delete_ms=-1.)
            if self.defect == "late-allocator" and n == 7:
                pe.update(parse_ms=budget + 1., budget_cross_ms=budget, live_at_budget=1000, peak_after_budget=1000)
                final["parse_ms"] = budget + 1.
        elif op == "CANCEL_HALF":
            target = (length + 1) // 2
            pe.update(callbacks=10, callback_target=0, byte_target=target,
                      request_byte=target, max_byte_before_request=target - 1)
            if self.defect == "half":
                pe["request_byte"] = length
        if self.defect == "duplicate" and n == 203:
            r["report"]["pid"] = 1
        self.runs.append(r)
        return r


class V4Judgement(unittest.TestCase):
    def test_retention_preserves_full_raw_return_and_both_process_id_types(self):
        for clock in ("creation_filetime", "creation_monotonic_ns"):
            with tempfile.TemporaryDirectory() as directory:
                class Lab:
                    out, runs = Path(directory), []

                    def supervise(self, cid, argv):
                        report = {"pid": 42, clock: 123, "peak_commit_bytes": 1000,
                                  "termination_reason": "COMPLETED", "exit_code_raw": 0,
                                  "exit_confirmed": True, "active_processes": 0}
                        events = [{"event": "parse", "parse_ms": 1.}, {"final": True, "bytes": 1}]
                        return report, "\n".join(json.dumps(x) for x in events)

                lab = Lab()
                (lab.out / "inputs").mkdir()
                runner = Runner(lab, {"cand": ("image", "query")}, "query")
                record = runner.run("cand", "PARSE", "A501J-k01000", 0)
                raw = json.loads((lab.out / "runs.jsonl").read_text())
                self.assertEqual(record, raw)
                self.assertIn("events", raw)
                self.assertNotIn("events", lab.runs[0])
                self.assertEqual(lab.runs[0]["report"], {"pid": 42, clock: 123, "peak_commit_bytes": 1000})
                self.assertEqual(gates.run_id(lab.runs[0]), gates.run_id(record))
                timed = dict(record, budget=200)
                self.assertIs(retained_run(timed), timed)

    def test_complete_performance_plan_and_cache_isolation(self):
        r = Records()
        for gate in (gates_v4.performance(r, 5707), gates_v4.performance(r, 5707, valid=True), gates_v4.sweep(r, 5707)):
            self.assertEqual(gate["status"], "PASS")
            self.assertTrue(gate["complete"] and gate["controls"]["complete"])
        self.assertEqual(len(r.runs), 3328 + 2048 + 1248 + 19008)
        other = Records("aa")
        self.assertFalse(gates_v4.controls(other, 5707)["pass"])
        self.assertTrue(r.v4_controls["pass"])
        self.assertEqual(len(other.runs), 3328)

    def test_control_failure_reaches_every_gate(self):
        for defect in ("aa", "slow", "duplicate"):
            r = Records(defect)
            for gate in (gates_v4.performance(r, 5707), gates_v4.performance(r, 5707, valid=True), gates_v4.sweep(r, 5707)):
                self.assertEqual(gate["status"], "FAIL", (defect, gate["gate"]))
                self.assertFalse(gate["controls"]["pass"])

    def test_real_cost_and_individual_memory_maximum(self):
        r = Records("candidate")
        self.assertEqual(gates_v4.performance(r, 5707, valid=True)["status"], "FAIL")
        r = Records("memory")
        sweep = gates_v4.sweep(r, 5707)
        self.assertEqual(sweep["status"], "FAIL")
        self.assertTrue(sweep["controls"]["pass"])
        self.assertTrue(all(p["memory_growth"] == 64 * gates.MIB for p in sweep["points"]))
        for defect in ("small-warmup", "small-measured"):
            sweep = gates_v4.sweep(Records(defect), 5707)
            self.assertEqual(sweep["status"], "FAIL", defect)
            self.assertTrue(sweep["complete"] and sweep["controls"]["pass"])
            self.assertTrue(all(p["memory_growth"] == 0 and not p["pass"] for p in sweep["points"]))

    def test_timed_natural_completion_keeps_legacy_failure(self):
        r = Cancellation()
        result = gates_v4.cancel(r)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["legacy"]["status"], "FAIL")
        self.assertTrue(all(p["safety"] == "PASS" for p in result["legacy"]["points"]))
        self.assertEqual(len(r.runs), 203)
        for defect in ("late", "late-allocator", "warmup-cleanup", "warmup-memory", "half", "duplicate"):
            self.assertEqual(gates_v4.cancel(Cancellation(defect))["status"], "FAIL", defect)

    def test_timed_fields_fail_closed(self):
        r = Cancellation()
        record = r.run("cand", "PARSE", "V-FLAT-1MiB", 200, "rep0")
        self.assertTrue(gates_v4.timed_record(record, "V-FLAT-1MiB", 200, False)["pass"])
        for section, key, value in (("report", "active_processes", 1), ("report", "exit_confirmed", False),
                                    ("report", "pid", 0), ("final", "parse_ms", 190.),
                                    ("final", "allocator_live_after", 1), ("final", "op", "CANCEL_FIRST")):
            changed = copy.deepcopy(record)
            changed[section][key] = value
            self.assertFalse(gates_v4.timed_record(changed, "V-FLAT-1MiB", 200, False)["pass"], (section, key))


if __name__ == "__main__":
    unittest.main()
