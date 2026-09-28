"""Fail closed unless the three supported OS report the same normalized native behavior."""
import argparse
import json
import re
from pathlib import Path

from build_native_evidence import REQUIRED_GATES, registered_run_keys

SHA256 = re.compile(r"[0-9a-f]{64}\Z")
SHA1 = re.compile(r"[0-9a-f]{40}\Z")
COMMON_KEYS = {"commit", "candidate", "lane_sources", "protocol", "runtime", "support", "seed", "gate_statuses",
               "oracle_cases", "oracle_workload", "oracle_content_sha256", "native_trees", "native_runs",
               "incremental"}
ARCHITECTURES = {"win32": {"amd64", "x86_64"}, "linux": {"x86_64", "amd64"},
                 "darwin": {"arm64", "aarch64"}}


def digest(value):
    return isinstance(value, str) and SHA256.fullmatch(value) is not None


def load(path):
    path = Path(path)
    if not path.is_file() or path.is_symlink() or path.stat().st_size > 16 * 2**20:
        raise ValueError(f"missing or oversized evidence: {path.name}")
    result = json.loads(path.read_text(encoding="utf-8"))
    if set(result) != {"common", "host"} or not isinstance(result["common"], dict):
        raise ValueError("incomplete native evidence")
    common, host = result["common"], result["host"]
    if set(common) != COMMON_KEYS or not isinstance(host, dict) or host.get("platform") not in ARCHITECTURES:
        raise ValueError("incomplete native evidence")
    if host.get("architecture") not in ARCHITECTURES[host["platform"]]:
        raise ValueError("unsupported host architecture")
    image = host.get("runner_image")
    if (not isinstance(image, dict) or not isinstance(image.get("os"), str) or not image["os"]
            or not isinstance(image.get("version"), str) or not image["version"]
            or image.get("runner_arch") != ("ARM64" if host["platform"] == "darwin" else "X64")):
        raise ValueError("missing runner image identity")
    if (not isinstance(common["commit"], str) or not SHA1.fullmatch(common["commit"])
            or common["gate_statuses"] != list(REQUIRED_GATES)
            or common["protocol"] != "v4" or common["runtime"] != "0.27.0" or common["support"] != ["0.25.1", "0.26.13"]
            or common["seed"] != 5707 or common["oracle_cases"] != 231
            or common["oracle_workload"].get("cases") != 231
            or not digest(common["oracle_workload"].get("sha256"))
            or not digest(common["oracle_content_sha256"])):
        raise ValueError("incomplete native identity")
    for key in ("candidate", "lane_sources"):
        if not isinstance(common[key], dict) or not common[key] or not all(digest(v) for v in common[key].values()):
            raise ValueError(f"incomplete {key} identity")
    trees = common["native_trees"]
    if (not isinstance(trees, list) or len(trees) != 2811
            or any(not isinstance(t, dict) or set(t) != {"name", "input_sha256", "tree_sha256"}
                   or not isinstance(t["name"], str) or not digest(t["input_sha256"])
                   or not digest(t["tree_sha256"]) for t in trees)
            or len({t["name"] for t in trees}) != len(trees)):
        raise ValueError("incomplete native tree results")
    if not isinstance(common["native_runs"], dict) or set(common["native_runs"]) != registered_run_keys():
        raise ValueError("incomplete native run results")
    incremental = common["incremental"]
    if (not isinstance(incremental, list) or len(incremental) != 30
            or any(not isinstance(p, dict) or p.get("pass") is not True for p in incremental)
            or [p.get("case") for p in incremental if "detected" in p] != [
                "comparator self-test 1", "comparator self-test 2"]):
        raise ValueError("incomplete incremental results")
    return result


def compare(windows, ubuntu, macos):
    records = [load(path) for path in (windows, ubuntu, macos)]
    if [r["host"]["platform"] for r in records] != ["win32", "linux", "darwin"]:
        raise ValueError("missing or mislabelled OS result")
    reference = records[0]["common"]
    for name, record in zip(("ubuntu", "macos"), records[1:]):
        if record["common"] != reference:
            keys = sorted(k for k in reference.keys() | record["common"].keys()
                          if reference.get(k) != record["common"].get(k))
            raise ValueError(f"{name} native output differs: {keys[:8]}")
    return reference


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--windows", required=True)
    parser.add_argument("--ubuntu", required=True)
    parser.add_argument("--macos", required=True)
    args = parser.parse_args()
    common = compare(args.windows, args.ubuntu, args.macos)
    print(f"THREE_OS_NATIVE_PARITY_PASS gates={len(common['gate_statuses'])} "
          f"trees={len(common['native_trees'])} oracle={common['oracle_cases']}")
