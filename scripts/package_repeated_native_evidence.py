"""Bind two independently allocated three-OS qualification cohorts into release evidence."""
import argparse
import hashlib
import json
import tempfile
import zipfile
from pathlib import Path

from compare_native_evidence import compare, digest, load
from package_native_evidence import package

HOSTS = ("native-windows-2025-vs2026", "native-ubuntu-24.04", "native-macos-15")
COHORT_KEYS = ("platform", "architecture", "runner_image", "cc_sha256", "cli_binary_sha256",
               "supervisor_kind", "supervisor_sha256", "probe_sha256", "memory_metric")


def repeated(first, second, out):
    roots = [[Path(root) / host for host in HOSTS] for root in (first, second)]
    common = [compare(*(root / "native-evidence.json" for root in cohort)) for cohort in roots]
    if common[0] != common[1]:
        raise ValueError("qualification cohorts have different candidate or functional results")
    hosts = [[load(root / "native-evidence.json")["host"] for root in cohort] for cohort in roots]
    runs = []
    for cohort in hosts:
        run = cohort[0].get("hosted_run")
        if (not isinstance(run, dict) or set(run) != {"id", "attempt", "job"}
                or not isinstance(run["id"], str) or not run["id"].isascii() or not run["id"].isdecimal()
                or int(run["id"]) <= 0 or run["attempt"] != "1" or run["job"] != "native-qualification"
                or any(host.get("hosted_run") != run for host in cohort)):
            raise ValueError("missing independent first-attempt hosted cohort identity")
        runs.append(run)
    if runs[0]["id"] == runs[1]["id"]:
        raise ValueError("the same hosted run cannot count as two cohorts")
    for left, right in zip(*hosts):
        for host in (left, right):
            if (not digest(host.get("supervisor_sha256")) if host["platform"] == "win32"
                    else host.get("supervisor_sha256") is not None):
                raise ValueError("missing or invalid supervisor identity")
        if any(left[k] != right[k] for k in COHORT_KEYS):
            raise ValueError("runner image or tool identities changed between cohorts")
        if left["runs_sha256"] == right["runs_sha256"]:
            raise ValueError("a duplicate raw file cannot count as independent measurement")
    out = Path(out)
    if out.exists():
        raise ValueError("release evidence ZIP already exists")
    out.parent.mkdir(parents=True, exist_ok=True)
    # Existing packager rechecks every raw hash, gate, W12 and normalized result.
    # Both cohorts are verified before the release ZIP is opened.
    with tempfile.TemporaryDirectory(prefix="native-cohorts-", dir=out.parent) as directory:
        zips = [package(*cohort, Path(directory) / f"cohort-{i}.zip") for i, cohort in enumerate(roots, 1)]
        entries = [(f"cohort-{i}.zip", path.read_bytes()) for i, path in enumerate(zips, 1)]
        receipt = {"commit": common[0]["commit"], "protocol": common[0]["protocol"],
                   "response_policy": common[0]["response_policy"], "verdict": "PASS",
                   "hosted_runs": runs, "os_jobs": 6, "gates_per_job": 17,
                   "native_keys": len(common[0]["native_runs"]),
                   "files": [{"path": name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
                             for name, data in entries]}
        entries.append(("manifest.json", (json.dumps(receipt, indent=2) + "\n").encode()))
        with zipfile.ZipFile(out, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            for name, data in entries:
                item = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                item.compress_type = zipfile.ZIP_DEFLATED
                item.external_attr = 0o644 << 16
                archive.writestr(item, data)
    return out


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for name in ("first", "second", "out"):
        parser.add_argument(f"--{name}", required=True)
    args = parser.parse_args()
    target = repeated(args.first, args.second, args.out)
    print(f"SIX_JOB_EVIDENCE_PASS sha256={hashlib.sha256(target.read_bytes()).hexdigest()}")
