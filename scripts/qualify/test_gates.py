"""Self-test of the CANCEL judgement of gates.py (Session 05-7-1 evidence contract C1, C2). Stdlib unittest.

Usage: python scripts/qualify/test_gates.py

Every case feeds synthetic probe records through a fake runner to the production gates.cancel; no parser runs and
no program starts. The mutants are edits of gates.py's own text that the case matrix must detect. The same matrix
applied to an earlier gates.py (evaluate()) shows which cases that version judged wrongly.
"""
import sys
import types
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gates  # noqa: E402

MIB = 1 << 20
NAN, INF = float("nan"), float("inf")


def pe(parse_ms, cancelled=False, cross=-1.0, callback=False, live=0, peak=0, budget=200.0, **drop):
    event = {"event": "parse", "parse_ms": parse_ms, "cancelled": cancelled, "budget_ms": budget,
             "budget_cross_ms": cross, "cross_at_callback": callback, "live_at_budget": live,
             "peak_after_budget": peak}
    return {k: v for k, v in event.items() if k not in drop}


def rec(parse, cleanup=1.0, completed=True, final=True):
    """A runner record; a cancelled parse has no tree to delete (tree_delete_ms -1, probe.c)."""
    cancelled = parse.get("cancelled") is True
    return {"completed": completed, "final": {"final": True} if final else None,
            "report": {"termination_reason": "COMPLETED" if completed else "MEMORY_LIMIT", "exit_code_raw": 0},
            "events": {"parse": parse, "cleanup": {"tree_delete_ms": -1.0 if cancelled else cleanup,
                                                   "parser_delete_ms": cleanup if cancelled else 0.0}}}


class FakeRunner:
    """Answers gates.cancel's runs: rep0 (warmup) .. rep5 uninstrumented, then the allocator run."""

    def __init__(self, plain, alloc):
        self.plain, self.alloc = plain if isinstance(plain, list) else [plain] * 6, alloc

    def run(self, build, op, case, budget, tag=""):
        assert (op, budget) == ("PARSE", 200)
        return self.alloc if build == "cand-alloc" else self.plain[int(tag[3:])]


CANCELLED = pe(250.0, True, 200.4, True)                  # uninstrumented: crossing at the cancelling callback
ALLOC_X = pe(250.0, True, 200.2, False, 1000, 5000)       # allocator run: crossing at an allocation
ALLOC_CB = pe(250.0, True, 200.3, True, 1000, 1000)       # allocator run: crossing at the callback

# (id, uninstrumented runs, allocator run, actual cancellation required, expected pass, expected point status)
MATRIX = [
    ("C01", rec(pe(180.0)), rec(pe(180.0)), False, True, "NOT_APPLICABLE_BEFORE_BUDGET"),
    ("C02", rec(pe(200.0)), rec(pe(200.0)), False, False, "NOT_RUN_BUDGET_REACHED_UNOBSERVED"),
    ("C03", rec(pe(250.0), 1.0), rec(pe(250.0)), False, False, "NOT_RUN_BUDGET_REACHED_UNOBSERVED"),
    ("C04", rec(CANCELLED), rec(ALLOC_X), True, True, "MEASURED_ALLOCATION_CROSSING"),
    ("C05", rec(CANCELLED), rec(ALLOC_CB), True, True, "MEASURED_CALLBACK_CROSSING"),
    ("C06", rec(CANCELLED), rec(pe(250.0, True)), True, False, "NOT_RUN_BUDGET_REACHED_UNOBSERVED"),
    ("C07", rec(pe(230.0)), rec(pe(230.0)), False, False, "NOT_RUN_BUDGET_REACHED_UNOBSERVED"),
    ("C08-nan-last", [rec(pe(180.0))] * 5 + [rec(pe(NAN))], rec(pe(180.0)), False, False, "MEASUREMENT_INCONSISTENT"),
    ("C08-inf", rec(pe(INF)), rec(pe(180.0)), False, False, "MEASUREMENT_INCONSISTENT"),
    ("C08-null", rec(pe(None)), rec(pe(180.0)), False, False, "MEASUREMENT_INCONSISTENT"),
    ("C08-negative", rec(pe(-1.0)), rec(pe(180.0)), False, False, "MEASUREMENT_INCONSISTENT"),
    ("C08-alloc-nan", rec(pe(180.0)), rec(pe(NAN)), False, False, "MEASUREMENT_INCONSISTENT"),
    ("C08-budget", rec(pe(180.0)), rec(pe(180.0, budget=0.0)), False, False, "MEASUREMENT_INCONSISTENT"),
    ("C09-before-budget", rec(CANCELLED), rec(pe(250.0, True, 150.0, False, 10, 20)), True, False,
     "MEASUREMENT_INCONSISTENT"),
    ("C09-after-return", rec(CANCELLED), rec(pe(250.0, True, 260.0, False, 10, 20)), True, False,
     "MEASUREMENT_INCONSISTENT"),
    ("C09-counter-without-crossing", rec(pe(180.0)), rec(pe(180.0, live=5)), False, False, "MEASUREMENT_INCONSISTENT"),
    ("C10-peak-below-live", rec(CANCELLED), rec(pe(250.0, True, 210.0, False, 5000, 1000)), True, False,
     "MEASUREMENT_INCONSISTENT"),
    ("C10-missing-counter", rec(CANCELLED), rec(pe(250.0, True, 210.0, False, 1000, 5000, live_at_budget=0)), True,
     False, "MEASUREMENT_INCONSISTENT"),
    ("C11", rec(pe(180.0)), rec(pe(180.0)), True, False, "NOT_APPLICABLE_BEFORE_BUDGET"),
    ("C12", rec(pe(220.0, True, 200.1, True)), rec(pe(180.0)), True, False, "NOT_RUN_BUDGET_REACHED_UNOBSERVED"),
    ("C13", rec(pe(180.0)), rec(pe(250.0)), False, False, "NOT_RUN_BUDGET_REACHED_UNOBSERVED"),
    ("C14-return-300", rec(pe(300.0, True, 200.4, True)), rec(ALLOC_X), True, True, "MEASURED_ALLOCATION_CROSSING"),
    ("C14-return-over", rec(pe(300.001, True, 200.4, True)), rec(ALLOC_X), True, False, "MEASURED_ALLOCATION_CROSSING"),
    ("C14-cleanup-100", rec(CANCELLED, 100.0), rec(ALLOC_X), True, True, "MEASURED_ALLOCATION_CROSSING"),
    ("C14-cleanup-over", rec(CANCELLED, 100.001), rec(ALLOC_X), True, False, "MEASURED_ALLOCATION_CROSSING"),
    ("C15-64MiB", rec(CANCELLED), rec(pe(250.0, True, 200.2, False, 1000, 1000 + 64 * MIB)), True, False,
     "MEASURED_ALLOCATION_CROSSING"),
    ("C15-below", rec(CANCELLED), rec(pe(250.0, True, 200.2, False, 1000, 999 + 64 * MIB)), True, True,
     "MEASURED_ALLOCATION_CROSSING"),
    ("C16-no-final", rec(pe(180.0), final=False), rec(pe(180.0)), False, False, "CENSORED"),
    ("C16-cap", rec(pe(180.0)), rec(pe(180.0), completed=False), False, False, "CENSORED"),
]

