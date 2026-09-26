"""Self-test of the CANCEL judgement of gates.py (Session 05-7-1 C1, C2; Session 05-7-2 P572-SEP, contract C1).

Usage: python scripts/qualify/test_gates.py

Every case feeds synthetic probe records through a fake runner to the production gates.cancel_point or gates.cancel;
no parser runs and no program starts. The mutants are edits of gates.py's own text that the cases must detect.
"""
import copy
import itertools
import sys
import types
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gates  # noqa: E402

MIB = 1 << 20
NAN, INF = float("nan"), float("inf")
S, D, A = ("SAFETY",), ("SAFETY", "ACTUAL"), ("ACTUAL",)
CASE = {S: "L-ANON-1MiB", D: "V-FLAT-1MiB", A: "L-FOREACH-1MiB"}   # one real case per role set (valid: V-FLAT)
LENGTH = {}
PIDS = itertools.count(1000)


def pe(parse_ms, cancelled=False, cross=-1.0, callback=False, live=0, peak=0, budget=200.0, **drop):
    event = {"event": "parse", "parse_ms": parse_ms, "cancelled": cancelled, "budget_ms": budget,
             "budget_cross_ms": cross, "cross_at_callback": callback, "live_at_budget": live,
             "peak_after_budget": peak}
    return {k: v for k, v in event.items() if k not in drop}


def rec(parse, cleanup=1.0, completed=True, final=True, tree=None, **final_fields):
    """A runner record; a cancelled parse has no tree to delete (tree_delete_ms -1, probe.c) unless `tree` says.
    The final record's bytes, cancellation and error state are filled per case by the runner unless given here."""
    cancelled = parse.get("cancelled") is True
    tree = (-1.0 if cancelled else cleanup) if tree is None else tree
    return {"completed": completed, "final": final_fields if final else None,
            "report": {"termination_reason": "COMPLETED" if completed else "MEMORY_LIMIT", "exit_code_raw": 0},
            "events": {"parse": parse, "cleanup": {"tree_delete_ms": tree,
                                                   "parser_delete_ms": cleanup if cancelled else 0.0}}}


def fill(template, case):
    """What the probe would print for `case`: the registered length and error state (gates.result_check)."""
    r = copy.deepcopy(template)
    r["report"].update(pid=next(PIDS), creation_filetime=1)
    if r["final"] is not None:
        c = (r["events"].get("parse") or {}).get("cancelled") is True
        n = LENGTH.setdefault(case, len(gates.cases.generate(case)))
        r["final"] = {"final": True, "bytes": n, "cancelled": c,
                      "has_error": -1 if c else 0 if case in gates.VALID_1MIB else 1, **r["final"]}
    return r


class FakeRunner:
    """Answers one point: rep0 (warmup) .. rep5 uninstrumented, then the allocator run, all at one budget."""

    def __init__(self, plain, alloc, budget=200):
        self.plain, self.alloc, self.budget = plain if isinstance(plain, list) else [plain] * 6, alloc, budget

    def run(self, build, op, case, budget, tag=""):
        assert (op, budget) == ("PARSE", self.budget)
        return fill(self.alloc if build == "cand-alloc" else self.plain[int(tag[3:])], case)


class GateRunner:
    """Answers the whole CANCEL gate from per-point templates (case, budget) -> (plain, alloc); logs every request."""

    def __init__(self, points):
        self.points, self.requests = points, []

    def run(self, build, op, case, budget, tag=""):
        self.requests.append((build, op, case, budget, tag))
        plain, alloc = self.points[(case, budget)]
        return fill(alloc if build == "cand-alloc" else plain, case)


CANCELLED = pe(250.0, True, 200.4, True)                  # uninstrumented: crossing at the cancelling callback
ALLOC_X = pe(250.0, True, 200.2, False, 1000, 5000)       # allocator run: crossing at an allocation
ALLOC_CB = pe(250.0, True, 200.3, True, 1000, 1000)       # allocator run: crossing at the callback
C100 = pe(100.2, True, 100.1, True, budget=100.0)         # 100 ms point, cancelled
A100 = pe(101.0, True, 100.05, False, 1000, 9000, budget=100.0)

