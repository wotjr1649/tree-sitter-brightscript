"""Offline comparison of frozen qualification results (S07-PATCH012 E1).

Only the enumerated log-derived fields admit <= 2 ULP. Raw measurements,
thresholds, identities, types, ordering and verdicts remain exact. This module
does not run a parser, change a recorded result, or decide a release gate.
"""
import json
import math
import struct
import sys

POLICY = "S07-REPLAY-2ULP-r1"
MAX_ULPS = 2
GATES = ("B5-01-MEMORY", "B5-02-LIFECYCLE", "A5-01-COST", "CANCEL", "CANCEL-OVERSHOOT",
         "MAX-CALLBACK-GAP", "CLEANUP-ALL", "LARGE-INPUT", "QUERY-MALFORMED", "VALID-PARSE",
         "SEM-PUBLIC", "INCREMENTAL-REPAIR", "RESUME-RESET", "SUPPORT", "REGRESSION-SWEEP",
         "ABS-MEMORY", "RECOVERY-LOCALITY")


class ReplayMismatch(ValueError):
    pass


def strict_json(data):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ReplayMismatch("DUPLICATE_JSON_KEY: " + key)
            result[key] = value
        return result

    def constant(value):
        raise ReplayMismatch("NONFINITE_JSON: " + value)

    def floating(value):
        number = float(value)
        if not math.isfinite(number):
            raise ReplayMismatch("NONFINITE_JSON")
        return number

    return json.loads(data, object_pairs_hook=pairs, parse_constant=constant, parse_float=floating)


def bits(value):
    return struct.unpack(">Q", struct.pack(">d", value))[0]


def point_id(point):
    """An explanatory semantic ID, never a list offset used as authorization."""
    return {k: point[k] for k in ("case", "family", "op", "sizes", "check", "budget") if k in point}


def derived_fields(gate, point):
    """Allowlist from pinned gates.py exponent() callers; thresholds are unchanged.

    The original formulas use log(t2/t1)/log(n2/n1). REGRESSION-SWEEP
    additionally clamps the smaller time to 0.1 ms and takes the maximum.
    None means the original formula was inapplicable and is compared exactly.
    """
    if gate == "B5-01-MEMORY" and set(point) == {"family", "sizes", "exponent", "pass"}:
        return {("exponent",): 1.5}
    if gate == "B5-02-LIFECYCLE" and point.get("check") == "call exponent 1,000 -> 4,000":
        if set(point) == {"check", "exponent", "pass"}:
            return {("exponent",): 1.5}
    if gate == "A5-01-COST" and set(point) == {"family", "op", "sizes", "exponents", "pass"}:
        return {("exponents", i): 1.5 for i in range(2)}
    if gate == "QUERY-MALFORMED" and "family" in point and "exponent" in point:
        return {("exponent",): 1.5}
    if gate == "VALID-PARSE" and set(point) == {"family", "largest_pair_exponents", "pass"}:
        return {("largest_pair_exponents", i): 1.2 for i in range(2)}
    if gate == "REGRESSION-SWEEP" and point.get("completed") is True:
        if set(point.get("exponents", {})) != {"400-20000", "4000-20000"}:
            raise ReplayMismatch("UNKNOWN_DERIVED_SCHEMA")
        return {("exponents", "400-20000"): 1.5, ("exponents", "4000-20000"): 1.5,
                ("exponent",): 1.5}
    return {}


