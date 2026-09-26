"""Release gates of the qualification lane (validation.md, "Release qualification lane").

Bounds are those of protocol v3 (Session 05-2, resume-08) and are never relaxed here. Each gate is a function
of a runner that measures one (build, op, case, budget) under the supervisor and returns the parsed record;
it returns {"gate", "status" (PASS, FAIL, NOT_RUN), "points", "notes"}. Censored points (memory cap, watchdog,
crash, harness failure) count as failures. Stdlib only; starts no program.
"""
import math
import random
import statistics

import cases

MIB = 1 << 20
FLOOR_MS = 0.1

B5_01 = ["B5-01-prefix-k00100", "B5-01-prefix-k00200", "B5-01-prefix-k00400", "B5-01-prefix-k00800",
         "B5-01-minus-k00100", "B5-01-minus-k00200", "B5-01-minus-k00400", "B5-01-minus-k00800",
         "B5-01-aa-k00150", "B5-01-aa-k00300", "B5-01-aa-k00600"]
B5_02 = [f"B5-02-{f}-k{k:05d}" for f in ("call", "sep") for k in (1000, 2000, 4000, 10000, 15000, 20000)]
B5_02_NONPRINT = [f"B502X-k{k:05d}" for k in (1000, 2000, 4000, 20000)]
A5_01 = [f"A5-01-k{k:05d}" for k in (1000, 2000, 4000, 8000, 16000, 32000)] + \
        [f"A5-01-number-k{k:05d}" for k in (1000, 2000, 4000, 8000, 16000, 32000)]
A501J = [f"A501J-k{k:05d}" for k in (1000, 2000, 4000, 8000)]
CANCEL_V3 = ["B5-01-prefix-k00800", "B5-01-minus-k00800", "B5-01-aa-k00600", "B5-02-call-k20000", "B5-02-sep-k20000",
             "KL2-plusstar-k08000"]
CANCEL_SET = CANCEL_V3 + ["SW-z203d207bk3a20-7ba3a402a7d3c-colon-k20000", "REVB-aaz-colon-k40000", "B5-01-prefix-k16000"]
# The families whose actual cancellation CANCEL requires; registered in ec14a17 as parsing longer than 200 ms, which
# S571 q1 found false for L-FOREACH and L-ANON (the v3 CANCEL cases finish before the budget on a fast candidate).
CANCEL_ACTUAL = ["V-FLAT-1MiB", "V-ARRAY-1MiB", "V-CALLS-1MiB", "V-PRINT-1MiB", "L-WHILE-1MiB", "L-FOREACH-1MiB",
                 "L-ANON-1MiB"]
# P572-SEP (Session 05-7-2, DEV-572): every case keeps its 200 ms point, judged for SAFETY; ACTUAL cancellation is
# required at 200 ms for five families and at a fixed 100 ms point for the two that finished before 200 ms in S571
# q1 (a value chosen after that result). A point is one (case, budget) with its own runs.
ACTUAL_AT_100 = ["L-FOREACH-1MiB", "L-ANON-1MiB"]
CANCEL_POINTS = [(c, 200, ("SAFETY", "ACTUAL") if c in CANCEL_ACTUAL and c not in ACTUAL_AT_100 else ("SAFETY",))
                 for c in CANCEL_V3 + CANCEL_ACTUAL] + [(c, 100, ("ACTUAL",)) for c in ACTUAL_AT_100]
LARGE_SET = [f"{c}-1MiB" for c in cases.LARGE_MALFORMED]
VALID_1MIB = [f"{c}-1MiB" for c in cases.LARGE_VALID]
BUDGETS = [25, 50, 100, 200, 300, 500, 1000, 2000, 4000]
QUERY_MALFORMED = ["Q-INDEX-MEMBER", "Q-NEG-PAREN-IDX", "Q-PAREN-NEG", "Q-TRY", "Q-PAREN", "Q-ARR"]
VALID_FAMILIES = ["flat-assign", "nested-if", "array", "aa", "long-expr", "calls"]
KL002_UNITS = {"+*", "2^*", "(not)"}  # the units of the retired KL-002, reported separately


def exponent(t1, t2, n1, n2):
    return math.log(t2 / t1) / math.log(n2 / n1) if t1 > 0 and t2 > 0 else None


def result(gate, ok, points, notes=(), status=None):
    return {"gate": gate, "status": status or ("PASS" if ok else "FAIL"), "points": points, "notes": list(notes)}


def completed(rec):
    return rec["completed"] and rec["final"] is not None


def med(values):
    return statistics.median(values) if values else None


def timed(r, build, op, case, n, metric, budget=0, warmup=1):
    """n measured runs after `warmup`; returns (values, records). A censored run ends the series."""
    values, records = [], []
    for i in range(warmup + n):
        rec = r.run(build, op, case, budget, tag=f"rep{i}")
        records.append(rec)
        if not completed(rec):
            return None, records
        if i >= warmup:
            values.append(metric(rec))
    return values, records


def m_parse(rec):
    return rec["events"]["parse"]["parse_ms"]


def m_query(rec):
    return rec["events"]["query"]["query_ms"]


def m_nav(rec):
    return rec["events"]["navigation"]["navigation_ms"]


