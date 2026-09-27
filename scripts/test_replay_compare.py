"""Known-bad and boundary controls for the offline replay comparison; no native run."""
import copy
import math
import struct
import unittest

import replay_compare as rc


def archived():
    # Archived public q3, resolved by family ID, not its historical list index.
    return {"gate": "REGRESSION-SWEEP", "status": "PASS", "notes": [], "points": [{
        "family": "SW-y203d205b-2920else20-nl", "completed": True,
        "parse_ms": {"100": 0.2332, "400": 0.6648, "4000": 5.5785, "20000": 28.3676},
        "memory_growth": 11468800, "exponents": {"400-20000": 0.9594822625200103,
        "4000-20000": 1.0104942310740572}, "exponent": 1.0104942310740572,
        "kl002": False, "pass": True}]}


class ReplayComparison(unittest.TestCase):
    def test_archived_failure_and_original_formula(self):
        old = archived()
        new = copy.deepcopy(old)
        new["points"][0]["exponents"]["400-20000"] = 0.9594822625200102
        self.assertNotEqual(old, new)  # Old public comparator rejects these saved values.
        result = rc.compare_gate(old, new)
        self.assertEqual(result["status"], "REPLAY_EQUIVALENT_WITH_DECLARED_ROUNDING")
        self.assertEqual(result["differences"][0]["ulp_distance"], 1)
        self.assertEqual(result["differences"][0]["point_id"]["family"], old["points"][0]["family"])
        derived = math.log(28.3676 / 0.6648) / math.log(20000 / 400)
        self.assertLessEqual(abs(rc.bits(derived) - rc.bits(0.9594822625200103)), 2)

    def test_zero_through_three_ulp_symmetric(self):
        old = archived()
        for steps in range(4):
            for direction in (-math.inf, math.inf):
                new = copy.deepcopy(old)
                new["points"][0]["exponents"]["400-20000"] = math.nextafter(
                    old["points"][0]["exponents"]["400-20000"], direction, steps=steps)
                for a, b in ((old, new), (new, old)):
                    if steps <= 2:
                        self.assertEqual(len(rc.compare_gate(a, b)["differences"]), int(steps > 0))
                    else:
                        with self.assertRaisesRegex(rc.ReplayMismatch, "ULP_LIMIT"):
                            rc.compare_gate(a, b)

    def test_raw_and_unregistered_fields_are_exact(self):
        old = archived()
        for field in ("100", "400", "4000", "20000"):
            new = copy.deepcopy(old)
            new["points"][0]["parse_ms"][field] = math.nextafter(new["points"][0]["parse_ms"][field], math.inf)
            with self.assertRaises(rc.ReplayMismatch):
                rc.compare_gate(old, new)
        for path in ("timing", "threshold", "arbitrary", "budget"):
            with self.assertRaises(rc.ReplayMismatch):
                rc.compare_value({path: 1.0}, {path: math.nextafter(1.0, math.inf)})

    def test_special_floats(self):
        for value in (math.nan, math.inf, -math.inf):
            with self.assertRaises(rc.ReplayMismatch):
                rc.compare_value(value, value, allowed={(): 1.5})
        for a, b in ((0.0, -0.0), (0.0, math.ulp(0.0)), (math.ulp(0.0), 2 * math.ulp(0.0)),
                     (1.0, -1.0), (-1.0, 1.0)):
            with self.assertRaises(rc.ReplayMismatch):
                rc.compare_value(a, b, allowed={(): 1.5})
        for value in (0.0, -0.0, math.ulp(0.0), -math.ulp(0.0)):
            self.assertEqual(rc.compare_value(value, value, allowed={(): 1.5}), [])
        self.assertEqual(len(rc.compare_value(-1.0, math.nextafter(-1.0, -math.inf), allowed={(): 1.5})), 1)
        biggest = struct.unpack(">d", bytes.fromhex("7fefffffffffffff"))[0]
        with self.assertRaisesRegex(rc.ReplayMismatch, "BOUNDARY"):
            rc.compare_value(biggest, biggest, allowed={(): 1.5})

    def test_json_and_type_controls(self):
        for text in ('{"x":1,"x":1}', '{"x":NaN}', '{"x":Infinity}', '{"x":-Infinity}', '{"x":1e999}'):
            with self.assertRaises(rc.ReplayMismatch):
                rc.strict_json(text)
        for a, b in ((True, 1), (1, 1.0), (1.0, "1.0"), (None, 0), (False, None)):
            with self.assertRaises(rc.ReplayMismatch):
                rc.compare_value(a, b)
        for a, b in (({"a": 1}, {}), ({}, {"a": 1}), ([1, 2], [2, 1]), ([1, 2], [1]), ([1, 2], [1, 1])):
            with self.assertRaises(rc.ReplayMismatch):
                rc.compare_value(a, b)

    def test_threshold_and_verdict_controls(self):
        for threshold in (1.2, 1.5):
            for v in (math.nextafter(threshold, -math.inf), threshold, math.nextafter(threshold, math.inf)):
                with self.assertRaisesRegex(rc.ReplayMismatch, "BOUNDARY"):
                    rc.compare_value(v, v, allowed={(): threshold})
        old = archived()
        for scope in ("gate", "point"):
            new = copy.deepcopy(old)
            if scope == "gate":
                new["status"] = "FAIL"
            else:
                new["points"][0]["pass"] = False
            with self.assertRaises(rc.ReplayMismatch):
                rc.compare_gate(old, new)
        fail = copy.deepcopy(old)
        fail["status"], fail["points"][0]["pass"] = "FAIL", False
        self.assertEqual(rc.compare_gate(fail, fail)["verdict"], "FAIL")

    def test_max_source_change(self):
        old = archived()
        old["points"][0]["exponents"] = {"400-20000": 1.0, "4000-20000": math.nextafter(1.0, math.inf)}
        old["points"][0]["exponent"] = math.nextafter(1.0, math.inf)
        new = copy.deepcopy(old)
        new["points"][0]["exponents"] = dict(zip(old["points"][0]["exponents"], reversed(list(old["points"][0]["exponents"].values()))))
        with self.assertRaisesRegex(rc.ReplayMismatch, "AGGREGATE_SOURCE"):
            rc.compare_gate(old, new)

    def test_unknown_schema_id_and_identity(self):
        old = archived()
        for field, value in (("gate", "UNKNOWN"), ("unexpected_schema", 2)):
            new = copy.deepcopy(old)
            new[field] = value
            with self.assertRaises(rc.ReplayMismatch):
                rc.compare_gate(old, new)
        new = copy.deepcopy(old)
        new["points"][0]["family"] += "-other"
        with self.assertRaises(rc.ReplayMismatch):
            rc.compare_gate(old, new)


if __name__ == "__main__":
    unittest.main(verbosity=2)
