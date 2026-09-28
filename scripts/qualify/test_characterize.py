"""Negative controls for the A/A judgement; no parser execution is represented by these records."""
import tempfile
import unittest
from pathlib import Path

import characterize


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
