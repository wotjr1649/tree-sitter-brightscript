"""Prospective v5 controls; synthetic records do not qualify native execution."""
import copy
import hashlib
import json
import unittest

import characterize
import gates
import gates_v4
import response_policy as policy
from run import retained_run
from test_completion_pilot import record
from test_gates_v4 import Cancellation


class CancellationRecords(Cancellation):
    def run(self, *args, **kwargs):
        r = super().run(*args, **kwargs)
        p, f = r["events"]["parse"], r["final"]
        p.update(head_gap_ms=.5, max_gap_ms=.5, tail_gap_ms=.5, max_gap_incl_edges_ms=.5)
        f["max_gap_incl_edges_ms"] = .5
        if r["build"] == "cand":
            r["events"]["cleanup"]["parser_delete_ms"] = f["parser_delete_ms"] = 175.
        return r


class PlainRecords:
    def __init__(self, value=175., defect=None):
        self.runs, self.lab, self.value, self.defect = [], self, value, defect

    def run(self, build, op, case, budget, tag=""):
        r = record(budget=budget)
        r.update(build=build, op=op, case=case, budget=budget, tag=tag)
        p, c, f = r["events"]["parse"], r["events"]["cleanup"], r["final"]
        r["report"]["pid"] = len(self.runs) + 1
        p.update(parse_ms=budget + self.value + 1, head_gap_ms=.5, max_gap_ms=self.value,
                 tail_gap_ms=.5, max_gap_incl_edges_ms=self.value)
        f.update(bytes=len(gates.cases.generate(case)), parse_ms=p["parse_ms"], max_gap_incl_edges_ms=self.value,
                 has_error=-1 if budget else 0 if case in gates.VALID_1MIB else 1)
        if not budget:
            c["tree_delete_ms"] = f["tree_delete_ms"] = self.value - 1.
        if self.defect and len(self.runs) == 1:
            p["max_gap_ms"] = self.defect
        self.runs.append(retained_run(r))
        return r