# Edits of gates.py's text (Session 05-7-1 C2 mutants); each must change the verdict of some matrix case.
MUTANTS = {
    "no elapsed-time reach": ("reached = crossed or cancelled or parse_ms >= budget", "reached = crossed or cancelled"),
    "unobserved counted as growth 0": (
        'return reached, "NOT_RUN_BUDGET_REACHED_UNOBSERVED" if reached else "NOT_APPLICABLE_BEFORE_BUDGET", None,',
        'return reached, "MEASURED_ALLOCATION_CROSSING" if reached else "NOT_APPLICABLE_BEFORE_BUDGET", 0 if reached '
        'else None,'),
    "crossing borrowed from another run": ("budget_run(a, 200)", "budget_run(vals[-1], 200)"),
    "NaN and negative accepted": ("type(x) in (int, float) and math.isfinite(x) and x >= 0", "type(x) in (int, float)"),
    "actual cancellation ignored": ("and (not must_cancel or all(cancelled)))", ")"),
    "NOT_RUN counted as a pass": ('point_status, live_ok = status, status == "NOT_APPLICABLE_BEFORE_BUDGET"',
                                  'point_status, live_ok = status, status != "MEASUREMENT_INCONSISTENT"'),
    "uninstrumented reach ignored": ('elif status == "NOT_APPLICABLE_BEFORE_BUDGET" and plain_reached:', "elif False:"),
}


def judge(module, plain, alloc, must_cancel):
    module.CANCEL_V3, module.CANCEL_ACTUAL = ([], ["X"]) if must_cancel else (["X"], [])
    point = module.cancel(FakeRunner(plain, alloc))["points"][0]
    return point["pass"], point.get("post_budget_live_status")


def evaluate(module):
    """{case id: (pass, status)} of one gates module; an exception counts as its own outcome."""
    out = {}
    for cid, plain, alloc, must, _, _ in MATRIX:
        try:
            out[cid] = judge(module, plain, alloc, must)
        except Exception as e:  # noqa: BLE001  (a crash is a verdict the matrix must see, not a pass)
            out[cid] = ("EXCEPTION", type(e).__name__)
    return out


def mutant(old, new):
    source = (HERE / "gates.py").read_text(encoding="utf-8")
    assert source.count(old) == 1, old
    module = types.ModuleType("gates_mutant")
    exec(compile(source.replace(old, new), "gates_mutant", "exec"), module.__dict__)
    return module


class CancelJudgement(unittest.TestCase):
    def test_matrix(self):
        got = evaluate(gates)
        for cid, _, _, _, want_pass, want_status in MATRIX:
            with self.subTest(cid):
                self.assertEqual(got[cid], (want_pass, want_status))

    def test_each_run_is_judged_by_its_own_records(self):
        # C12: the allocator run's own status stays N/A although the uninstrumented runs were cancelled.
        gates.CANCEL_V3, gates.CANCEL_ACTUAL = [], ["X"]
        point = gates.cancel(FakeRunner(rec(pe(220.0, True, 200.1, True)), rec(pe(180.0))))["points"][0]
        self.assertEqual(point["alloc_memory_status"], "NOT_APPLICABLE_BEFORE_BUDGET")
        self.assertIsNone(point["post_budget_live"])

    def test_mutants_are_detected(self):
        expected = {cid: (p, s) for cid, _, _, _, p, s in MATRIX}
        for name, (old, new) in MUTANTS.items():
            with self.subTest(name):
                got = evaluate(mutant(old, new))
                self.assertTrue([c for c in expected if got[c] != expected[c]], f"mutant not detected: {name}")

    def tearDown(self):
        gates.CANCEL_V3, gates.CANCEL_ACTUAL = CANCEL_V3, CANCEL_ACTUAL


CANCEL_V3, CANCEL_ACTUAL = gates.CANCEL_V3, gates.CANCEL_ACTUAL

if __name__ == "__main__":
    unittest.main()
