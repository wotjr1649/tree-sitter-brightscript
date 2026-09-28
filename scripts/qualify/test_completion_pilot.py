"""Synthetic judgement controls; these are not native runtime evidence."""
import unittest
import copy
import re
from pathlib import Path

import completion_pilot as pilot
import completion_runtime
from test_characterize import cancellation_record


def record(op="PARSE", budget=0, allocator=False):
    r = cancellation_record(allocator)
    case = "L-ANON-1MiB"
    r.update(build="completion-alloc" if allocator else "completion", op=op, case=case, budget=budget, tag="test")
    p, c, f = r["events"]["parse"], r["events"]["cleanup"], r["final"]
    length = len(pilot.cases.generate(case))
    p.update(head_gap_ms=1., max_gap_ms=1., tail_gap_ms=1., max_gap_incl_edges_ms=1.,
             byte_target=0, request_byte=0, max_byte_before_request=0, budget_ms=budget)
    f.update(op=op, bytes=length, nodes=0, errors=0, missing=0, max_depth=0, captures=0,
             match_limit_exceeded=False, max_gap_incl_edges_ms=1., allocator_total=3000 if allocator else 0)
    if budget:
        p.update(parse_ms=budget + 1., request_ms=float(budget), budget_cross_ms=float(budget), callback_target=0)
        f["parse_ms"] = budget + 1.
    elif op == "CANCEL_HALF":
        half = (length + 1) // 2
        p.update(callbacks=2, callback_target=0, byte_target=half, request_byte=half, max_byte_before_request=half - 1)
    elif op != "CANCEL_FIRST":
        p.update(cancelled=False, request_ms=-1., budget_cross_ms=-1., cross_at_callback=False,
                 live_at_budget=0, peak_after_budget=0)
        c.update(tree_delete_ms=1., peak_after_budget=0)
        f.update(cancelled=False, has_error=1, tree_delete_ms=1.)
        if op == "QUERY_ONLY":
            r["events"]["query"] = {"query_ms": 1., "compile_ms": 1., "captures": 1,
                                     "zero_width_captures": 0, "exceeded": False, "digest": "a" * 16}
            f.update(query_ms=1., captures=1)
        elif op.startswith("NAV_"):
            r["events"]["navigation"] = {"op": op, "navigation_ms": 1., "visits": 1, "field_calls": 0,
                                          "child_calls": 0, "digest": "a" * 16}
            f.update(navigation_ms=1., nodes=1)
    return r


