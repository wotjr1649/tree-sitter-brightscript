"""Negative controls for the A/A judgement; no parser execution is represented by these records."""
import copy
import tempfile
import unittest
from pathlib import Path

import characterize


def cancellation_record(allocator=False):
    live, peak = (1000, 2000) if allocator else (0, 0)
    return {"completed": True,
            "report": {"termination_reason": "COMPLETED", "exit_code_raw": 0, "exit_confirmed": True,
                       "active_processes": 0, "pid": 1, "creation_filetime": 1},
            "events": {"parse": {"parse_ms": 2., "request_ms": 1., "budget_cross_ms": 1., "budget_ms": 0.,
                                 "callbacks": 1, "callback_target": 1, "cancelled": True, "cross_at_callback": True,
                                 "live_at_budget": live, "peak_after_budget": peak, "live_at_return": live},
                       "cleanup": {"parser_delete_ms": 1., "tree_delete_ms": -1., "allocator_live_after": 0,
                                   "peak_after_budget": peak}},
            "final": {"final": True, "op": "CANCEL_FIRST", "bytes": 100, "cancelled": True, "has_error": -1,
                      "parse_ms": 2., "parser_delete_ms": 1., "tree_delete_ms": -1., "allocator_live_after": 0,
                      "allocator_peak_live": peak, "allocations": 10 if allocator else 0}}


class FirstCallbackControl(unittest.TestCase):
    def test_all_families_run_once_with_unique_processes(self):
        class Runner:
            def __init__(self, duplicate):
                self.calls, self.duplicate = [], duplicate

            def run(self, build, op, case, budget, tag=""):
                self.calls.append((build, op, case, budget, tag))
                assert op == "CANCEL_FIRST" and budget == 0
                r = cancellation_record(build == "cand-alloc")
                r["final"]["bytes"] = len(characterize.gates.cases.generate(case))
                r["report"]["pid"] = (len(self.calls) - 1) % 7 + 1 if self.duplicate else len(self.calls)
                return r

        for duplicate in (False, True):
            r = Runner(duplicate)
            self.assertEqual(characterize.first_callback_control(r)["pass"], not duplicate)
            self.assertEqual(len(r.calls), 49)
            self.assertEqual(len(set(r.calls)), 49)

    def test_missing_and_contradictory_records_fail(self):
        for allocator in (False, True):
            base = cancellation_record(allocator)
            self.assertTrue(characterize.first_callback_record(base, 100, allocator)["pass"])
            sections = (base["report"], base["events"]["parse"], base["events"]["cleanup"], base["final"])
            paths = (("report",), ("events", "parse"), ("events", "cleanup"), ("final",))
            for section, path in zip(sections, paths):
                for key in section:
                    bad = copy.deepcopy(base)
                    target = bad
                    for part in path:
                        target = target[part]
                    del target[key]
                    self.assertFalse(characterize.first_callback_record(bad, 100, allocator)["pass"], (path, key))
            for field in ("parse_ms", "request_ms", "budget_cross_ms"):
                for value in (-1, None, float("inf"), float("nan"), True):
                    bad = copy.deepcopy(base)
                    bad["events"]["parse"][field] = value
                    self.assertFalse(characterize.first_callback_record(bad, 100, allocator)["pass"])
            for section, changes in (("parse", {"callbacks": 0, "callback_target": 2, "cancelled": False,
                                                 "budget_ms": 100., "request_ms": 3., "live_at_return": 99999}),
                                     ("cleanup", {"allocator_live_after": 1, "tree_delete_ms": 0.})):
                for key, value in changes.items():
                    bad = copy.deepcopy(base)
                    bad["events"][section][key] = value
                    self.assertFalse(characterize.first_callback_record(bad, 100, allocator)["pass"])
            for key, value in (("exit_confirmed", False), ("active_processes", 1), ("pid", 0)):
                bad = copy.deepcopy(base)
                bad["report"][key] = value
                self.assertFalse(characterize.first_callback_record(bad, 100, allocator)["pass"])

    def test_latency_growth_and_null_tree_boundaries(self):
        for cleanup in (100., 100.5):
            r = cancellation_record()
            r["events"]["cleanup"]["parser_delete_ms"] = r["final"]["parser_delete_ms"] = cleanup
            self.assertEqual(characterize.first_callback_record(r, 100, False)["pass"], cleanup <= 100)
        for latency in (100., 100.1):
            r = cancellation_record()
            r["events"]["parse"]["parse_ms"] = r["final"]["parse_ms"] = 1. + latency
            self.assertEqual(characterize.first_callback_record(r, 100, False)["pass"], latency <= 100)
        for growth in (64 * 2**20 - 1, 64 * 2**20):
            r = cancellation_record(True)
            r["events"]["parse"]["peak_after_budget"] = r["final"]["allocator_peak_live"] = 1000 + growth
            r["events"]["cleanup"]["peak_after_budget"] = 1000 + growth
            self.assertEqual(characterize.first_callback_record(r, 100, True)["pass"], growth < 64 * 2**20)
        r = cancellation_record(True)
        r["events"]["cleanup"]["peak_after_budget"] = r["final"]["allocator_peak_live"] = 128 * 2**20
        self.assertFalse(characterize.first_callback_record(r, 100, True)["pass"])


class Records:
    def __init__(self, image, query, *, slow=False, wrong=False, censored=False, invalid=None, drop_digest=False,
                 duplicate=False):
        self.probes = {"cand": (image, query)}
        self.slow, self.wrong, self.censored = slow, wrong, censored
        self.invalid, self.drop_digest = invalid, drop_digest
        self.sequence = 0
        self.duplicate = duplicate

    def run(self, build, op, case, budget, tag=""):
        assert build in ("aa-left", "aa-right") and self.probes[build] == self.probes["cand"]
        right = build == "aa-right"
        self.sequence += 1
        t = 2.0 if right and self.slow else 1.0
        if self.invalid and right and tag == self.invalid[0]:
            t = self.invalid[1]
        digest = {} if self.drop_digest else {"digest": "b" * 16 if right and self.wrong else "a" * 16}
        return {"completed": not self.censored,
                "report": {"pid": 1 if self.duplicate else self.sequence, "creation_filetime": 1},
                "final": {"final": True, "bytes": 10, "parse_ms": t, "cancelled": False, "has_error": 0},
                "events": {"navigation": {"navigation_ms": t, "visits": 1, "field_calls": 0, "child_calls": 0,
                                          **digest},
                           "query": {"query_ms": t, "captures": 1, "zero_width_captures": 0, "exceeded": False,
                                     **digest}}}


class SameBinaryControl(unittest.TestCase):
    def test_wrong_work_slow_series_and_censor_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            image, query = Path(directory) / "image", Path(directory) / "query"
            image.write_bytes(b"control identity")
            query.write_bytes(b"control query")
            configs = [{}, {"slow": True}, {"wrong": True}, {"censored": True}, {"drop_digest": True}, {"duplicate": True}]
            configs += [{"invalid": (tag, value)} for tag in ("pair0", "pair5")
                        for value in (-1, 0, float("inf"), float("nan"), None)]
            for config in configs:
                result = characterize.same_binary_control(Records(image, query, **config), 5707)
                self.assertEqual(result["pass"], not config, config)
                self.assertTrue(result["points"])
            more = Records(image, query)
            more.cost_samples = 15
            result = characterize.same_binary_control(more, 5707)
            self.assertTrue(result["pass"])
            self.assertTrue(all(p["observed_count"] == {"aa-left": 16, "aa-right": 16} for p in result["points"]))


if __name__ == "__main__":
    unittest.main()