# (id, uninstrumented runs, allocator run, roles, budget, expected pass, expected memory status)
MATRIX = [
    ("C01", rec(pe(180.0)), rec(pe(180.0)), S, 200, True, "NOT_APPLICABLE_BEFORE_BUDGET"),
    ("C02", rec(pe(200.0)), rec(pe(200.0)), S, 200, False, "NOT_RUN_BUDGET_REACHED_UNOBSERVED"),
    ("C03", rec(pe(250.0), 1.0), rec(pe(250.0)), S, 200, False, "NOT_RUN_BUDGET_REACHED_UNOBSERVED"),
    ("C04", rec(CANCELLED), rec(ALLOC_X), D, 200, True, "MEASURED_ALLOCATION_CROSSING"),
    ("C05", rec(CANCELLED), rec(ALLOC_CB), D, 200, True, "MEASURED_CALLBACK_CROSSING"),
    # A cancelled run without a crossing contradicts probe.c (a cancelling callback records one): S572 review.
    ("C06", rec(CANCELLED), rec(pe(250.0, True)), D, 200, False, "MEASUREMENT_INCONSISTENT"),
    ("C06-alloc-late-natural", rec(CANCELLED), rec(pe(230.0)), D, 200, False, "NOT_RUN_BUDGET_REACHED_UNOBSERVED"),
    ("C07", rec(pe(230.0)), rec(pe(230.0)), S, 200, False, "NOT_RUN_BUDGET_REACHED_UNOBSERVED"),
    ("C08-nan-last", [rec(pe(180.0))] * 5 + [rec(pe(NAN))], rec(pe(180.0)), S, 200, False, "MEASUREMENT_INCONSISTENT"),
    ("C08-inf", rec(pe(INF)), rec(pe(180.0)), S, 200, False, "MEASUREMENT_INCONSISTENT"),
    ("C08-null", rec(pe(None)), rec(pe(180.0)), S, 200, False, "MEASUREMENT_INCONSISTENT"),
    ("C08-negative", rec(pe(-1.0)), rec(pe(180.0)), S, 200, False, "MEASUREMENT_INCONSISTENT"),
    ("C08-alloc-nan", rec(pe(180.0)), rec(pe(NAN)), S, 200, False, "MEASUREMENT_INCONSISTENT"),
    ("C08-budget", rec(pe(180.0)), rec(pe(180.0, budget=0.0)), S, 200, False, "MEASUREMENT_INCONSISTENT"),
    ("C09-before-budget", rec(CANCELLED), rec(pe(250.0, True, 150.0, False, 10, 20)), D, 200, False,
     "MEASUREMENT_INCONSISTENT"),
    ("C09-after-return", rec(CANCELLED), rec(pe(250.0, True, 260.0, False, 10, 20)), D, 200, False,
     "MEASUREMENT_INCONSISTENT"),
    ("C09-counter-without-crossing", rec(pe(180.0)), rec(pe(180.0, live=5)), S, 200, False,
     "MEASUREMENT_INCONSISTENT"),
    ("C10-peak-below-live", rec(CANCELLED), rec(pe(250.0, True, 210.0, False, 5000, 1000)), D, 200, False,
     "MEASUREMENT_INCONSISTENT"),
    ("C10-missing-counter", rec(CANCELLED), rec(pe(250.0, True, 210.0, False, 1000, 5000, live_at_budget=0)), D, 200,
     False, "MEASUREMENT_INCONSISTENT"),
    ("C11", rec(pe(180.0)), rec(pe(180.0)), D, 200, False, "NOT_APPLICABLE_BEFORE_BUDGET"),
    ("C12", rec(pe(220.0, True, 200.1, True)), rec(pe(180.0)), D, 200, False, "NOT_RUN_BUDGET_REACHED_UNOBSERVED"),
    ("C13", rec(pe(180.0)), rec(pe(250.0)), S, 200, False, "NOT_RUN_BUDGET_REACHED_UNOBSERVED"),
    ("C14-return-300", rec(pe(300.0, True, 200.4, True)), rec(ALLOC_X), D, 200, True, "MEASURED_ALLOCATION_CROSSING"),
    ("C14-return-over", rec(pe(300.001, True, 200.4, True)), rec(ALLOC_X), D, 200, False,
     "MEASURED_ALLOCATION_CROSSING"),
    ("C14-cleanup-100", rec(CANCELLED, 100.0), rec(ALLOC_X), D, 200, True, "MEASURED_ALLOCATION_CROSSING"),
    ("C14-cleanup-over", rec(CANCELLED, 100.001), rec(ALLOC_X), D, 200, False, "MEASURED_ALLOCATION_CROSSING"),
    ("C15-64MiB", rec(CANCELLED), rec(pe(250.0, True, 200.2, False, 1000, 1000 + 64 * MIB)), D, 200, False,
     "MEASURED_ALLOCATION_CROSSING"),
    ("C15-below", rec(CANCELLED), rec(pe(250.0, True, 200.2, False, 1000, 999 + 64 * MIB)), D, 200, True,
     "MEASURED_ALLOCATION_CROSSING"),
    ("C16-no-final", rec(pe(180.0), final=False), rec(pe(180.0)), S, 200, False, "CENSORED"),
    ("C16-cap", rec(pe(180.0)), rec(pe(180.0), completed=False), S, 200, False, "CENSORED"),
    ("C09-tree-deleted-when-cancelled", rec(CANCELLED, tree=5.0), rec(ALLOC_X), D, 200, False,
     "MEASUREMENT_INCONSISTENT"),
    ("C09-no-tree-without-cancel", rec(pe(180.0), tree=-1.0), rec(pe(180.0)), S, 200, False,
     "MEASUREMENT_INCONSISTENT"),
    ("C08-non-bool-flag", rec(pe(180.0, cancelled=0)), rec(pe(180.0)), S, 200, False, "MEASUREMENT_INCONSISTENT"),
    # Session 05-7-2 contract C1 (X01-X20 at the point level)
    ("X01-early-dual", rec(pe(170.0)), rec(pe(170.0)), D, 200, False, "NOT_APPLICABLE_BEFORE_BUDGET"),
    ("X01-early-safety", rec(pe(170.0)), rec(pe(170.0)), S, 200, True, "NOT_APPLICABLE_BEFORE_BUDGET"),
    ("X03-foreach-100", rec(C100), rec(A100), A, 100, True, "MEASURED_ALLOCATION_CROSSING"),
    ("X04-no-borrowed-cancel", rec(pe(190.0)), rec(pe(210.0, True, 200.1, False, 10, 20)), D, 200, False,
     "MEASURED_ALLOCATION_CROSSING"),
    ("X04-safety-with-alloc-crossing", rec(pe(190.0)), rec(pe(210.0, True, 200.1, False, 10, 20)), S, 200, True,
     "MEASURED_ALLOCATION_CROSSING"),
    ("X05-alloc-before-100", rec(C100), rec(pe(80.0, budget=100.0)), A, 100, False,
     "NOT_RUN_BUDGET_REACHED_UNOBSERVED"),
    ("X05-safety-reached-alloc-before", rec(CANCELLED), rec(pe(180.0)), S, 200, False,
     "NOT_RUN_BUDGET_REACHED_UNOBSERVED"),
    ("X07-late-natural", rec(pe(301.0)), rec(ALLOC_X), S, 200, False, "MEASURED_ALLOCATION_CROSSING"),
    ("X08-one-natural", [rec(CANCELLED)] * 5 + [rec(pe(190.0))], rec(ALLOC_X), D, 200, False,
     "MEASURED_ALLOCATION_CROSSING"),
    ("X08-warmup-natural", [rec(pe(190.0))] + [rec(CANCELLED)] * 5, rec(ALLOC_X), D, 200, True,
     "MEASURED_ALLOCATION_CROSSING"),
    ("X09-return-200-at-100", rec(pe(200.0, True, 100.1, True, budget=100.0)), rec(A100), A, 100, True,
     "MEASURED_ALLOCATION_CROSSING"),
    ("X09-return-over-at-100", rec(pe(200.001, True, 100.1, True, budget=100.0)), rec(A100), A, 100, False,
     "MEASURED_ALLOCATION_CROSSING"),
    ("X11-cancel-before-crossing", rec(pe(150.0, True, 200.4, True)), rec(ALLOC_X), D, 200, False,
     "MEASUREMENT_INCONSISTENT"),
    ("X11-final-disagrees", rec(CANCELLED, cancelled=False), rec(ALLOC_X), D, 200, False, "MEASUREMENT_INCONSISTENT"),
    ("X12-budget-100-as-200", rec(C100), rec(ALLOC_X), D, 200, False, "MEASUREMENT_INCONSISTENT"),
    ("X14-valid-with-error", rec(pe(170.0), has_error=1), rec(pe(170.0)), D, 200, False,
     "NOT_APPLICABLE_BEFORE_BUDGET"),
    ("X14-short-input", rec(pe(170.0), bytes=4096), rec(pe(170.0)), S, 200, False, "MEASUREMENT_INCONSISTENT"),
    ("X15-error-erased", rec(pe(170.0), has_error=0), rec(pe(170.0)), S, 200, False, "NOT_APPLICABLE_BEFORE_BUDGET"),
    ("X16-callback-ignored-slow", rec(pe(400.0)), rec(pe(420.0, False, 200.0, False, 10, 20)), D, 200, False,
     "MEASURED_ALLOCATION_CROSSING"),
    ("X09-last-measured-over", [rec(CANCELLED)] * 5 + [rec(pe(301.0, True, 200.4, True))], rec(ALLOC_X), D, 200,
     False, "MEASURED_ALLOCATION_CROSSING"),
    ("X11-cancelled-without-crossing", rec(pe(150.0, True)), rec(ALLOC_X), D, 200, False, "MEASUREMENT_INCONSISTENT"),
    ("X15-allocator-error-erased", rec(pe(180.0)), rec(pe(180.0), has_error=0), S, 200, False,
     "NOT_APPLICABLE_BEFORE_BUDGET"),
    ("X15-warmup-error-erased", [rec(pe(180.0), has_error=0)] + [rec(pe(180.0))] * 5, rec(pe(180.0)), S, 200, False,
     "NOT_APPLICABLE_BEFORE_BUDGET"),
    ("X19-uninstrumented-allocation-crossing", rec(pe(250.0, True, 200.2, False, 1000, 2000)), rec(ALLOC_X), D, 200,
     False, "MEASUREMENT_INCONSISTENT"),
    ("X19-warmup-nan", [rec(pe(NAN))] + [rec(pe(180.0))] * 5, rec(pe(180.0)), S, 200, False,
     "MEASUREMENT_INCONSISTENT"),
    ("X19-warmup-counter", [rec(pe(180.0, live=3))] + [rec(pe(180.0))] * 5, rec(pe(180.0)), S, 200, False,
     "MEASUREMENT_INCONSISTENT"),
]
# Coverage and safety of selected cases (the point fields beside pass and memory).
FIELDS = {"X01-early-dual": ("PASS", "NOT_TRIGGERED"), "X01-early-safety": ("PASS", "NOT_REQUIRED"),
          "X03-foreach-100": ("PASS", "TRIGGERED"), "X04-no-borrowed-cancel": ("PASS", "NOT_TRIGGERED"),
          "X08-one-natural": ("PASS", "NOT_ALL_CANCELLED"), "X08-warmup-natural": ("PASS", "TRIGGERED"),
          "X14-valid-with-error": ("FAIL", "NOT_TRIGGERED"), "C04": ("PASS", "TRIGGERED"),
          "C06": ("FAIL", "MEASUREMENT_INCONSISTENT"), "C06-alloc-late-natural": ("FAIL", "ALLOCATOR_GROWTH_UNOBSERVED"),
          "X16-callback-ignored-slow": ("FAIL", "NOT_ALL_CANCELLED")}


