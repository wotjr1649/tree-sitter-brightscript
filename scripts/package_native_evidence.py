"""Verify three hosted qualification artifacts and make a source-only release evidence ZIP."""
import argparse
import hashlib
import json
import zipfile
from pathlib import Path

from build_native_evidence import REQUIRED_GATES, incremental_signatures, signatures
from compare_native_evidence import compare, load


FILES = ("native-evidence.json", "native-full/identity.json", "native-full/gates.json",
         "native-full/runs.jsonl", "oracle-a/manifest.json", "oracle-b/manifest.json")


def sha(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def verified_files(root, platform, common):
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError(f"invalid {platform} artifact root")
    paths = {name: root / name for name in FILES}
    for name, path in paths.items():
        if (path.is_symlink() or path.parent.is_symlink() or not path.is_file()
                or path.stat().st_size > (64 if name.endswith("runs.jsonl") else 32) * 2**20):
            raise ValueError(f"missing, linked or oversized {platform}/{name}")
    evidence = load(paths["native-evidence.json"])
    host = evidence["host"]
    if evidence["common"] != common or host["platform"] != platform:
        raise ValueError(f"{platform} evidence identity mismatch")
    identity = json.loads(paths["native-full/identity.json"].read_text(encoding="utf-8"))
    gates = json.loads(paths["native-full/gates.json"].read_text(encoding="utf-8"))
    if (sha(paths["native-full/identity.json"]) != host["identity_sha256"]
            or sha(paths["native-full/gates.json"]) != host["gates_sha256"]
            or gates["identity"] != identity or not identity["git_clean"]
            or identity["git_head"] != common["commit"] or identity["candidate"] != common["candidate"]
            or identity["runner_image"] != host["runner_image"]
            or [g["gate"] for g in gates["results"]] != list(REQUIRED_GATES)
            or any(g["status"] != "PASS" for g in gates["results"])):
        raise ValueError(f"{platform} raw gate identity mismatch")
    if (signatures(paths["native-full/runs.jsonl"]) != common["native_runs"]
            or gates["results"][REQUIRED_GATES.index("SEM-PUBLIC")]["points"][0]["native_tree_digests"]
            != common["native_trees"]
            or incremental_signatures(gates["results"][REQUIRED_GATES.index("INCREMENTAL-REPAIR")]["points"])
            != common["incremental"]):
        raise ValueError(f"{platform} raw native results differ")
    if paths["oracle-a/manifest.json"].read_bytes() != paths["oracle-b/manifest.json"].read_bytes():
        raise ValueError(f"{platform} W12 recordings differ")
    oracle = json.loads(paths["oracle-a/manifest.json"].read_text(encoding="utf-8"))["identity"]
    if (oracle["grammar_commit"] != common["commit"] or oracle["platform"] != platform
            or not oracle["generated_files"]
            or any(common["candidate"].get(name) != digest
                   for name, digest in oracle["generated_files"].items())
            or oracle["cli_binary_sha256"] != host["cli_binary_sha256"]
            or oracle["workload"] != common["oracle_workload"]
            or oracle["content_sha256"] != common["oracle_content_sha256"]):
        raise ValueError(f"{platform} W12 identity mismatch")
    return paths


def package(windows, ubuntu, macos, out):
    roots = {"windows": Path(windows), "ubuntu": Path(ubuntu), "macos": Path(macos)}
    common = compare(*(root / "native-evidence.json" for root in roots.values()))
    sources = {name: verified_files(roots[name], platform, common)
               for name, platform in (("windows", "win32"), ("ubuntu", "linux"), ("macos", "darwin"))}
    out = Path(out)
    if out.exists():
        raise ValueError("evidence ZIP already exists")
    out.parent.mkdir(parents=True, exist_ok=True)
    entries = []
    with zipfile.ZipFile(out, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for host, files in sources.items():
            for name, path in files.items():
                data = path.read_bytes()
                member = f"{host}/{name}"
                item = zipfile.ZipInfo(member, date_time=(1980, 1, 1, 0, 0, 0))
                item.compress_type = zipfile.ZIP_DEFLATED
                item.external_attr = 0o644 << 16
                archive.writestr(item, data)
                entries.append({"path": member, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)})
        receipt = {"commit": common["commit"], "gates": len(REQUIRED_GATES),
                   "native_trees": len(common["native_trees"]), "oracle_cases": common["oracle_cases"],
                   "files": entries}
        item = zipfile.ZipInfo("manifest.json", date_time=(1980, 1, 1, 0, 0, 0))
        item.compress_type = zipfile.ZIP_DEFLATED
        item.external_attr = 0o644 << 16
        archive.writestr(item, json.dumps(receipt, indent=2) + "\n")
    return out


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for name in ("windows", "ubuntu", "macos", "out"):
        parser.add_argument(f"--{name}", required=True)
    args = parser.parse_args()
    target = package(args.windows, args.ubuntu, args.macos, args.out)
    print(f"THREE_OS_EVIDENCE_ZIP_PASS sha256={sha(target)} bytes={target.stat().st_size}")
