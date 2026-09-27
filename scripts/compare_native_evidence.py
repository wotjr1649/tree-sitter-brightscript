"""Fail closed unless the three supported OS report the same normalized native behavior."""
import argparse
import json
from pathlib import Path


def load(path):
    path = Path(path)
    if not path.is_file() or path.is_symlink() or path.stat().st_size > 16 * 2**20:
        raise ValueError(f"missing or oversized evidence: {path.name}")
    result = json.loads(path.read_text(encoding="utf-8"))
    if set(result) != {"common", "host"} or len(result["common"]["gate_statuses"]) != 17:
        raise ValueError("incomplete native evidence")
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