def gate_points(over=None):
    """Templates for every registered point: a product that cancels where registered. `over` replaces points."""
    pts = {}
    for case, budget, roles in gates.CANCEL_POINTS:
        if budget == 100:
            pts[(case, budget)] = (rec(C100), rec(A100))
        elif "ACTUAL" in roles:
            pts[(case, budget)] = (rec(CANCELLED), rec(ALLOC_X))
        else:
            pts[(case, budget)] = (rec(pe(170.0)), rec(pe(185.0)))
    pts.update(over or {})
    return pts


# Whole-gate scenarios: (id, point templates, CANCEL_POINTS edit or None, expected gate status)
EARLY = {(c, b): (rec(pe(60.0, budget=float(b))), rec(pe(70.0, budget=float(b)))) for c, b, _ in gates.CANCEL_POINTS}
GATE = [
    ("G-all-registered", gate_points(), None, "PASS"),
    ("X02-all-early", EARLY, None, "FAIL"),
    ("X03-foreach-200-natural-100-cancelled", gate_points(), None, "PASS"),
    ("X13-family-missing", gate_points(), lambda p: p[:-1], "FAIL"),
    ("X13-family-duplicated", gate_points(), lambda p: p + [p[-1]], "FAIL"),
    ("X13-family-replaced", gate_points({("V-FLAT-1MiB", 100): (rec(C100), rec(A100))}),
     lambda p: p[:-1] + [("V-FLAT-1MiB", 100, A)], "FAIL"),
    ("X13-actual-budget-moved", gate_points({(c, 25): (rec(pe(25.2, True, 25.1, True, budget=25.0)),
                                                       rec(pe(26.0, True, 25.05, False, 1000, 2000, budget=25.0)))
                                             for c in gates.ACTUAL_AT_100}),
     lambda p: p[:-2] + [(c, 25, A) for c in gates.ACTUAL_AT_100], "FAIL"),
]