def compare_value(recorded, recomputed, path=(), allowed=None, changes=None):
    allowed = {} if allowed is None else allowed
    changes = [] if changes is None else changes
    if type(recorded) is not type(recomputed):
        raise ReplayMismatch(f"TYPE_DIFFERENCE: {path}")
    if isinstance(recorded, dict):
        if recorded.keys() != recomputed.keys():
            raise ReplayMismatch(f"KEY_DIFFERENCE: {path}")
        for key in recorded:
            compare_value(recorded[key], recomputed[key], (*path, key), allowed, changes)
    elif isinstance(recorded, list):
        if len(recorded) != len(recomputed):
            raise ReplayMismatch(f"CARDINALITY_DIFFERENCE: {path}")
        for i, (a, b) in enumerate(zip(recorded, recomputed)):
            compare_value(a, b, (*path, i), allowed, changes)
    elif type(recorded) is float:
        if not math.isfinite(recorded) or not math.isfinite(recomputed):
            raise ReplayMismatch(f"NONFINITE: {path}")
        a, b = bits(recorded), bits(recomputed)
        limit = allowed.get(path)
        normal = (abs(recorded) >= sys.float_info.min and abs(recomputed) >= sys.float_info.min
                  and (a >> 63) == (b >> 63))
        if limit is not None and normal:
            # A tolerance corridor may not straddle any original threshold,
            # even when the central values happen to agree on this host.
            for v in (recorded, recomputed):
                lo, hi = v, v
                for _ in range(MAX_ULPS):
                    lo, hi = math.nextafter(lo, -math.inf), math.nextafter(hi, math.inf)
                if not math.isfinite(lo) or not math.isfinite(hi) or lo <= limit < hi:
                    raise ReplayMismatch(f"NUMERIC_BOUNDARY_INDETERMINATE: {path}")
            if (recorded <= limit) != (recomputed <= limit):
                raise ReplayMismatch(f"THRESHOLD_DECISION_DIFFERENCE: {path}")
            if abs(a - b) > MAX_ULPS:
                raise ReplayMismatch(f"ULP_LIMIT_EXCEEDED: {path}")
            if a != b:
                changes.append({"path": list(path), "recorded": recorded, "recomputed": recomputed,
                                "ulp_distance": abs(a - b), "allowed_ulps": MAX_ULPS,
                                "threshold": limit, "threshold_decisions_equal": True})
        elif a != b:
            raise ReplayMismatch(f"EXACT_FLOAT_DIFFERENCE: {path}")
    elif type(recorded) not in (str, int, bool, type(None)) or recorded != recomputed:
        raise ReplayMismatch(f"VALUE_DIFFERENCE: {path}")
    return changes


def compare_gate(recorded, recomputed):
    if set(recorded) != {"gate", "status", "points", "notes"} or set(recomputed) != set(recorded):
        raise ReplayMismatch("UNKNOWN_GATE_SCHEMA")
    name = recorded["gate"]
    if name not in GATES or name != recomputed["gate"]:
        raise ReplayMismatch("UNKNOWN_GATE_ID")
    compare_value(recorded["status"], recomputed["status"])
    compare_value(recorded["notes"], recomputed["notes"])
    if type(recorded["points"]) is not list or type(recomputed["points"]) is not list:
        raise ReplayMismatch("POINT_LIST_REQUIRED")
    if len(recorded["points"]) != len(recomputed["points"]):
        raise ReplayMismatch("POINT_CARDINALITY_DIFFERENCE")
    changes = []
    for old, new in zip(recorded["points"], recomputed["points"]):
        compare_value(point_id(old), point_id(new))
        allow = derived_fields(name, old)
        if name == "REGRESSION-SWEEP" and old.get("completed") is True:
            for p in (old, new):
                if p["exponent"] != max(p["exponents"].values()):
                    raise ReplayMismatch("AGGREGATE_VALUE_DIFFERENCE")
            winners = lambda p: {k for k, v in p["exponents"].items() if v == p["exponent"]}
            if winners(old) != winners(new):
                raise ReplayMismatch("AGGREGATE_SOURCE_CHANGED")
        for row in compare_value(old, new, allowed=allow):
            changes.append({"gate_id": name, "point_id": point_id(old), **row})
    return {"status": "REPLAY_EQUIVALENT_WITH_DECLARED_ROUNDING" if changes else "BITWISE_EQUAL",
            "policy": POLICY, "gate_id": name, "verdict": recorded["status"], "differences": changes}