# ------------------------------------------------------------------ B5-01
def b5_01_memory(r):
    points, ok = [], True
    live = {}
    for case in B5_01:
        a = r.run("cand-alloc", "PARSE", case, 0, tag="alloc")
        ws, recs = timed(r, "cand", "PARSE", case, 5, lambda x: x["report"]["peak_working_set_bytes"]
                         - x["events"]["idle"]["working_set_bytes"])
        p = {"case": case, "allocator_peak_live": a["final"]["allocator_peak_live"] if completed(a) else None,
             "ws_delta_median": med(ws) if ws else None, "censored": not completed(a) or ws is None}
        p["pass"] = not p["censored"] and p["allocator_peak_live"] < 64 * MIB and p["ws_delta_median"] < 64 * MIB
        live[case] = p["allocator_peak_live"]
        ok &= p["pass"]
        points.append(p)
    pairs = []
    # Every consecutive pair of each family's series, without exemption (Session 05-7 reviews B-11, B2-02).
    for fam, ks in (("prefix", (100, 200, 400, 800)), ("minus", (100, 200, 400, 800)), ("aa", (150, 300, 600))):
        for k0, k1 in zip(ks, ks[1:]):
            a, b = live[f"B5-01-{fam}-k{k0:05d}"], live[f"B5-01-{fam}-k{k1:05d}"]
            e = exponent(a, b, k0, k1) if a and b else None
            pairs.append({"family": fam, "sizes": (k0, k1), "exponent": e, "pass": e is not None and e <= 1.5})
            ok &= pairs[-1]["pass"]
    return result("B5-01-MEMORY", ok, points + pairs)


# ------------------------------------------------------------------ B5-02
def b5_02_lifecycle(r):
    points, ok = [], True
    series = {}
    for case in B5_02 + B5_02_NONPRINT:
        small = case.endswith(("k01000", "k02000", "k04000"))
        if small:
            vals, recs = timed(r, "cand", "LIFECYCLE", case, 5, m_parse)
        else:
            rec = r.run("cand", "LIFECYCLE", case, 0)
            vals, recs = ([m_parse(rec)] if completed(rec) else None), [rec]
        last = recs[-1]
        p = {"case": case, "completed": vals is not None, "exit_code": last["report"]["exit_code_raw"],
             "termination": last["report"]["termination_reason"], "parse_median_ms": med(vals) if vals else None,
             "peak_commit": last["report"]["peak_commit_bytes"]}
        p["pass"] = p["completed"]
        ok &= p["pass"]
        series[case] = p["parse_median_ms"]
        points.append(p)
    t1, t4 = series.get("B5-02-call-k01000"), series.get("B5-02-call-k04000")
    e = exponent(t1, t4, 1000, 4000) if t1 and t4 else None
    below = t4 is not None and t4 < FLOOR_MS
    points.append({"check": "call exponent 1,000 -> 4,000", "exponent": e, "pass": below or (e is not None and e <= 1.5)})
    ok &= points[-1]["pass"]
    return result("B5-02-LIFECYCLE", ok, points, ["B502X (x = -f(-)) is the registered non-PRINT witness (E3)"])


# ------------------------------------------------------------------ A5-01
def paired(r, cand, ref, op, case, n, metric, rng):
    """Candidate and reference alternately in random order; 1 warmup + n each."""
    vals = {cand: [], ref: []}
    recs = {cand: [], ref: []}
    for i in range(n + 1):
        order = [cand, ref]
        rng.shuffle(order)
        for b in order:
            rec = r.run(b, op, case, 0, tag=f"pair{i}")
            recs[b].append(rec)
            if not completed(rec):
                return None, recs
            if i > 0:
                vals[b].append(metric(rec))
    return {b: med(v) for b, v in vals.items()}, recs


def a5_01_cost(r, seed):
    rng = random.Random(seed)
    points, ok = [], True
    ops = {"QUERY_ONLY": m_query, "NAV_CURSOR": m_nav, "NAV_FIELD": m_nav, "NAV_INDEX": m_nav}
    series = {}
    for case in A5_01 + A501J:
        for op, metric in ops.items():
            meds, recs = paired(r, "cand", "bp", op, case, 5, metric, rng)
            p = {"case": case, "op": op}
            if meds is None:
                p.update(censored=True, pass_=False)
            else:
                c, b = meds["cand"], meds["bp"]
                last_c, last_b = recs["cand"][-1]["events"], recs["bp"][-1]["events"]
                if op == "QUERY_ONLY":
                    same = (last_c["query"]["captures"], last_c["query"]["digest"]) == (last_b["query"]["captures"],
                                                                                         last_b["query"]["digest"])
                    same = same and not any(x["events"]["query"]["exceeded"] for x in recs["cand"] + recs["bp"])
                else:
                    nc, nb = last_c["navigation"], last_b["navigation"]
                    same = (nc["digest"], nc["visits"], nc["child_calls"]) == (nb["digest"], nb["visits"], nb["child_calls"])
                ratio = c / b if b >= FLOOR_MS else None
                p.update(cand_median=c, ref_median=b, ratio=ratio, same_work=same,
                         pass_=same and (ratio is None or ratio <= 1.5))
                series[(case.rsplit("-k", 1)[0], op, int(case.rsplit("-k", 1)[1]))] = c
            p["pass"] = p.pop("pass_")
            ok &= p["pass"]
            points.append(p)
    for fam, ks in (("A5-01", (8000, 16000, 32000)), ("A5-01-number", (8000, 16000, 32000)),
                    ("A501J", (2000, 4000, 8000))):
        for op in ops:
            t = [series.get((fam, op, k)) for k in ks]
            es = [exponent(t[i], t[i + 1], ks[i], ks[i + 1]) if t[i] and t[i + 1] and t[i + 1] >= FLOOR_MS else None
                  for i in range(2)]
            p = {"family": fam, "op": op, "sizes": ks, "exponents": es,
                 "pass": all(e is None or e <= 1.5 for e in es) and None not in t}
            ok &= p["pass"]
            points.append(p)
    return result("A5-01-COST", ok, points, ["reference BEFORE_PRINT (8e2ad7c) cross-measured in the same batch",
                                             "same_work: role digest and capture count, or tree digest, visits and child calls"])