class CompletionPilot(unittest.TestCase):
    def test_hosted_scope(self):
        text = (Path(__file__).resolve().parents[2] / ".github/workflows/native-characterization.yml").read_text()
        block = text.split("  completion:\n", 1)[1]
        self.assertIn("inputs.experiment == 'completion-gap' || inputs.experiment == 'response-v5') && github.run_attempt == 1", block)
        self.assertIn("github.sha == inputs.expected_commit", block)
        self.assertIn("fromJSON(inputs.experiment == 'completion-gap' && '[\"macos-15\"]'", block)
        self.assertIn("'[\"windows-2025-vs2026\", \"ubuntu-24.04\", \"macos-15\"]'", block)
        self.assertIn("timeout-minutes: 30", block)
        self.assertNotIn("--etw-", block)
        paths = re.search(r"          path: \|\n((?:            [^\n]+\n)+)", block).group(1)
        self.assertEqual([x.strip() for x in paths.splitlines()], [".work/completion-pilot/" + name for name in (
            "identity.json", "runs.jsonl", "commands.jsonl", "completion-pilot.json", "controls-result.txt")]
            + [".work/completion-gap/" + name for name in ("identity.json", "runs.jsonl", "commands.jsonl", "completion-gap.json")]
            + [".work/response-v5/" + name for name in ("identity.json", "gates.json", "runs.jsonl", "commands.jsonl")])

    def test_gap_diagnostic_registration_and_negative_controls(self):
        plan = pilot.gap_registration()
        self.assertEqual(len(plan), 68)
        self.assertEqual(len(set(plan)), 68)
        self.assertEqual([x[0] for x in plan[:4]], list(pilot.GAP_BUILDS))
        self.assertEqual([x[0] for x in plan[4:8]], list(pilot.GAP_BUILDS[1:] + pilot.GAP_BUILDS[:1]))
        base = record()
        self.assertTrue(pilot.gap_record(base))
        base['build'] = 'completion-diagnostic'
        self.assertFalse(pilot.gap_record(base))
        base['events']['diagnostic'] = dict(parse_cpu_ms=1., cleanup_cpu_ms=.5, gap_wall_ms=1., gap_cpu_ms=.5,
                                            gap_from_byte=0, gap_to_byte=10, gap_edge=0, gap_ordinal=1)
        self.assertTrue(pilot.gap_record(base))
        for key, values in {'parse_cpu_ms': (-1., None, float('nan'), True),
                            'gap_wall_ms': (2., float('inf')), 'gap_cpu_ms': (2., -.1),
                            'gap_from_byte': (-1, base['final']['bytes']+1, True),
                            'gap_to_byte': (-1, base['final']['bytes']+1),
                            'gap_edge': (3, 1, 2, True), 'gap_ordinal': (0, 2, True)}.items():
            for value in values:
                bad=copy.deepcopy(base)
                bad['events']['diagnostic'][key]=value
                self.assertFalse(pilot.gap_record(bad), (key,value))
        base['build']='completion'
        self.assertFalse(pilot.gap_record(base))

    def test_registration(self):
        plan = pilot.registered_runs()
        self.assertEqual(len(plan), 192)
        self.assertEqual(len(set(plan)), 192)
        self.assertNotIn(("VALID-calls-004k", "NAV_INDEX"), pilot.API_POINTS)
        self.assertIn(("A5-01-number-k01000", "NAV_INDEX"), pilot.API_POINTS)

    def test_runtime_rejects_other_bytes(self):
        for fn in (completion_runtime.candidate_bytes, completion_runtime.controls_bytes):
            with self.assertRaises(ValueError):
                fn(b"wrong source")

    def test_valid_records(self):
        for allocator in (False, True):
            for op, budget in (("PARSE", 0), ("PARSE", 100), ("CANCEL_FIRST", 0), ("CANCEL_HALF", 0),
                               ("QUERY_ONLY", 0), ("NAV_CURSOR", 0)):
                self.assertTrue(pilot.judge_record(record(op, budget, allocator))["pass"], (op, budget, allocator))

    def test_measurement_mutants(self):
        for key in ("head_gap_ms", "max_gap_ms", "tail_gap_ms", "max_gap_incl_edges_ms", "parse_ms"):
            for value in (float("nan"), float("inf"), -1., None, True):
                r = record()
                r["events"]["parse"][key] = value
                self.assertFalse(pilot.judge_record(r)["pass"], (key, value))
        for key, value in (("parse_ms", 3.), ("bytes", 0), ("op", "QUERY_ONLY"),
                           ("tree_delete_ms", 2.), ("match_limit_exceeded", True)):
            r = record()
            r["final"][key] = value
            self.assertFalse(pilot.judge_record(r)["pass"], (key, value))
        for op, event in (("QUERY_ONLY", "query"), ("NAV_CURSOR", "navigation")):
            for value in ("", "x" * 16, None, 123):
                pair = [record(op), record(op)]
                for r in pair:
                    r["events"][event]["digest"] = value
                self.assertFalse(any(pilot.judge_record(r)["pass"] for r in pair))
        r = record("QUERY_ONLY")
        r["events"]["query"]["exceeded"] = True
        self.assertFalse(pilot.judge_record(r)["pass"])
        for op in ("CANCEL_FIRST", "CANCEL_HALF"):
            r = record(op, allocator=True)
            r["events"]["parse"]["callback_target"] = 2
            self.assertFalse(pilot.judge_record(r)["pass"])

    def test_timed_safety_mutants(self):
        for key in ("parse_ms", "parser_delete_ms"):
            r = record(budget=100)
            section = "parse" if key == "parse_ms" else "cleanup"
            r["events"][section][key] = r["final"][key] = 201.
            self.assertFalse(pilot.judge_record(r)["pass"], key)
        r = record(budget=100)
        r["events"]["parse"]["cancelled"] = r["final"]["cancelled"] = False
        r["events"]["cleanup"]["tree_delete_ms"] = r["final"]["tree_delete_ms"] = 1.
        r["final"]["has_error"] = 1
        self.assertFalse(pilot.judge_record(r)["pass"])
        for cleanup_only in (False, True):
            r = record(budget=100, allocator=True)
            p, c, f = r["events"]["parse"], r["events"]["cleanup"], r["final"]
            peak = p["live_at_budget"] + 64 * pilot.gates.MIB
            c["peak_after_budget"] = f["allocator_peak_live"] = f["allocator_total"] = peak
            if not cleanup_only:
                p["peak_after_budget"] = peak
            self.assertFalse(pilot.judge_record(r)["pass"])


if __name__ == "__main__":
    unittest.main()
