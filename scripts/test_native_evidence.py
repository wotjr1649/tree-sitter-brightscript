"""Small positive and planted-difference controls for cross-OS evidence comparison."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from build_native_evidence import signatures
from check_oracle_pair import compare as compare_oracles
from compare_native_evidence import compare as compare_hosts


def sha(data):
    return hashlib.sha256(data).hexdigest()


class NativeEvidence(unittest.TestCase):
    def test_oracle_repeat_detects_changed_tree(self):
        with tempfile.TemporaryDirectory() as tmp:
            roots = [Path(tmp) / name for name in ("a", "b")]
            blobs = {"inputs/000.brs": b"x = 1\n", "trees/000.txt": b"(source_file)\n",
                     "cst/000.txt": b"0:0 - 1:0 source_file\n"}
            record = {"n": 0, "input_sha256": sha(blobs["inputs/000.brs"]),
                      "tree_sha256": sha(blobs["trees/000.txt"]), "cst_sha256": sha(blobs["cst/000.txt"])}
            content = sha((record["input_sha256"] + record["tree_sha256"] + record["cst_sha256"]).encode())
            blobs["manifest.json"] = json.dumps({"identity": {"content_sha256": content},
                                                 "results": [record]}).encode()
            for root in roots:
                for name, data in blobs.items():
                    path = root / name
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(data)
            self.assertEqual(compare_oracles(*roots), (1, content))
            (roots[1] / "trees/000.txt").write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                compare_oracles(*roots)

    def test_host_comparison_detects_planted_difference(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = [Path(tmp) / f"{name}.json" for name in ("windows", "ubuntu", "macos")]
            common = {"gate_statuses": [f"gate-{i}" for i in range(17)], "native_trees": ["same"],
                      "oracle_cases": 1}
            for path, platform in zip(paths, ("win32", "linux", "darwin")):
                path.write_text(json.dumps({"common": common, "host": {"platform": platform}}), encoding="utf-8")
            self.assertEqual(compare_hosts(*paths), common)
            bad = dict(common, native_trees=["different"])
            paths[2].write_text(json.dumps({"common": bad, "host": {"platform": "darwin"}}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "native_trees"):
                compare_hosts(*paths)

    def test_timing_is_excluded_but_query_digest_is_not(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "runs.jsonl"
            final = {"final": True, "bytes": 1, "cancelled": False, "has_error": 0, "nodes": 1,
                     "errors": 0, "missing": 0, "max_depth": 0, "captures": 1, "match_limit_exceeded": False}
            record = {"budget": 0, "completed": True, "build": "cand", "op": "QUERY_ONLY", "case": "one",
                      "final": final, "events": {"query": {"captures": 1, "zero_width_captures": 0,
                                                            "exceeded": False, "digest": "a"}}}
            path.write_text(json.dumps(record) + "\n" + json.dumps(record) + "\n", encoding="utf-8")
            self.assertEqual(len(signatures(path)), 1)
            changed = json.loads(json.dumps(record))
            changed["events"]["query"]["digest"] = "b"
            path.write_text(json.dumps(record) + "\n" + json.dumps(changed) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "non-deterministic"):
                signatures(path)


if __name__ == "__main__":
    unittest.main()