# ------------------------------------------------------------------ cancellation, gaps, cleanup
def number(x):
    """A finite non-negative number, else None: a missing, null, NaN, infinite or negative value is never 0."""
    return x if type(x) in (int, float) and math.isfinite(x) and x >= 0 else None


def budget_run(rec, budget):
    """One execution judged by its own records alone (gate contract CANCEL; Session 05-7-1 C1).

    Returns (reached, status, growth, parse_ms, cleanup_ms). The budget is reached if this run recorded a crossing,
    was cancelled, or took at least the budget. The crossing is taken at the first allocation (allocator build) or
    progress callback after the budget, whichever comes first (probe.c); a reached budget without one leaves the
    growth after the budget unmeasured (NOT_RUN), never 0. Values that contradict each other fail closed."""
    pe, cl = rec["events"].get("parse") or {}, rec["events"].get("cleanup") or {}
    parse_ms, cross, pbudget = number(pe.get("parse_ms")), pe.get("budget_cross_ms"), pe.get("budget_ms")
    cancelled, at_callback = pe.get("cancelled"), pe.get("cross_at_callback")
    live, peak = pe.get("live_at_budget"), pe.get("peak_after_budget")
    tree_ms, parser_ms = cl.get("tree_delete_ms"), number(cl.get("parser_delete_ms"))
    bad = (parse_ms is None or parser_ms is None or number(budget) is None or budget <= 0 or pbudget != budget
           or type(cancelled) is not bool or type(at_callback) is not bool or type(live) is not int or live < 0
           or type(peak) is not int or peak < 0 or not (tree_ms == -1 and cancelled or number(tree_ms) is not None
                                                          and not cancelled))
    crossed = not bad and cross != -1
    if not bad and crossed:
        bad = number(cross) is None or not budget <= cross <= parse_ms or peak < live
    elif not bad:
        # A cancellation is requested only by a callback after the budget, which records a crossing (probe.c).
        bad = at_callback or live != 0 or peak != 0 or cancelled
    if bad:
        return True, "MEASUREMENT_INCONSISTENT", None, parse_ms, None
    cleanup = (0 if cancelled else tree_ms) + parser_ms
    reached = crossed or cancelled or parse_ms >= budget
    if crossed:
        status = "MEASURED_CALLBACK_CROSSING" if at_callback else "MEASURED_ALLOCATION_CROSSING"
        return True, status, peak - live, parse_ms, cleanup
    return reached, "NOT_RUN_BUDGET_REACHED_UNOBSERVED" if reached else "NOT_APPLICABLE_BEFORE_BUDGET", None, \
        parse_ms, cleanup


def run_id(rec):
    """One native execution: the supervisor's process id and creation time."""
    return f"{rec['report'].get('pid')}@{rec['report'].get('creation_filetime')}"


def uninstrumented(rec):
    """An uninstrumented run counts no allocations: no allocator counters, and a crossing only at the callback."""
    pe = rec["events"].get("parse") or {}
    return pe.get("live_at_budget") == 0 and pe.get("peak_after_budget") == 0 and (
        pe.get("budget_cross_ms") == -1 or pe.get("cross_at_callback") is True)


def result_check(rec, case, length):
    """A run's final record against its parse event and the registered input (Session 05-7-2 A-03): the byte count,
    the cancellation, and the error state: -1 for a cancelled parse (no tree), else 0 for the valid 1 MiB inputs and
    1 for the malformed cases. A parse that is not cancelled returns the whole input's tree; the frozen probe reports
    no root span. Returns OK, MEASUREMENT_INCONSISTENT or WRONG_RESULT."""
    f, pe = rec["final"] or {}, rec["events"].get("parse") or {}
    if f.get("bytes") != length or type(f.get("cancelled")) is not bool or f.get("cancelled") != pe.get("cancelled"):
        return "MEASUREMENT_INCONSISTENT"
    want = -1 if f["cancelled"] else 0 if case in VALID_1MIB else 1
    return "OK" if type(f.get("has_error")) is int and f["has_error"] == want else "WRONG_RESULT"