def judge(module, plain, alloc, roles, budget):
    p = module.cancel_point(FakeRunner(plain, alloc, budget), CASE[roles], budget, roles)
    return p["pass"], p.get("memory"), p.get("safety"), p.get("coverage")


def gate(module, points, edit):
    saved = module.CANCEL_POINTS
    if edit:
        module.CANCEL_POINTS = edit(list(saved))
    try:
        runner = GateRunner(points)
        return module.cancel(runner)["status"], runner.requests
    finally:
        module.CANCEL_POINTS = saved


def evaluate(module):
    """{case id: outcome} of one gates module; an exception counts as its own outcome."""
    out = {}
    for cid, plain, alloc, roles, budget, *_ in MATRIX:
        try:
            out[cid] = judge(module, plain, alloc, roles, budget)
        except Exception as e:  # noqa: BLE001  (a crash is a verdict the matrix must see, not a pass)
            out[cid] = ("EXCEPTION", type(e).__name__)
    for gid, points, edit, _ in GATE:
        try:
            out[gid] = (gate(module, points, edit)[0],)
        except Exception as e:  # noqa: BLE001
            out[gid] = ("EXCEPTION", type(e).__name__)
    return out


def mutant(old, new):
    source = (HERE / "gates.py").read_text(encoding="utf-8")
    assert source.count(old) == 1, old
    module = types.ModuleType("gates_mutant")
    exec(compile(source.replace(old, new), "gates_mutant", "exec"), module.__dict__)
    return module


