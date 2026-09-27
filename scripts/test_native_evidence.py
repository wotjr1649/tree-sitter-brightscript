"""Small positive and planted-difference controls for cross-OS evidence comparison."""
import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from build_native_evidence import REQUIRED_GATES, build, signatures
from check_oracle_pair import compare as compare_oracles
from compare_native_evidence import compare as compare_hosts
from package_native_evidence import package


def sha(data):
    return hashlib.sha256(data).hexdigest()


class NativeEvidence(unittest.TestCase):
    @staticmethod
    def common():
        zero = "0" * 64
        return {"commit": "a" * 40, "candidate": {"src/parser.c": zero, "grammar.js": zero},
                "lane_sources": {"run.py": zero},
                "runtime": "0.27.0", "support": ["0.25.1", "0.26.13"], "seed": 5707,
                "gate_statuses": list(REQUIRED_GATES), "oracle_cases": 231,
                "oracle_workload": {"cases": 231, "sha256": zero}, "oracle_content_sha256": zero,
                "native_trees": [{"name": f"case-{i}", "input_sha256": zero, "tree_sha256": zero}
                                 for i in range(2811)],
                "native_runs": {f"cand|PARSE|case-{i}": {"bytes": 1} for i in range(1533)},
                "incremental": [{"case": f"edit-{i}", "pass": True, "result": {"same": True}}
                                for i in range(28)] + [
                                    {"case": f"comparator self-test {i}", "pass": True, "detected": True}
                                    for i in (1, 2)]}

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
            common = self.common()
            for path, platform, arch in zip(paths, ("win32", "linux", "darwin"),
                                            ("amd64", "x86_64", "arm64")):
                path.write_text(json.dumps({"common": common, "host": {"platform": platform,
                                                                          "architecture": arch,
                                                                          "runner_image": {"os": platform,
                                                                                           "version": "test",
                                                                                           "runner_arch": "ARM64" if platform == "darwin" else "X64"}}}), encoding="utf-8")
            self.assertEqual(compare_hosts(*paths), common)
            bad = dict(common, native_trees=[dict(common["native_trees"][0], tree_sha256="f" * 64),
                                             *common["native_trees"][1:]])
            paths[2].write_text(json.dumps({"common": bad, "host": {"platform": "darwin",
                                                                   "architecture": "arm64",
                                                                   "runner_image": {"os": "macos15", "version": "test",
                                                                                    "runner_arch": "ARM64"}}}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "native_trees"):
                compare_hosts(*paths)
            paths[2].write_text(json.dumps({"common": {"gate_statuses": list(REQUIRED_GATES),
                                                     "native_trees": [], "oracle_cases": 0},
                                           "host": {"platform": "darwin", "architecture": "arm64"}}),
                                encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "incomplete"):
                compare_hosts(*paths)

    def test_build_preserves_incremental_comparator_controls(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            q = root / "qualification"
            q.mkdir()
            common = self.common()
            identity = {"git_clean": True, "git_head": common["commit"], "candidate": common["candidate"],
                        "lane_sources": common["lane_sources"], "runtime": common["runtime"],
                        "support": common["support"], "seed": common["seed"], "cc_sha256": "0" * 64,
                        "runner_image": {"os": "win25", "version": "test", "runner_arch": "X64"},
                        "supervisor_kind": "windows_job", "probes": {"cand": "0" * 64}}
            (q / "identity.json").write_text(json.dumps(identity), encoding="utf-8")
            gates = [{"gate": name, "status": "PASS", "points": []} for name in REQUIRED_GATES]
            gates[REQUIRED_GATES.index("SEM-PUBLIC")]["points"] = [{"native_tree_digests": common["native_trees"]}]
            gates[REQUIRED_GATES.index("INCREMENTAL-REPAIR")]["points"] = common["incremental"]
            (q / "gates.json").write_text(json.dumps({"identity": identity, "results": gates}), encoding="utf-8")
            final = {"final": True, "bytes": 1, "cancelled": False, "has_error": 0, "nodes": 1,
                     "errors": 0, "missing": 0, "max_depth": 0, "captures": 0,
                     "match_limit_exceeded": False}
            run = {"budget": 0, "completed": True, "build": "cand", "op": "PARSE", "case": "one",
                   "final": final, "events": {}, "report": {"memory_metric": "windows_private_commit"}}
            (q / "runs.jsonl").write_text(json.dumps(run) + "\n", encoding="utf-8")
            blobs = (("inputs", "brs", b"x"), ("trees", "txt", b"t"), ("cst", "txt", b"c"))
            records = [{"n": i, **{f"{folder[:-1] if folder != 'cst' else 'cst'}_sha256": sha(data)
                                    for folder, _, data in blobs}} for i in range(231)]
            # The input field is singular; tree is singular, and CST keeps its acronym.
            content = sha("".join(r["input_sha256"] + r["tree_sha256"] + r["cst_sha256"]
                                  for r in records).encode())
            manifest = {"identity": {"grammar_commit": common["commit"], "generated_files": common["candidate"],
                                     "platform": "win32", "cli_binary_sha256": "0" * 64,
                                     "workload": {"cases": 231, "sha256": "0" * 64},
                                     "content_sha256": content}, "results": records}
            for name in ("oracle-a", "oracle-b"):
                oracle = root / name
                for folder, suffix, data in blobs:
                    target = oracle / folder
                    target.mkdir(parents=True)
                    for i in range(231):
                        (target / f"{i:03d}.{suffix}").write_bytes(data)
                (oracle / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            result = build(q, root / "oracle-a", root / "oracle-b")
            self.assertEqual(len(result["common"]["incremental"]), 30)
            self.assertEqual([p["case"] for p in result["common"]["incremental"] if "detected" in p],
                             ["comparator self-test 1", "comparator self-test 2"])

    def test_evidence_zip_checks_raw_records_and_is_reproducible(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            common = self.common()
            final = {"final": True, "bytes": 1, "cancelled": False, "has_error": 0, "nodes": 1,
                     "errors": 0, "missing": 0, "max_depth": 0, "captures": 0,
                     "match_limit_exceeded": False}
            runs = "".join(json.dumps({"budget": 0, "completed": True, "build": "cand", "op": "PARSE",
                                      "case": f"case-{i}", "final": final, "events": {}}) + "\n"
                           for i in range(1533))
            with (root / "runs.jsonl").open("w", encoding="utf-8") as output:
                output.write(runs)
            common["native_runs"] = signatures(root / "runs.jsonl")
            roots = []
            for name, platform, arch, runner_arch in (("windows", "win32", "amd64", "X64"),
                                                      ("ubuntu", "linux", "x86_64", "X64"),
                                                      ("macos", "darwin", "arm64", "ARM64")):
                host_root = root / name
                roots.append(host_root)
                (host_root / "native-full").mkdir(parents=True)
                for oracle_name in ("oracle-a", "oracle-b"):
                    (host_root / oracle_name).mkdir()
                (host_root / "native-full/runs.jsonl").write_text(runs, encoding="utf-8")
                runner_image = {"os": platform, "version": "test", "runner_arch": runner_arch}
                identity = {"git_clean": True, "git_head": common["commit"], "candidate": common["candidate"],
                            "runner_image": runner_image}
                gates = [{"gate": gate, "status": "PASS", "points": []} for gate in REQUIRED_GATES]
                gates[REQUIRED_GATES.index("SEM-PUBLIC")]["points"] = [
                    {"native_tree_digests": common["native_trees"]}]
                gates[REQUIRED_GATES.index("INCREMENTAL-REPAIR")]["points"] = common["incremental"]
                (host_root / "native-full/identity.json").write_text(json.dumps(identity), encoding="utf-8")
                (host_root / "native-full/gates.json").write_text(json.dumps(
                    {"identity": identity, "results": gates}), encoding="utf-8")
                oracle = {"identity": {"grammar_commit": common["commit"], "platform": platform,
                                       "generated_files": {"src/parser.c": common["candidate"]["src/parser.c"]},
                                       "cli_binary_sha256": "0" * 64,
                                       "workload": common["oracle_workload"],
                                       "content_sha256": common["oracle_content_sha256"]}}
                for oracle_name in ("oracle-a", "oracle-b"):
                    (host_root / oracle_name / "manifest.json").write_text(json.dumps(oracle), encoding="utf-8")
                evidence = {"common": common, "host": {"platform": platform, "architecture": arch,
                            "runner_image": runner_image, "identity_sha256": sha((host_root / "native-full/identity.json").read_bytes()),
                            "gates_sha256": sha((host_root / "native-full/gates.json").read_bytes()),
                            "cli_binary_sha256": "0" * 64}}
                (host_root / "native-evidence.json").write_text(json.dumps(evidence), encoding="utf-8")
            first, second = root / "first.zip", root / "second.zip"
            package(*roots, first)
            package(*roots, second)
            self.assertEqual(sha(first.read_bytes()), sha(second.read_bytes()))
            with zipfile.ZipFile(first) as archive:
                self.assertEqual(len(archive.namelist()), 19)
            (roots[2] / "native-full/gates.json").write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "raw gate identity"):
                package(*roots, root / "tampered.zip")

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