def cancel_point(r, case, budget, roles):
    """One registered point: 1 warmup + 5 uninstrumented runs, then one allocator run, all at `budget`.

    SAFETY: no censored, inconsistent or wrong run (warmup and allocator included); the 5 measured runs return within
    budget + 100 ms and clean up within 100 ms; growth after the budget below 64 MiB where measured, and never
    unobserved where a run reached the budget. ACTUAL also: all 5 measured runs cancelled (the warmup is no
    substitute) and the allocator run's growth measured at its own crossing (Session 05-7-2 P572-SEP)."""
    vals, recs = timed(r, "cand", "PARSE", case, 5, lambda x: x, budget=budget)
    a = r.run("cand-alloc", "PARSE", case, budget, tag="alloc")
    actual = "ACTUAL" in roles
    p = {"case": case, "budget": budget, "roles": list(roles), "source_sha": cases.RECORDED["cases"][case],
         "required_count": 5, "run_ids": {"uninstrumented": [run_id(x) for x in recs], "allocator": run_id(a)}}
    if vals is None or not completed(a):
        p.update(censored_count=sum(not completed(x) for x in recs + [a]), safety="CENSORED",
                 coverage="CENSORED" if actual else "NOT_REQUIRED", memory="CENSORED", pass_=False)
    else:
        # Return, cleanup and cancellation from the uninstrumented runs; growth after the budget from the
        # allocator run; each run's budget, time and crossing from its own records, never from another run's.
        length = len(cases.generate(case))
        judged = [budget_run(x, budget) for x in recs + [a]]          # warmup, 5 measured, allocator
        checks = [result_check(x, case, length) for x in recs + [a]]
        mixed = [not uninstrumented(x) for x in recs] + [False]    # allocator evidence in an uninstrumented run
        inconsistent = sum(j[1] == "MEASUREMENT_INCONSISTENT" or c == "MEASUREMENT_INCONSISTENT" or m
                           for j, c, m in zip(judged, checks, mixed))
        wrong = checks.count("WRONG_RESULT")
        plain = judged[1:6]
        reached, status, post, alloc_ms, _ = judged[6]
        cancelled = [(v["events"].get("parse") or {}).get("cancelled") is True for v in vals]
        ret, cleanup = [x[3] for x in plain], [x[4] for x in plain]
        plain_reached = sum(x[0] for x in plain)
        if inconsistent:
            point_status, live_ok = "MEASUREMENT_INCONSISTENT", False
        elif status.startswith("MEASURED"):
            point_status, live_ok = status, post < 64 * MIB
        elif status == "NOT_APPLICABLE_BEFORE_BUDGET" and plain_reached:
            # The allocator run finished before the budget but uninstrumented runs reached it: their growth
            # after the budget is unmeasured, and the allocator run's N/A is not borrowed for them.
            point_status, live_ok = "NOT_RUN_BUDGET_REACHED_UNOBSERVED", False
        else:
            point_status, live_ok = status, status == "NOT_APPLICABLE_BEFORE_BUDGET"
        safety = not inconsistent and not wrong and max(ret) <= budget + 100 and max(cleanup) <= 100 and live_ok
        natural_before = sum(not x[0] for x in plain)
        if not actual:
            coverage = "NOT_REQUIRED"
        elif inconsistent:
            coverage = "MEASUREMENT_INCONSISTENT"
        elif all(cancelled):
            coverage = "TRIGGERED" if point_status.startswith("MEASURED") else "ALLOCATOR_GROWTH_UNOBSERVED"
        else:
            coverage = "NOT_TRIGGERED" if natural_before == 5 else "NOT_ALL_CANCELLED"
        p.update(observed_count=len(vals), triggered_count=sum(cancelled), natural_before_count=natural_before,
                 late_natural_count=sum(x[0] and not c for x, c in zip(plain, cancelled)), censored_count=0,
                 inconsistent_count=inconsistent, wrong_result_count=wrong,
                 warmup_cancelled=(recs[0]["events"].get("parse") or {}).get("cancelled"),
                 return_median_ms=None if inconsistent else med(ret), return_max_ms=None if inconsistent else max(ret),
                 cleanup_max_ms=None if inconsistent else max(cleanup), runs_reached_budget=plain_reached,
                 alloc_parse_ms=alloc_ms, alloc_memory_status=status, post_budget_live=post,
                 cross_at_callback=(a["events"].get("parse") or {}).get("cross_at_callback"),
                 budget_reached=reached or plain_reached > 0, safety="PASS" if safety else "FAIL", coverage=coverage,
                 memory=point_status, pass_=safety and coverage in ("TRIGGERED", "NOT_REQUIRED"))
    p["pass"] = p.pop("pass_")
    return p