# Edits of gates.py's text (Session 05-7-1 C2 and Session 05-7-2 C1 mutants); each must change some outcome.
MUTANTS = {
    "no elapsed-time reach": ("reached = crossed or cancelled or parse_ms >= budget", "reached = crossed or cancelled"),
    "unobserved counted as growth 0": (
        'return reached, "NOT_RUN_BUDGET_REACHED_UNOBSERVED" if reached else "NOT_APPLICABLE_BEFORE_BUDGET", None,',
        'return reached, "MEASURED_ALLOCATION_CROSSING" if reached else "NOT_APPLICABLE_BEFORE_BUDGET", 0 if reached '
        'else None,'),
    "crossing borrowed from another run": ("reached, status, post, alloc_ms, _ = judged[6]",
                                           "reached, status, post, alloc_ms, _ = judged[5]"),
    "NaN and negative accepted": ("type(x) in (int, float) and math.isfinite(x) and x >= 0", "type(x) in (int, float)"),
    "actual cancellation ignored": ("elif all(cancelled):", "elif True:"),
    "NOT_RUN counted as a pass": ('point_status, live_ok = status, status == "NOT_APPLICABLE_BEFORE_BUDGET"',
                                  'point_status, live_ok = status, status != "MEASUREMENT_INCONSISTENT"'),
    "uninstrumented reach ignored": ('elif status == "NOT_APPLICABLE_BEFORE_BUDGET" and plain_reached:', "elif False:"),
    "tree and cancellation not cross-checked": (
        "not (tree_ms == -1 and cancelled or number(tree_ms) is not None\n" + " " * 58 + "and not cancelled)", "False"),
    "flag types not checked": ("or type(cancelled) is not bool or type(at_callback) is not bool", ""),
    "coverage not required": ('pass_=safety and coverage in ("TRIGGERED", "NOT_REQUIRED"))', "pass_=safety)"),
    "return bound fixed at 300 ms": ("max(ret) <= budget + 100", "max(ret) <= 300"),
    "warmup not checked": ("for j, c, m in zip(judged, checks, mixed))",
                           "for j, c, m in zip(judged[1:], checks[1:], mixed[1:]))"),
    "result state not checked": ('wrong = checks.count("WRONG_RESULT")', "wrong = 0"),
    "bytes and final cancellation not checked": (
        'if f.get("bytes") != length or type(f.get("cancelled")) is not bool or f.get("cancelled") != pe.get('
        '"cancelled"):', "if False:"),
    "point set not checked": ('return result("CANCEL", registered and all(', 'return result("CANCEL", all('),
    "measured runs shifted onto the warmup": ("plain = judged[1:6]", "plain = judged[0:5]"),
    "allocator result not checked": ("checks = [result_check(x, case, length) for x in recs + [a]]",
                                     'checks = [result_check(x, case, length) for x in recs] + ["OK"]'),
    "warmup result not checked": ('wrong = checks.count("WRONG_RESULT")', 'wrong = checks[1:].count("WRONG_RESULT")'),
    "cancelled without crossing accepted": ("bad = at_callback or live != 0 or peak != 0 or cancelled",
                                            "bad = at_callback or live != 0 or peak != 0"),
    "uninstrumented counters not checked": ("mixed = [not uninstrumented(x) for x in recs] + [False]",
                                            "mixed = [False] * 7"),
    "ACTUAL budgets not registered": (
        "and actual == sorted((c, 100 if c in ACTUAL_AT_100 else 200) for c in CANCEL_ACTUAL))",
        "and sorted(c for c, _ in actual) == sorted(CANCEL_ACTUAL))"),
    "allocator growth not required for coverage": (
        'coverage = "TRIGGERED" if point_status.startswith("MEASURED") else "ALLOCATOR_GROWTH_UNOBSERVED"',
        'coverage = "TRIGGERED"'),
}
# Mutants whose verdicts equal the original's on every input, with the reason; they must still change a label.
VERDICT_EQUIVALENT = {
    "allocator growth not required for coverage": "five cancelled runs reached the budget, so an allocator run "
    "without a crossing already makes the growth unobserved and SAFETY fail",
}


