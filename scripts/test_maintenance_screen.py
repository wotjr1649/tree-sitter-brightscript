"""Discriminating controls for the finite screen manifest, edits and raw reader."""
import copy
import unittest

import maintenance_screen as screen


class ScreenControls(unittest.TestCase):
    def test_manifest_and_operation_accounting(self):
        sources, edits = screen.sources(), screen.edits()
        self.assertLessEqual(len(sources), 200)
        self.assertLessEqual(len(edits), 24)
        self.assertEqual(len({r["case_id"] for r in sources}), len(sources))
        self.assertTrue(all(r["expected_named"] for r in sources if r["expected_class"] == "VALID"))
        plan = screen.public_manifest()
        self.assertEqual(plan["expected_probe_children"], len(sources) * 3 + len(edits) + 2)
        self.assertEqual(plan["expected_parser_calls"], len(sources) * 4 + sum(2 + 2 * len(r["edits"]) for r in edits) + 12)
        for row in edits:
            self.assertEqual(screen.apply_edits(row["data"], row["edits"]), row["final_data"])
        bad = copy.deepcopy(plan)
        bad["expected_parser_calls"] -= 1
        self.assertNotEqual(bad, screen.public_manifest())

    def test_edit_offsets_rejected_before_native(self):
        for script in ([(2, 1, b"x")], [(-1, 0, b"")], [(0, -1, b"")], [(True, 0, b"")], [(0, 0, "x")]):
            with self.assertRaises(ValueError):
                screen.apply_edits(b"ab", script)
        self.assertEqual(screen.apply_edits(b"abc", [(1, 1, b"d")]), b"adc")

    def test_dump_fidelity_completion_span_and_missing(self):
        # Independent minimal artificial tree exercises the reader, not a parser oracle.
        data = b"a"
        h = ((14695981039346656037 ^ ord("a")) * 1099511628211) & ((1 << 64) - 1)
        raw = f"F\tinput\t1\t{h:016x}\nN\t0\tsource_file\t-\t0\t1\t1\nN\t1\tidentifier\t-\t0\t1\t1\nEND\t2\t1\nDUMP_DONE\t0\n"
        self.assertFalse(screen.check_dump(raw, data, "VALID")["has_error"])
        mutants = [raw.replace("DUMP_DONE\t0", "DUMP_DONE\t1"), raw.replace("END\t2", "END\t1"),
                   raw.replace("identifier\t-\t0\t1", "identifier\t-\t1\t2"),
                   raw.replace("identifier\t-\t0\t1\t1", "identifier\t-\t0\t1\t3"),
                   raw.replace("source_file\t-\t0\t1", "source_file\t-\t0\t0")]
        for mutant in mutants:
            with self.assertRaises(ValueError):
                screen.check_dump(mutant, data, "VALID")
        with self.assertRaises(ValueError):
            screen.check_dump(raw, b"b", "VALID")
        with self.assertRaises(ValueError):
            screen.check_dump(raw, b"", "VALID")
        for bad in (None, "x" * (screen.OUTPUT_BYTES + 1), "\n" * (screen.MAX_NODES + 4),
                    raw.replace("N\t1\tidentifier", "N\t-1\tidentifier"),
                    raw.replace("identifier\t-\t0\t1\t1", "identifier\t-\t0\t1\t33")):
            with self.assertRaises(ValueError):
                screen.check_dump(bad, data, "VALID")
        bad_operator = raw.replace("identifier\t-\t0\t1\t1", "+\toperator\t0\t1\t0")
        with self.assertRaisesRegex(ValueError, "operator"):
            screen.check_dump(bad_operator, data, "VALID")

    def test_partial_and_cancelled_query(self):
        final = {"final": True, "op": "QUERY_ONLY", "bytes": 1, "cancelled": False,
                 "has_error": 0, "match_limit_exceeded": False, "captures": 1}
        screen.check_query(final, b"a")
        for key, value in (("final", False), ("cancelled", True), ("bytes", 0),
                           ("has_error", False), ("match_limit_exceeded", True), ("captures", None)):
            with self.assertRaises(ValueError):
                screen.check_query({**final, key: value}, b"a")


if __name__ == "__main__":
    unittest.main(verbosity=2)