def cancel(r):
    points = [cancel_point(r, case, budget, roles) for case, budget, roles in CANCEL_POINTS]
    safety = [(c, b) for c, b, roles in CANCEL_POINTS if "SAFETY" in roles]
    actual = sorted((c, b) for c, b, roles in CANCEL_POINTS if "ACTUAL" in roles)
    registered = (safety == [(c, 200) for c in CANCEL_V3 + CANCEL_ACTUAL]
                  and actual == sorted((c, 100 if c in ACTUAL_AT_100 else 200) for c in CANCEL_ACTUAL))
    return result("CANCEL", registered and all(p["pass"] for p in points), points,
                  ["return and cleanup over 5 runs after 1 warmup; growth after the budget from the allocator build",
                   "each run judged by its own budget, time and crossing (Session 05-7-1 C1)",
                   f"P572-SEP: {len(safety)} SAFETY points at 200 ms; ACTUAL 5/5 cancellation for {len(actual)} "
                   f"families (L-FOREACH, L-ANON at 100 ms, chosen after S571 q1); point set as registered: {registered}"])


def overshoot(r):
    points, ok = [], True
    for case in CANCEL_SET + LARGE_SET:
        for budget in BUDGETS:
            rec = r.run("cand", "PARSE", case, budget, tag=f"b{budget}")
            if not completed(rec):
                points.append({"case": case, "budget": budget, "censored": True, "pass": False})
                ok = False
                break
            pe = rec["events"]["parse"]
            if not pe["cancelled"] and pe["parse_ms"] < budget:
                points.append({"case": case, "budget": budget, "natural_completion_ms": pe["parse_ms"],
                               "status": "NOT_EXERCISED (finished before the budget)"})
                break
            reps = [pe["parse_ms"] - budget]
            if pe["cancelled"] and 80 <= reps[0] <= 120 or pe["cancelled"] and reps[0] > 100:
                for i in range(3):
                    again = r.run("cand", "PARSE", case, budget, tag=f"b{budget}-again{i}")
                    reps.append(again["events"]["parse"]["parse_ms"] - budget if completed(again) else math.inf)
            late_uncancelled = not pe["cancelled"] and pe["parse_ms"] > budget + 100
            p = {"case": case, "budget": budget, "cancelled": pe["cancelled"], "overshoot_ms": reps,
                 "pass": not late_uncancelled and max(reps) <= 100}
            ok &= p["pass"]
            points.append(p)
    exercised = [p for p in points if "overshoot_ms" in p]
    return result("CANCEL-OVERSHOOT", ok, points,
                  [f"{len(exercised)} points on {len({p['case'] for p in exercised})} inputs reached their budget; "
                   f"{sum(1 for p in points if 'status' in p)} inputs finished before the smallest budget reached"])


def gaps_and_cleanup(r):
    gap_points, clean_points, gap_ok, clean_ok = [], [], True, True
    for case in CANCEL_SET + LARGE_SET + VALID_1MIB:
        vals, recs = timed(r, "cand", "PARSE", case, 3, lambda x: x)
        if vals is None:
            gap_points.append({"case": case, "censored": True, "pass": False})
            clean_points.append({"case": case, "censored": True, "pass": False})
            gap_ok = clean_ok = False
            continue
        g = max(v["events"]["parse"]["max_gap_incl_edges_ms"] for v in vals)
        c = max(v["events"]["cleanup"]["tree_delete_ms"] + v["events"]["cleanup"]["parser_delete_ms"] for v in vals)
        gap_points.append({"case": case, "max_gap_ms": g, "pass": g <= 100})
        clean_points.append({"case": case, "max_cleanup_ms": c, "pass": c <= 100})
        gap_ok &= g <= 100
        clean_ok &= c <= 100
    return [result("MAX-CALLBACK-GAP", gap_ok, gap_points, ["budget 0, callback installed; 1 warmup + 3, maximum"]),
            result("CLEANUP-ALL", clean_ok, clean_points, ["tree + parser delete; same runs"])]


def large_input(r):
    points, ok = [], True
    for case in LARGE_SET + VALID_1MIB:
        rec = r.run("cand", "PARSE", case, 0)
        a = r.run("cand-alloc", "PARSE", case, 0, tag="alloc")
        p = {"case": case, "completed": completed(rec), "peak_commit": rec["report"]["peak_commit_bytes"],
             "termination": rec["report"]["termination_reason"],
             "parse_ms": m_parse(rec) if completed(rec) else None,
             "allocator_peak_live": a["final"]["allocator_peak_live"] if completed(a) else None}
        exempt = case == "L-SEP-1MiB"
        p["pass"] = p["completed"] and p["peak_commit"] <= 256 * MIB and (exempt or p["parse_ms"] <= 10000)
        ok &= p["pass"]
        points.append(p)
    return result("LARGE-INPUT", ok, points, ["uninstrumented peak commit decides; L-SEP time-exempt as in v3"])


def query_malformed(r):
    points, ok = [], True
    for fam in QUERY_MALFORMED:
        t = {}
        exceeded = False
        for k in (2000, 20000):
            vals, recs = timed(r, "cand", "QUERY_ONLY", f"{fam}-k{k:05d}", 3, m_query)
            t[k] = med(vals) if vals else None
            exceeded |= any(completed(x) and x["events"]["query"]["exceeded"] for x in recs)
        if exceeded:
            p = {"family": fam, "median_ms": t, "status": "query match limit exceeded", "pass": False}
        elif None in t.values():
            p = {"family": fam, "censored": True, "pass": False}
        elif t[20000] < FLOOR_MS:
            p = {"family": fam, "median_ms": t, "exponent": None, "status": "below the 0.1 ms floor at k=20,000",
                 "pass": True}
        else:
            e = exponent(t[2000], t[20000], 2000, 20000)
            p = {"family": fam, "median_ms": t, "exponent": e, "pass": e <= 1.5}
        ok &= p["pass"]
        points.append(p)
    return result("QUERY-MALFORMED", ok, points, ["full highlights, every capture consumed, default match limit"])