class CancelJudgement(unittest.TestCase):
    def test_matrix(self):
        got = evaluate(gates)
        for cid, _, _, _, _, want_pass, want_memory in MATRIX:
            with self.subTest(cid):
                self.assertEqual(got[cid][:2], (want_pass, want_memory))
                if cid in FIELDS:
                    self.assertEqual(got[cid][2:], FIELDS[cid])
        for gid, _, _, want in GATE:
            with self.subTest(gid):
                self.assertEqual(got[gid], (want,))

    def test_each_run_is_judged_by_its_own_records(self):
        # C12: the allocator run's own status stays N/A although the uninstrumented runs were cancelled.
        point = gates.cancel_point(FakeRunner(rec(pe(220.0, True, 200.1, True)), rec(pe(180.0))), "V-FLAT-1MiB", 200, D)
        self.assertEqual(point["alloc_memory_status"], "NOT_APPLICABLE_BEFORE_BUDGET")
        self.assertIsNone(point["post_budget_live"])

    def test_all_early_is_safe_but_not_covered(self):
        # X02, X16: every input finishes before its budget (a callback-ignoring or a much faster product).
        g = gates.cancel(GateRunner(EARLY))
        self.assertEqual(g["status"], "FAIL")
        self.assertTrue(all(p["safety"] == "PASS" for p in g["points"]))
        self.assertEqual(sorted(p["case"] for p in g["points"] if p["coverage"] == "NOT_TRIGGERED"),
                         sorted(gates.CANCEL_ACTUAL))

    def test_points_and_native_runs(self):
        # X17: 15 physical points, 13 SAFETY at 200 ms, 7 ACTUAL families; every native run requested once.
        g = gates.cancel(GateRunner(gate_points()))
        self.assertEqual(g["status"], "PASS")
        keys = [(p["case"], p["budget"], tuple(p["roles"])) for p in g["points"]]
        self.assertEqual(len(keys), 15)
        self.assertEqual([k[:2] for k in keys if "SAFETY" in k[2]], [(c, 200) for c in gates.CANCEL_V3 + gates.CANCEL_ACTUAL])
        self.assertEqual(sorted(k[0] for k in keys if "ACTUAL" in k[2]), sorted(gates.CANCEL_ACTUAL))
        _, requests = gate(gates, gate_points(), None)
        self.assertEqual(len(requests), 15 * 7)
        self.assertEqual(len(set(requests)), 15 * 7)
        ids = [i for p in g["points"] for i in p["run_ids"]["uninstrumented"] + [p["run_ids"]["allocator"]]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_mutants_are_detected(self):
        base = evaluate(gates)
        for name, (old, new) in MUTANTS.items():
            with self.subTest(name):
                got = evaluate(mutant(old, new))
                changed = [c for c in base if got[c] != base[c]]
                self.assertTrue(changed, f"mutant not detected: {name}")
                verdicts = [c for c in changed if got[c][0] != base[c][0]]
                self.assertEqual(bool(verdicts), name not in VERDICT_EQUIVALENT, (name, verdicts))


if __name__ == "__main__":
    unittest.main()
