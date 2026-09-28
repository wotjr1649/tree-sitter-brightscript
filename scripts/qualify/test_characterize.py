"""Negative controls for the A/A judgement; no parser execution is represented by these records."""
import copy
import contextlib
import io
import random
import tempfile
import unittest
from pathlib import Path

import characterize


class PairedEstimator(unittest.TestCase):
    def test_registered_plan_has_exactly_6816_executions(self):
        class Records:
            def __init__(self):
                self.probes, self.runs, self.lab = {"cand": ("image", "query")}, [], self

            def input(self, case):
                return Input()

            def run(self, side, op, case, budget, tag=""):
                n = len(self.runs) + 1
                t = 3. if side == "slow" else 1.
                r = {"completed": True, "tag": tag,
                     "report": {"pid": n, "creation_filetime": 1, "exit_confirmed": True, "active_processes": 0,
                                "termination_reason": "COMPLETED", "exit_code_raw": 0},
                     "final": {"final": True, "op": op, "cancelled": False, "has_error": int(case.startswith("SW-")),
                               "bytes": 2, "parse_ms": t, "query_ms": t, "navigation_ms": t},
                     "events": {"parse": {"cancelled": False, "budget_ms": 0, "parse_ms": t},
                                "query": {"query_ms": t, "captures": 1, "zero_width_captures": 0,
                                          "exceeded": False, "digest": "a" * 16},
                                "navigation": {"navigation_ms": t, "visits": 1, "field_calls": 0,
                                               "child_calls": 0, "digest": "a" * 16}}}
                self.runs.append(r)
                return r

        # Give the in-memory input the Path interface used by the real runner.
        class Input:
            def read_bytes(self):
                return b"a\n"

        r = Records()
        with contextlib.redirect_stdout(io.StringIO()):
            result = characterize.paired_diagnosis(r, 5708)
        self.assertTrue(result["complete"] and result["controls_pass"] and result["paired_performance_pass"])
        self.assertEqual(result["native_runs"], 6816)
        self.assertEqual((len(result["aa"]), len(result["cost"]), len(result["growth"])), (103, 103, 46))
        for op in ("PARSE", "QUERY_ONLY", "NAV_CURSOR"):
            record = next(x for x in r.runs if x["final"]["op"] == op)
            for key in ("termination_reason", "exit_code_raw", "pid", "creation_filetime"):
                bad = copy.deepcopy(record)
                del bad["report"][key]
                self.assertIsNone(characterize.work_signature(bad, op, "valid"), (op, key))
            for key, value in (("termination_reason", "WATCHDOG"), ("exit_code_raw", 1), ("pid", 0),
                               ("creation_filetime", None), ("active_processes", 1)):
                bad = copy.deepcopy(record)
                bad["report"][key] = value
                self.assertIsNone(characterize.work_signature(bad, op, "valid"), (op, key, value))
            for key in ("parse_ms", "query_ms" if op == "QUERY_ONLY" else "navigation_ms" if op != "PARSE" else "parse_ms"):
                for value in (None, record["final"][key] + 1, 0, float("inf"), float("nan"), True):
                    bad = copy.deepcopy(record)
                    if value is None:
                        del bad["final"][key]
                    else:
                        bad["final"][key] = value
                    self.assertIsNone(characterize.work_signature(bad, op, "valid"), (op, key, value))

    def test_floor_locations_and_growth_limit(self):
        def series(t):
            return {"valid": True, "values": [t] * 16}

        members, sizes = ("a", "b", "c", "d"), (100, 400, 4000, 20000)
        d = {("cand", case): series(t) for case, t in zip(members, (.01, .02, .04, .2))}
        points = characterize.growth_points(d, members, sizes, "PARSE", 1.5, "sweep")
        self.assertEqual([p["floor_scale"] for p in points], [5., 2.5])
        self.assertTrue(all(p["paired_exponent"] == p["legacy_exponent"] for p in points))
        d = {("cand", case): series(t) for case, t in zip(members[:3], (.001, .01, .09))}
        a5 = characterize.growth_points(d, members[:3], (1, 2, 4), "PARSE", 1.5, "a5")
        valid = characterize.growth_points(d, members[:3], (1, 2, 4), "PARSE", 1.2, "none")
        self.assertTrue(all(not p["applicable"] and p["pass"] for p in a5))
        self.assertTrue(all(p["applicable"] and not p["pass"] for p in valid))
        d[("cand", "a")]["valid"] = False
        self.assertFalse(characterize.growth_points(d, members[:3], (1, 2, 4), "PARSE", 1.5, "a5")[0]["pass"])

    def test_estimand_controls_and_invariance(self):
        # Synthetic judge controls, not parser-performance evidence.
        left = [1.] + [1.] * 8 + [3.] * 7
        right = [1.] + [1.] * 7 + [3.] * 8
        e = characterize.paired_estimates(left, right)
        self.assertEqual(e["paired_ratio"], 1.)
        self.assertEqual(e["legacy_ratio"], 1 / 3)
        swapped = characterize.paired_estimates(right, left)
        scaled = characterize.paired_estimates([x * 1000 for x in left], [x * 1000 for x in right])
        self.assertEqual(swapped["paired_ratio"], 1 / e["paired_ratio"])
        self.assertEqual(scaled["paired_ratio"], e["paired_ratio"])
        for factor in (1.5, 1.5001, 2.):
            e = characterize.paired_estimates([x * factor for x in left], left)
            self.assertEqual(e["paired_ratio"] <= 1.5, factor <= 1.5)
        for value in (-1, 0, None, True, float("inf"), float("nan")):
            for index in (0, 15):
                bad = list(left)
                bad[index] = value
                self.assertFalse(characterize.paired_estimates(bad, right)["valid"])
        self.assertFalse(characterize.paired_estimates(left[:-1], right)["valid"])
        self.assertFalse(characterize.paired_estimates([1e308] * 16, [1e-308] * 16)["valid"])

    def test_round_identity_and_work_are_required(self):
        class Runner:
            def __init__(self, path, defect):
                self.path, self.defect, self.calls = path, defect, []

            def input(self, case):
                return self.path

            def run(self, side, op, case, budget, tag=""):
                self.calls.append((side, op, case, budget, tag))
                n = len(self.calls)
                return {"completed": True, "tag": "round0" if self.defect == "tag" else tag,
                        "report": {"pid": 1 if self.defect == "duplicate" else n, "creation_filetime": 1,
                                   "exit_confirmed": self.defect != "exit", "active_processes": 0,
                                   "termination_reason": "COMPLETED", "exit_code_raw": 0},
                        "final": {"final": True, "op": op, "cancelled": False, "has_error": 0,
                                  "bytes": 3 if self.defect == "bytes" else 2, "parse_ms": 1.},
                        "events": {"parse": {"cancelled": False, "budget_ms": 0, "parse_ms": 1.}}}

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input"
            path.write_bytes(b"a\n")
            for defect in (None, "tag", "duplicate", "exit", "bytes"):
                r = Runner(path, defect)
                d = characterize.measure_rounds(r, ("cand", "h"), ("small", "middle", "big"), "PARSE", random.Random(7))
                self.assertEqual(len(r.calls), 96)
                self.assertEqual(len(set(r.calls)), 96)
                self.assertEqual(all(p["valid"] for p in d.values()), defect is None)
                self.assertEqual(all(p["pass"] for p in characterize.cost_points(d, ("cand", "h"),
                                                                                 ("small", "middle", "big"), "PARSE")),
                                 defect is None)
                if defect is None:
                    d[("cand", "middle")]["values"] = [2.] * 16
                    d[("cand", "big")]["values"] = [4.] * 16
                    g = characterize.growth_points(d, ("small", "middle", "big"), (1, 2, 4), "PARSE", 1.2, "none")
                    self.assertTrue(all(p["pass"] and p["paired_exponent"] == 1 for p in g))
                    self.assertEqual(len(r.calls), 96)  # contrasts reuse the middle-size observation


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