def valid_parse(r, seed):
    rng = random.Random(seed)
    points, ok = [], True
    groups = {"A5-01": A5_01[:6], "A5-01-number": A5_01[6:]}
    groups.update({f"VALID-{f}": [f"VALID-{f}-{k:03d}k" for k in (4, 16, 64, 256)] for f in VALID_FAMILIES})
    groups["W03"] = ["W03-compact", "W03-program", "W03-program-crlf"]
    for fam, members in groups.items():
        meds = []
        for case in members:
            m, recs = paired(r, "cand", "h", "PARSE", case, 5, m_parse, rng)
            if m is None:
                points.append({"case": case, "censored": True, "pass": False})
                ok = False
                meds.append(None)
                continue
            ratio = m["cand"] / m["h"] if m["h"] >= FLOOR_MS else None
            p = {"case": case, "cand_median": m["cand"], "ref_median": m["h"], "ratio": ratio,
                 "pass": ratio is None or ratio <= 1.5}
            ok &= p["pass"]
            points.append(p)
            meds.append(m["cand"])
        if fam != "W03" and None not in meds:
            sizes = [int(c.rsplit("-k", 1)[1]) if "-k" in c else int(c.rsplit("-", 1)[1][:-1]) for c in members]
            es = [exponent(meds[i], meds[i + 1], sizes[i], sizes[i + 1]) for i in (len(meds) - 3, len(meds) - 2)]
            p = {"family": fam, "largest_pair_exponents": es, "pass": all(e is not None and e <= 1.2 for e in es)}
            ok &= p["pass"]
            points.append(p)
    return result("VALID-PARSE", ok, points, ["reference H (47d4047, parser 2711f7cc), paired randomized order"])


# ------------------------------------------------------------------ memory over registered points
def abs_memory(runs):
    registered = set(B5_01 + B5_02 + ["A5-01-k32000", "A5-01-number-k32000"] + CANCEL_SET)
    peak = {}
    for rec in runs:
        if rec["build"] == "cand" and rec["case"] in registered:
            peak[rec["case"]] = max(peak.get(rec["case"], 0), rec["report"]["peak_commit_bytes"])
    points = [{"case": c, "peak_commit": peak.get(c), "pass": peak.get(c) is not None and peak[c] <= 128 * MIB}
              for c in sorted(registered)]
    return result("ABS-MEMORY", all(p["pass"] for p in points), points,
                  ["maximum supervisor peak commit over every uninstrumented run of each registered point"])


# ------------------------------------------------------------------ SEM-PUBLIC (ADR-0007 projection)
def parse_dump(text):
    """DUMPLIST output -> {path: root}; node = [type, field, start, end, flags, children]."""
    files, stack, cur = {}, [], None
    for line in text.splitlines():
        parts = line.split("\t")
        if parts[0] == "F":
            cur = parts[1]
            files[cur] = {"root": None, "complete": False}
            stack = []
        elif parts[0] == "N":
            depth = int(parts[1])
            node = [parts[2], parts[3], int(parts[4]), int(parts[5]), int(parts[6]), []]
            del stack[depth:]
            if depth == 0:
                files[cur]["root"] = node
            else:
                stack[depth - 1][5].append(node)
            stack.append(node)
        elif parts[0] == "END":
            files[cur]["complete"] = True
    return files


def project(node):
    """The ADR-0007 rule: a call whose `function` is a member_expression becomes object . property arguments."""
    t, f, s, e, fl, kids = node
    kids = [project(k) for k in kids]
    if t == "call_expression":
        flat = []
        for k in kids:
            flat.extend(k[5] if k[1] == "function" and k[0] == "member_expression" else [k])
        kids = flat
    return [t, f, s, e, fl, kids]


def mutants(tree, rng):
    """Copies of a valid tree with one span, field, type, order or child changed (comparator self-test)."""
    import copy
    for kind in ("span", "field", "type", "order", "drop"):
        m = copy.deepcopy(tree)
        nodes = []

        def walk(n, parent):
            nodes.append((n, parent))
            for k in n[5]:
                walk(k, n)
        walk(m, None)
        named = [(n, p) for n, p in nodes if n[4] & 1 and p is not None]
        if not named:
            return
        n, p = named[rng.randrange(len(named))]
        if kind == "span":
            n[3] += 1
        elif kind == "field":
            n[1] = "left" if n[1] != "left" else "right"
        elif kind == "type":
            n[0] += "_x"
        elif kind == "order":
            if len(p[5]) < 2:
                continue
            p[5].reverse()
        else:
            p[5].remove(n)
        yield kind, m