class ResponsePolicy(unittest.TestCase):
    def test_exact_policy_and_mutations(self):
        good = {"protocol": policy.PROTOCOL, "response_policy": copy.deepcopy(policy.IDENTITY)}
        policy.require_identity(good)
        for protocol in ("v4", "v4.1", "v6", None):
            with self.assertRaises(ValueError):
                policy.require_identity(dict(good, protocol=protocol))
        for limit in (100, 249, 251, 500):
            bad = copy.deepcopy(good)
            spec = bad["response_policy"]["spec"]
            spec["limits_ms"]["callback_gap_ms"] = limit
            bad["response_policy"]["sha256"] = hashlib.sha256(json.dumps(spec, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            with self.assertRaises(ValueError):
                policy.require_identity(bad)

    def test_default_and_explicit_historical_judgements_equal(self):
        self.assertEqual(gates_v4.cancel(Cancellation()), gates_v4.cancel(Cancellation(), response_ms=100))
        for judge in (gates.overshoot, gates.gaps_and_cleanup):
            self.assertEqual(judge(PlainRecords()), judge(PlainRecords(), response_ms=100))

    def test_collect_once_keep_legacy_failure_and_compact_records(self):
        r = CancellationRecords()
        current = policy.evaluate(r, gates_v4.cancel)
        self.assertEqual(current["status"], "PASS")
        self.assertEqual(current["legacy_v4_1_100ms"]["status"], "FAIL")
        self.assertEqual(len(r.runs), 278)
        for judge in (gates.overshoot, gates.gaps_and_cleanup):
            r = PlainRecords()
            result = policy.evaluate(r, judge)
            active = result if isinstance(result, list) else [result]
            self.assertTrue(all(x["status"] == "PASS" and x["legacy_v4_1_100ms"]["status"] == "FAIL" for x in active))
            if judge == gates.gaps_and_cleanup:
                self.assertNotIn("events", r.runs[0])
            else:
                self.assertEqual(len(r.runs), len(gates.CANCEL_SET + gates.LARGE_SET) * len(gates.BUDGETS) * 4)

    def test_250_boundaries_and_safety(self):
        for value in (250., 250.001):
            r = record(budget=100)
            r["events"]["parse"]["parse_ms"] = r["final"]["parse_ms"] = 100 + value
            self.assertEqual(gates_v4.timed_record(r, r["case"], 100, False, response_ms=250)["pass"], value == 250)
            r = record(budget=100)
            r["events"]["cleanup"]["parser_delete_ms"] = r["final"]["parser_delete_ms"] = value
            self.assertEqual(gates_v4.timed_record(r, r["case"], 100, False, response_ms=250)["pass"], value == 250)
            for op in ("CANCEL_FIRST", "CANCEL_HALF"):
                r = record(op)
                r["events"]["parse"]["parse_ms"] = r["final"]["parse_ms"] = 1 + value
                self.assertEqual(characterize.first_callback_record(r, r["final"]["bytes"], False,
                    progressed=op == "CANCEL_HALF", response_ms=250)["pass"], value == 250)
            result = policy.evaluate(PlainRecords(value), gates.gaps_and_cleanup)
            self.assertEqual([x["status"] for x in result], ["PASS" if value == 250 else "FAIL"] * 2)
        for defect in ("late", "late-allocator", "extra-miss", "extra-growth", "extra-unobserved", "extra-censored", "duplicate"):
            self.assertEqual(gates_v4.cancel(Cancellation(defect), response_ms=250)["status"], "FAIL", defect)

    def test_invalid_records_and_replay_registration_fail_closed(self):
        for value in (float("nan"), float("inf"), -1.):
            with self.assertRaisesRegex(ValueError, "invalid v5"):
                policy.evaluate(PlainRecords(defect=value), gates.gaps_and_cleanup)
        r = record()
        r["report"]["active_processes"] = False
        self.assertFalse(policy.valid_record(r))
        replay = policy.Replay([record()])
        with self.assertRaises(ValueError):
            replay.run("wrong", "PARSE", "L-ANON-1MiB", 0)

    def test_overshoot_preserves_return_bound_and_separate_cancel_purpose(self):
        class LateNatural(PlainRecords):
            def run(self, *args, **kwargs):
                r = super().run(*args, **kwargs)
                if r["tag"] == target:
                    r["events"]["parse"].update(cancelled=False, budget_cross_ms=-1., cross_at_callback=False,
                                               live_at_budget=0, peak_after_budget=0)
                    r["events"]["cleanup"]["tree_delete_ms"] = 1.
                    r["final"].update(cancelled=False, has_error=0 if r["case"] in gates.VALID_1MIB else 1,
                                      tree_delete_ms=1.)
                    if at_budget:
                        r["events"]["parse"]["parse_ms"] = r["final"]["parse_ms"] = r["budget"]
                return r
        for target, value, at_budget in (("b25", 50., False), ("b25-again0", 175., False), ("b100", 50., True)):
            result = policy.evaluate(LateNatural(value), gates.overshoot)
            self.assertEqual(result["status"], "PASS")
            self.assertTrue(all(x["pass"] for x in result["individual_runs"]))
            self.assertTrue(any(x["status"] == "NATURAL_WITHIN_RETURN_BOUND" for x in result["individual_runs"]))
            if target in ("b25", "b100"):
                self.assertEqual(result["legacy_v4_1_100ms"]["status"], "PASS")
        for value, expected in ((249., "PASS"), (249.001, "FAIL")):
            # PlainRecords returns B + value + 1: exact 250 ms and just over it.
            target, at_budget = "b25", False
            self.assertEqual(policy.evaluate(LateNatural(value), gates.overshoot)["status"], expected)
        bad = record(budget=25)
        bad.update(build="cand", op="PARSE")
        bad["events"]["parse"]["cancelled"] = False
        self.assertFalse(policy.overshoot_record(bad)["pass"])


if __name__ == "__main__":
    unittest.main()
