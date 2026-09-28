"""Small positive and planted-difference controls for cross-OS evidence comparison."""
import hashlib
import copy
import json
from functools import lru_cache
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path

from build_native_evidence import REQUIRED_GATES, build, signatures, registered_run_keys
from check_oracle_pair import compare as compare_oracles
from compare_native_evidence import compare as compare_hosts
from package_native_evidence import package
from package_repeated_native_evidence import HOSTS, repeated
from qualify.test_latency_diagnostic import WitnessRecords
from qualify.test_gates_v4 import V4Judgement
from qualify.test_etw_diagnostic import EtwDiagnostic
from qualify.test_completion_pilot import CompletionPilot
from qualify.test_response_policy import ResponsePolicy, CancellationRecords, PlainRecords
from qualify import response_policy


def sha(data):
    return hashlib.sha256(data).hexdigest()


@lru_cache(maxsize=1)
def response_fixture():
    """Complete synthetic response segment, including separately retained historical failures."""
    rows, results = [], []

    class Capture:
        def __init__(self, runner):
            self.runner, self.lab = runner, runner.lab

        def run(self, *args, **kwargs):
            row = self.runner.run(*args, **kwargs)
            row["report"].update(pid=len(rows) + 1, memory_metric="host-memory")
            row["final"].update(nodes=0, errors=0, missing=0, max_depth=0, captures=0, match_limit_exceeded=False)
            rows.append(row)
            return row

    for runner, judge in ((CancellationRecords(), response_policy.gates_v4.cancel),
                          (PlainRecords(1.), response_policy.gates.overshoot),
                          (PlainRecords(), response_policy.gates.gaps_and_cleanup)):
        result = response_policy.evaluate(Capture(runner), judge)
        results.extend(result if isinstance(result, list) else [result])
    return results, rows


def gate_records():
    results = [{"gate": name, "status": "PASS", "points": []} for name in REQUIRED_GATES]
    for result in response_fixture()[0]:
        results[REQUIRED_GATES.index(result["gate"])] = copy.deepcopy(result)
    return results