def sem_public(r, seed):
    items = cases.tree_compare()
    rng = random.Random(seed)
    counts = {"valid_equal": 0, "valid_raw_equal": 0, "valid_different": 0, "error_presence_equal": 0,
              "error_presence_mismatch": 0, "incomplete": 0}
    different, mismatch, mutant_total, mutant_rejected = [], [], 0, 0
    for i in range(0, len(items), 150):
        chunk = items[i:i + 150]
        paths = [r.write_input(f"tree-compare/{i + j:05d}.brs", data) for j, (_, data, _) in enumerate(chunk)]
        listing = r.write_list(f"tree-compare/list-{i:05d}.txt", paths)
        old = parse_dump(r.probe("h", ["DUMPLIST", listing], f"sem-h-{i:05d}"))
        new = parse_dump(r.probe("cand", ["DUMPLIST", listing], f"sem-c-{i:05d}"))
        for (name, _, _), path in zip(chunk, paths):
            a, b = old.get(str(path)), new.get(str(path))
            if not a or not b or not a["complete"] or not b["complete"]:
                counts["incomplete"] += 1
                continue
            ea, eb = bool(a["root"][4] & 16), bool(b["root"][4] & 16)
            if ea or eb:
                counts["error_presence_equal" if ea == eb else "error_presence_mismatch"] += 1
                if ea != eb:
                    mismatch.append(name)
                continue
            pa = project(a["root"])
            if pa == b["root"]:
                counts["valid_equal"] += 1
                counts["valid_raw_equal"] += a["root"] == b["root"]
                if mutant_total < 400:
                    for _, m in mutants(b["root"], rng):
                        mutant_total += 1
                        mutant_rejected += pa != m
            else:
                counts["valid_different"] += 1
                different.append(name)
    ok = (counts["valid_different"] == 0 and counts["error_presence_mismatch"] == 0 and counts["incomplete"] == 0
          and mutant_total > 0 and mutant_rejected == mutant_total)
    return result("SEM-PUBLIC", ok, [{"counts": counts, "different": different[:50], "error_presence_mismatch": mismatch[:50],
                                      "mutants": {"total": mutant_total, "rejected": mutant_rejected}}],
                  ["corpus 228/228 and W03-W05, W07, W09 are checked by the repository scripts (tscli.py test and others)"])


# ------------------------------------------------------------------ incremental, resume, two parsers
def incremental_repair(r):
    points, ok = [], True
    for idx, (name, base, edits) in enumerate(cases.incremental()):
        b = r.write_input(f"incremental/{name}.brs", base)
        e = r.write_input(f"incremental/{name}.edits", edits)
        final = r.probe_final("cand", ["INCREMENTAL", b, e, "1", "0"], f"inc-{name}")
        p = {"case": name, "result": final}
        p["pass"] = bool(final) and final["incremental_equals_fresh"] is True and final["repair_equals_original"] is True
        ok &= p["pass"]
        points.append(p)
        if idx == 0:
            for selftest, key in ((1, "incremental_equals_fresh"), (2, "repair_equals_original")):
                st = r.probe_final("cand", ["INCREMENTAL", b, e, "1", str(selftest)], f"inc-selftest{selftest}")
                q = {"case": f"comparator self-test {selftest}", "detected": bool(st) and st[key] is False}
                q["pass"] = q["detected"]
                ok &= q["pass"]
                points.append(q)
    return result("INCREMENTAL-REPAIR", ok, points, ["28 scripts of resume-07; repair applies the inverse edits"])


# (input, other source for D3, chunk bytes, callback count that cancels): registered before the first run.
RESUME_PLAN = [
    ("VALID-calls-064k", "VALID-flat-assign-016k", 64, 20),
    ("A5-01-k08000", "VALID-flat-assign-016k", 64, 20),
    ("L-FOREACH-1MiB", "VALID-flat-assign-016k", 4096, 200),
    ("L-WHILE-1MiB", "VALID-flat-assign-016k", 4096, 200),
    ("Q-PAREN-k20000", "VALID-flat-assign-016k", 64, 5),
    ("V-PRINT-1MiB", "VALID-flat-assign-016k", 4096, 200),
]


def resume_and_two(r):
    points, ok = [], True
    for text, other, chunk, trigger in RESUME_PLAN:
        out = r.probe("cand", ["RESUME", r.input(text), r.input(other), str(chunk), str(trigger)], f"resume-{text}")
        events = [e for e in r.json_lines(out) if e.get("event") in ("fresh", "resume")]
        fresh = next((e for e in events if e["event"] == "fresh"), None)
        resumed = [e for e in events if e["event"] == "resume"]
        p = {"input": text, "chunk": chunk, "trigger": trigger,
             "chunked_equals_whole": bool(fresh) and fresh["chunked_equals_whole"], "cases": resumed,
             "cancel_observed": sum(1 for c in resumed if c["cancel_observed"])}
        triggered = [c for c in resumed if c["cancel_observed"]]
        if len(resumed) == 3 and not triggered:
            # The parse ended before the trigger: no resume or reset happened, so this input is no evidence.
            p["status"] = "NOT_TRIGGERED"
            p["pass"] = None
            ok &= p["chunked_equals_whole"]
            points.append(p)
            continue
        else:
            p["pass"] = (p["chunked_equals_whole"] and len(resumed) == 3 and len(triggered) == 3
                         and all(c["equals_fresh"] for c in triggered))
        ok &= p["pass"]
        points.append(p)
    exercised = [p for p in points if p.get("status") != "NOT_TRIGGERED"]
    if not exercised:
        ok = False
    two = r.probe_final("cand", ["TWO", r.input("VALID-flat-assign-004k"), r.input("A5-01-k01000")], "two")
    points.append({"check": "two parsers", "result": two, "pass": bool(two) and two["two_parser_independent"]})
    ok &= points[-1]["pass"]
    return result("RESUME-RESET", ok, points, ["E4.4: D1 resume same source, D2 reset same source, D3 reset new source; "
                                               "a case whose parse ends before the trigger is NOT_TRIGGERED, not a pass"])


# ------------------------------------------------------------------ RECOVERY-LOCALITY
def recovery_locality(r):
    """Lines after an error (ADR-0008; Session 05-7 review A-01). For every single-line mutant of the sample files
    (cases.locality_mutants), the rows covered by ERROR or MISSING nodes apart from the mutated row are compared
    between the candidate and H. Registered before the gate first ran: the candidate may hide rows that H keeps by
    five rows or more, and by twenty rows or more, in no more mutants than H hides rows that the candidate keeps."""
    counts = {"cand_hides_more": {1: 0, 5: 0, 20: 0}, "h_hides_more": {1: 0, 5: 0, 20: 0}}
    examples = []
    mutants = cases.locality_mutants()
    for name, data, row in mutants:
        path = r.write_input(f"locality/{name}.brs", data)
        cand, ref = r.error_rows("cand", path) - {row}, r.error_rows("h", path) - {row}
        for key, extra in (("cand_hides_more", cand - ref), ("h_hides_more", ref - cand)):
            for n in (1, 5, 20):
                counts[key][n] += len(extra) >= n
        if len(cand - ref) >= 5 and len(examples) < 30:
            examples.append({"mutant": name, "rows": len(cand - ref)})
    c, h = counts["cand_hides_more"], counts["h_hides_more"]
    ok = c[5] <= h[5] and c[20] <= h[20]
    return result("RECOVERY-LOCALITY", ok, [{"mutants": len(mutants), "counts": counts, "examples": examples}],
                  ["rows under ERROR or MISSING through the pinned CLI, candidate against H (47d4047)"])


# ------------------------------------------------------------------ SUPPORT, sweep
def support(r, versions):
    points, ok = [], True
    if not versions:
        return result("SUPPORT", False, [], ["no --support runtime given"], status="NOT_RUN")
    for ver in versions:
        for case in B5_01 + B5_02 + ["A5-01-k32000", "A5-01-number-k32000"]:
            rec = r.run(f"cand-rt{ver}", "LIFECYCLE", case, 0)
            p = {"runtime": ver, "case": case, "completed": completed(rec), "termination": rec["report"]["termination_reason"],
                 "exit_code": rec["report"]["exit_code_raw"], "peak_commit": rec["report"]["peak_commit_bytes"]}
            p["pass"] = p["completed"]
            ok &= p["pass"]
            points.append(p)
    return result("SUPPORT", ok, points, ["stock 0.27.0 is the product runtime; these runs check crash and cap only"])


def sweep(r):
    points, ok = [], True
    for fam, ctx, unit, end in cases.sweep_families():
        # 1 warmup + 5 runs per point, median (gate contract `sampling`, short points).
        series = {k: timed(r, "cand", "PARSE", f"{fam}-k{k:05d}", 5, m_parse) for k in (100, 400, 4000, 20000)}
        recs = {k: rs[-1] for k, (_, rs) in series.items()}
        p = {"family": fam, "completed": all(v is not None for v, _ in series.values())}
        if p["completed"]:
            t = {k: med(v) for k, (v, _) in series.items()}
            peak = {k: max(x["report"]["peak_commit_bytes"] for x in rs) for k, (_, rs) in series.items()}
            growth = peak[20000] - peak[100]
            # The smaller time of each pair is clamped to the 0.1 ms floor, so a startup-dominated or sub-floor point
            # bounds the exponent from above instead of hiding it (Session 05-7 review B-01, B-06).
            es = {f"{a}-{b}": exponent(max(t[a], FLOOR_MS), t[b], a, b) for a, b in ((400, 20000), (4000, 20000))}
            e = max(es.values())
            kl002 = unit in KL002_UNITS
            p.update(parse_ms=t, memory_growth=growth, exponents=es, exponent=e, kl002=kl002)
            p["pass"] = growth < 64 * MIB and e <= 1.5
        else:
            p["termination"] = {k: x["report"]["termination_reason"] for k, x in recs.items()}
            p["pass"] = False
        ok &= p["pass"]
        points.append(p)
    return result("REGRESSION-SWEEP", ok, points, [f"{len(points)} families x k 100, 400, 4000, 20000, 1 warmup + 5 runs each, "
                                                   "median; crash 0, memory growth "
                                                   "< 64 MiB; time exponents 400 -> 20000 and 4000 -> 20000, the "
                                                   "smaller time clamped to the 0.1 ms floor, <= 1.5; the retired "
                                                   "KL-002 units included"])