class NativeEvidence(unittest.TestCase):
    def test_exact_registration_preserves_v3_and_rejects_equal_count_replacement(self):
        old, current = registered_run_keys(False), registered_run_keys()
        self.assertEqual((len(old), len(current), len(current - old)), (1533, 1768, 235))
        self.assertTrue(old < current)
        with tempfile.TemporaryDirectory() as tmp:
            paths = [Path(tmp) / f"{name}.json" for name in ("windows", "ubuntu", "macos")]
            common = self.common()
            removed = sorted(old)[0]
            common["native_runs"]["cand|PARSE|unregistered"] = common["native_runs"].pop(removed)
            for path, platform, arch in zip(paths, ("win32", "linux", "darwin"), ("amd64", "x86_64", "arm64")):
                path.write_text(json.dumps({"common": common, "host": {"platform": platform, "architecture": arch,
                                "runner_image": {"os": platform, "version": "test",
                                                 "runner_arch": "ARM64" if platform == "darwin" else "X64"}}}))
            with self.assertRaisesRegex(ValueError, "native run"):
                compare_hosts(*paths)

    @staticmethod
    def common():
        zero = "0" * 64
        return {"commit": "a" * 40, "candidate": {"src/parser.c": zero, "grammar.js": zero},
                "lane_sources": {"run.py": zero},
                "protocol": "v5", "response_policy": response_policy.IDENTITY, "runtime": "0.27.0", "support": ["0.25.1", "0.26.13"], "seed": 5707,
                "gate_statuses": list(REQUIRED_GATES), "oracle_cases": 231,
                "oracle_workload": {"cases": 231, "sha256": zero}, "oracle_content_sha256": zero,
                "native_trees": [{"name": f"case-{i}", "input_sha256": zero, "tree_sha256": zero}
                                 for i in range(2811)],
                "native_runs": {key: {"bytes": 1} for key in sorted(registered_run_keys())},
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
            original = paths[0].read_text(encoding="utf-8")
            obsolete = json.loads(original)
            obsolete["common"]["protocol"] = "v4"
            paths[0].write_text(json.dumps(obsolete), encoding="utf-8")
            with self.assertRaises(ValueError):
                compare_hosts(*paths)
            paths[0].write_text(original, encoding="utf-8")
            for protocol, limit in (("v4.1", 250), ("v5", 100), ("v5", 500)):
                changed = json.loads(original)
                changed["common"]["protocol"] = protocol
                policy = changed["common"]["response_policy"]
                policy["spec"]["limits_ms"]["callback_gap_ms"] = limit
                policy["sha256"] = sha(json.dumps(policy["spec"], sort_keys=True, separators=(",", ":")).encode())
                paths[0].write_text(json.dumps(changed), encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "response policy"):
                    compare_hosts(*paths)
            paths[0].write_text(original, encoding="utf-8")
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
                        "lane_sources": common["lane_sources"], "runtime": common["runtime"], "protocol": "v5", "response_policy": response_policy.IDENTITY,
                        "support": common["support"], "seed": common["seed"], "cc_sha256": "0" * 64,
                        "runner_image": {"os": "win25", "version": "test", "runner_arch": "X64"},
                        "supervisor_kind": "windows_job", "probes": {"cand": "0" * 64}}
            (q / "identity.json").write_text(json.dumps(identity), encoding="utf-8")
            gates = gate_records()
            gates[REQUIRED_GATES.index("SEM-PUBLIC")]["points"] = [{"native_tree_digests": common["native_trees"]}]
            gates[REQUIRED_GATES.index("INCREMENTAL-REPAIR")]["points"] = common["incremental"]
            (q / "gates.json").write_text(json.dumps({"identity": identity, "results": gates}), encoding="utf-8")
            final = {"final": True, "bytes": 1, "cancelled": False, "has_error": 0, "nodes": 1,
                     "errors": 0, "missing": 0, "max_depth": 0, "captures": 0,
                     "match_limit_exceeded": False}
            run = {"budget": 0, "completed": True, "build": "cand", "op": "PARSE", "case": "one",
                   "final": final, "events": {}, "report": {"memory_metric": "windows_private_commit"}}
            (q / "runs.jsonl").write_text("".join(json.dumps(x) + "\n" for x in [run, *response_fixture()[1]]), encoding="utf-8")
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
            self.assertEqual(result["host"]["runs_sha256"], sha((q / "runs.jsonl").read_bytes()))
            gates[REQUIRED_GATES.index("CANCEL")]["legacy_v4_1_100ms"] = {"gate": "CANCEL", "status": "FAIL"}
            (q / "gates.json").write_text(json.dumps({"identity": identity, "results": gates}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "response raw replay"):
                build(q, root / "oracle-a", root / "oracle-b")

    def test_evidence_zip_checks_raw_records_and_is_reproducible(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            common = self.common()
            final = {"final": True, "bytes": 1, "cancelled": False, "has_error": 0, "nodes": 1,
                     "errors": 0, "missing": 0, "max_depth": 0, "captures": 0,
                     "match_limit_exceeded": False}
            response_rows = response_fixture()[1]
            response_finals = {"|".join(x[k] for k in ("build", "op", "case")): x["final"]
                               for x in response_rows if x["budget"] == 0}
            runs = "".join(json.dumps({"budget": 0, "completed": True, "build": b, "op": o,
                                      "case": c, "final": response_finals.get("|".join((b,o,c)), final), "events": {},
                                      "report": {"memory_metric": "host-memory"}}) + "\n"
                           for b, o, c in (key.split("|") for key in sorted(registered_run_keys())))
            runs += "".join(json.dumps(x) + "\n" for x in response_rows)
            runs += json.dumps({"budget": 100, "completed": True, "report": {"memory_metric": "host-memory"}}) + "\n"
            with (root / "runs.jsonl").open("w", encoding="utf-8") as output:
                output.write(runs)
            common["native_runs"] = signatures(root / "runs.jsonl")
            records = [{"n": i, "name": f"oracle-{i}", "input_sha256": "1" * 64,
                        "tree_sha256": "2" * 64, "cst_sha256": "3" * 64,
                        "has_error": False, "expected_error": False} for i in range(231)]
            common["oracle_workload"]["sha256"] = sha(("1" * 64 * 231).encode())
            common["oracle_content_sha256"] = sha((("1" * 64 + "2" * 64 + "3" * 64) * 231).encode())
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
                            "runner_image": runner_image, "lane_sources": common["lane_sources"],
                            "protocol": "v5", "response_policy": response_policy.IDENTITY, "runtime": common["runtime"], "support": common["support"], "seed": common["seed"],
                            "cc_sha256": "0" * 64, "probes": {"cand": "0" * 64},
                            "supervisor_sha256": "0" * 64 if platform == "win32" else None,
                            "supervisor_kind": "test-supervisor"}
                gates = gate_records()
                gates[REQUIRED_GATES.index("SEM-PUBLIC")]["points"] = [
                    {"native_tree_digests": common["native_trees"]}]
                gates[REQUIRED_GATES.index("INCREMENTAL-REPAIR")]["points"] = common["incremental"]
                (host_root / "native-full/identity.json").write_text(json.dumps(identity), encoding="utf-8")
                (host_root / "native-full/gates.json").write_text(json.dumps(
                    {"identity": identity, "results": gates}), encoding="utf-8")
                oracle = {"identity": {"grammar_commit": common["commit"], "platform": platform,
                                       "generated_files": {"src/parser.c": common["candidate"]["src/parser.c"]},
                                       "cli_binary_sha256": "0" * 64,
                                       "generator": "tree-sitter 0.27.0", "abi": 15,
                                       "workload": common["oracle_workload"],
                                       "content_sha256": common["oracle_content_sha256"]},
                          "results": records}
                for oracle_name in ("oracle-a", "oracle-b"):
                    (host_root / oracle_name / "manifest.json").write_text(json.dumps(oracle), encoding="utf-8")
                evidence = {"common": common, "host": {"platform": platform, "architecture": arch,
                            "runner_image": runner_image, "identity_sha256": sha((host_root / "native-full/identity.json").read_bytes()),
                            "gates_sha256": sha((host_root / "native-full/gates.json").read_bytes()),
                            "runs_sha256": sha((host_root / "native-full/runs.jsonl").read_bytes()),
                            "cli_binary_sha256": "0" * 64, "cc_sha256": "0" * 64,
                            "probe_sha256": {"cand": "0" * 64}, "supervisor_kind": "test-supervisor",
                            "supervisor_sha256": identity["supervisor_sha256"],
                            "memory_metric": "host-memory"}}
                (host_root / "native-evidence.json").write_text(json.dumps(evidence), encoding="utf-8")
            first, second = root / "first.zip", root / "second.zip"
            package(*roots, first)
            package(*roots, second)
            self.assertEqual(sha(first.read_bytes()), sha(second.read_bytes()))
            with zipfile.ZipFile(first) as archive:
                self.assertEqual(len(archive.namelist()), 19)
                self.assertEqual(json.loads(archive.read("manifest.json"))["response_policy"], response_policy.IDENTITY)
            target = roots[2]
            gate_path, evidence_path = target / "native-full/gates.json", target / "native-evidence.json"
            original_gate, original_evidence = gate_path.read_bytes(), evidence_path.read_bytes()
            for name in response_policy.GATES:
                changed = json.loads(original_gate)
                legacy = changed["results"][REQUIRED_GATES.index(name)]["legacy_v4_1_100ms"]
                del legacy["points"]
                gate_path.write_text(json.dumps(changed), encoding="utf-8")
                changed_evidence = json.loads(original_evidence)
                changed_evidence["host"]["gates_sha256"] = sha(gate_path.read_bytes())
                evidence_path.write_text(json.dumps(changed_evidence), encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "response raw replay"):
                    package(*roots, root / "truncated-legacy.zip")
            gate_path.write_bytes(original_gate)
            evidence_path.write_bytes(original_evidence)
            cohorts = [root / name for name in ("cohort-a", "cohort-b")]
            for cohort, run_id in zip(cohorts, ("101", "202")):
                for source, name in zip(roots, HOSTS):
                    target = cohort / name
                    shutil.copytree(source, target)
                    hosted = {"id": run_id, "attempt": "1", "job": "native-qualification"}
                    identity_path = target / "native-full/identity.json"
                    gate_path = target / "native-full/gates.json"
                    evidence_path = target / "native-evidence.json"
                    identity = json.loads(identity_path.read_text())
                    identity["hosted_run"] = hosted
                    identity_path.write_text(json.dumps(identity))
                    gate_record = json.loads(gate_path.read_text())
                    gate_record["identity"] = identity
                    gate_path.write_text(json.dumps(gate_record))
                    evidence = json.loads(evidence_path.read_text())
                    evidence["host"].update(hosted_run=hosted, identity_sha256=sha(identity_path.read_bytes()),
                                            gates_sha256=sha(gate_path.read_bytes()))
                    evidence_path.write_text(json.dumps(evidence))
            with self.assertRaisesRegex(ValueError, "same hosted run"):
                repeated(cohorts[0], cohorts[0], root / "duplicate-cohort.zip")
            with self.assertRaisesRegex(ValueError, "duplicate raw file"):
                repeated(*cohorts, root / "relabeled-cohort.zip")
            for name in HOSTS:
                target = cohorts[1] / name
                raw_path = target / "native-full/runs.jsonl"
                lines = raw_path.read_text().splitlines()
                timed = json.loads(lines[-1])
                timed["report"]["pid"] = 202  # synthetic independent report, excluded from exact behavior
                lines[-1] = json.dumps(timed)
                raw_path.write_text("\n".join(lines) + "\n")
                evidence_path = target / "native-evidence.json"
                evidence = json.loads(evidence_path.read_text())
                evidence["host"]["runs_sha256"] = sha(raw_path.read_bytes())
                evidence_path.write_text(json.dumps(evidence))
            combined = repeated(*cohorts, root / "six-jobs.zip")
            repeated(*cohorts, root / "six-jobs-again.zip")
            self.assertEqual(sha(combined.read_bytes()), sha((root / "six-jobs-again.zip").read_bytes()))
            with zipfile.ZipFile(combined) as archive:
                self.assertEqual(set(archive.namelist()), {"manifest.json", "cohort-1.zip", "cohort-2.zip"})
                self.assertEqual(json.loads(archive.read("manifest.json"))["os_jobs"], 6)
                self.assertEqual(json.loads(archive.read("manifest.json"))["protocol"], "v5")
                self.assertEqual(json.loads(archive.read("manifest.json"))["response_policy"], response_policy.IDENTITY)
            target = cohorts[1] / HOSTS[0]
            changed_paths = [target / name for name in ("native-full/identity.json", "native-full/gates.json",
                                                       "native-evidence.json")]
            originals = [path.read_bytes() for path in changed_paths]
            identity, gate_record, evidence = [json.loads(data) for data in originals]
            identity["supervisor_sha256"] = "1" * 64
            changed_paths[0].write_text(json.dumps(identity))
            gate_record["identity"] = identity
            changed_paths[1].write_text(json.dumps(gate_record))
            evidence["host"].update(supervisor_sha256="1" * 64, identity_sha256=sha(changed_paths[0].read_bytes()),
                                    gates_sha256=sha(changed_paths[1].read_bytes()))
            changed_paths[2].write_text(json.dumps(evidence))
            with self.assertRaisesRegex(ValueError, "image or tool"):
                repeated(*cohorts, root / "mixed-supervisors.zip")
            for path, data in zip(changed_paths, originals):
                path.write_bytes(data)
            evidence_path = cohorts[1] / HOSTS[-1] / "native-evidence.json"
            original = evidence_path.read_text()
            evidence = json.loads(original)
            evidence["host"]["runner_image"]["version"] = "different"
            evidence_path.write_text(json.dumps(evidence))
            with self.assertRaisesRegex(ValueError, "image or tool"):
                repeated(*cohorts, root / "mixed-images.zip")
            evidence_path.write_text(original)
            gate_path = cohorts[1] / HOSTS[-1] / "native-full/gates.json"
            gate_path.write_text("{}")
            with self.assertRaisesRegex(ValueError, "raw gate identity"):
                repeated(*cohorts, root / "tampered-cohort.zip")
            mac_gates = roots[2] / "native-full/gates.json"
            original_gates = mac_gates.read_text(encoding="utf-8")
            mac_gates.write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "raw gate identity"):
                package(*roots, root / "tampered.zip")
            mac_gates.write_text(original_gates, encoding="utf-8")
            manifests = [roots[2] / name / "manifest.json" for name in ("oracle-a", "oracle-b")]
            original_manifest = manifests[0].read_text(encoding="utf-8")
            incomplete = json.loads(original_manifest)
            incomplete["results"] = []
            for path in manifests:
                path.write_text(json.dumps(incomplete), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "W12 result set"):
                package(*roots, root / "missing-w12.zip")
            for path in manifests:
                path.write_text(original_manifest, encoding="utf-8")
            raw_runs = roots[2] / "native-full/runs.jsonl"
            raw_runs.write_text("".join(raw_runs.read_text(encoding="utf-8").splitlines(keepends=True)[:-1]),
                                encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "raw runs hash"):
                package(*roots, root / "missing-cancellation.zip")
            raw_runs.write_text(runs, encoding="utf-8")
            for host_root in roots:
                path = host_root / "native-evidence.json"
                changed = json.loads(path.read_text(encoding="utf-8"))
                changed["common"]["lane_sources"] = {"run.py": "f" * 64}
                path.write_text(json.dumps(changed), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "raw gate identity"):
                package(*roots, root / "false-tool.zip")

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
