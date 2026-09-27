"""Offline public replay. Run with Python -I -B -X utf8; never writes inputs.

Usage: python -I -B -X utf8 scripts/verify_public.py --bundle DIR --baseline-source DIR
       [--candidate-source DIR --candidate-registration FILE]
The baseline graph is the immutable public v0.1.1 graph, including its pinned
v0.1.0 -> v0.1.1 proof. Candidate registration is a separate graph.
Trust the verifier and its sibling replay_compare.py from the reviewed source
asset. SHA-256 checks establish integrity, not provenance authentication.
"""
import sys

if __name__ == "__main__" and (not sys.flags.isolated or not __debug__):
    raise SystemExit("use Python -I -B -X utf8 without -O for public verification")
sys.dont_write_bytecode = True

import argparse
from collections import deque
import hashlib
import json
from pathlib import Path, PurePosixPath
import platform
import re
# Load the baseline's stdlib dependencies before its source paths are admitted.
# The public entrypoint also requires an isolated interpreter.
import copy
import random
import statistics
import subprocess

# This directory is the reviewed verifier package, never a bundle-provided path.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import replay_compare as comparison

BASE_MANIFEST = "ce2abd0a05fd4dc15b26b85a27a20625063bbc4f838aaded2c0866c315f15bbb"
BASE_K1 = "ebe8c4ce2c5bbe21a1b1e90d1c6a8b9824aca4931074015b6de20ccb35a19f2e"
MODULES = {"corpus": ("scripts/corpus.py", "5161dcdcbc766c96d037355307d6b2d145ea842a2b495130318ab5b5136bb64e"),
           "cases": ("scripts/qualify/cases.py", "93ec08a76a46b16dd81f8f310a314c10a4ba32f6be6e826cbf1ab15ecdb22f44"),
           "gates": ("scripts/qualify/gates.py", "33fa4e47042f59fa4fd7807d4946eb88f0345aea63f376719b2efa3bc5024a73"),
           "check_maintenance": ("scripts/check_maintenance.py", "c9487bd06c41709114c141f264b4af05b5d6b3ebaed703741ff8f9b91cba2302")}


def require(condition, message):
    if not condition:
        raise comparison.ReplayMismatch(message)


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def load(path):
    return comparison.strict_json(Path(path).read_bytes())


def member(root, name):
    require(type(name) is str, "non-string path")
    p = PurePosixPath(name)
    require(name == p.as_posix() and not p.is_absolute() and ".." not in p.parts and "\\" not in name
            and ":" not in name and all(not x.endswith((" ", ".")) for x in p.parts), "unsafe member path")
    path = root
    for part in p.parts:
        path = path / part
        require(not path.is_symlink() and not path.is_junction(), "linked member")
    require(path.resolve().is_relative_to(root.resolve()), "member escapes root")
    return path


def verify_files(root, rows, extra=()):
    require(type(rows) is list and len(rows) <= 16000, "file list/count bound")
    total = 0
    for row in rows:
        require(type(row) is dict and type(row.get("bytes")) is int and 0 <= row["bytes"] <= 32 * 2**20,
                "file identity type/size bound")
        total += row["bytes"]
    require(total <= 160 * 2**20, "total source/verification size bound")
    seen = set()
    for row in rows:
        require(set(row) >= {"path", "sha256", "bytes"}, "file manifest schema")
        name = row["path"]
        path = member(root, name)
        require(name.casefold() not in seen, "duplicate/case-colliding path")
        seen.add(name.casefold())
        require(type(row["bytes"]) is int and row["bytes"] >= 0 and type(row["sha256"]) is str
                and re.fullmatch("[0-9a-f]{64}", row["sha256"]), "file identity type")
        require(path.is_file() and path.stat().st_size == row["bytes"] and sha(path) == row["sha256"],
                "file identity differs: " + name)
    actual = set()
    for entry_count, path in enumerate(root.rglob("*"), 1):
        require(entry_count <= 32000, "filesystem entry count bound")
        require(not path.is_symlink() and not path.is_junction(), "unexpected linked entry")
        if path.is_file():
            name = path.relative_to(root).as_posix().casefold()
            require(name not in actual, "case-colliding actual files")
            actual.add(name)
    require(actual == seen | set(extra), "missing or unregistered files")
    return len(seen)


def verify_source(root, files):
    require(type(files) is dict and len(files) <= 16000, "source registration map/count bound")
    rows = []
    for name, digest in files.items():
        p = member(root, name)
        rows.append({"path": name, "sha256": digest, "bytes": p.stat().st_size})
    return verify_files(root, rows)


def git_object(kind, data):
    return hashlib.sha1(kind.encode() + b" " + str(len(data)).encode() + b"\0" + data).digest()


def source_tree(root, modes):
    """Reconstruct Git's tree from bytes and registered modes, without Git."""
    tree = {}
    require(type(modes) is dict, "mode registration map")
    for name, mode in modes.items():
        require(type(mode) is int and mode in (0o100644, 0o100755), "unsupported source mode")
        path = member(root, name)
        current = tree
        parts = PurePosixPath(name).parts
        for part in parts[:-1]:
            current = current.setdefault(part, {})
            require(type(current) is dict, "file/directory collision")
        require(parts[-1] not in current, "duplicate tree member")
        current[parts[-1]] = (mode, git_object("blob", path.read_bytes()))

    def build(directory):
        entries = []
        for name, value in directory.items():
            is_dir = type(value) is dict
            mode, oid = (0o40000, build(value)) if is_dir else value
            entries.append((name.encode() + (b"/" if is_dir else b""),
                            f"{mode:o} ".encode() + name.encode() + b"\0" + oid))
        return git_object("tree", b"".join(data for _, data in sorted(entries)))
    return build(tree).hex()


def verify_candidate(bundle, baseline, source, registration_path):
    source, registration_path = Path(source).resolve(), Path(registration_path).resolve()
    q = registration_path.parent
    require(source != baseline and not source.is_relative_to(q) and not q.is_relative_to(source),
            "candidate and baseline source graphs must be separate")
    require(registration_path.name == "candidate-registration.json" and bundle == q / "baseline"
            and baseline == q / "baseline-source", "candidate graph paths differ")
    manifest = load(member(q, "VERIFICATION-MANIFEST.json"))
    require(set(manifest) == {"schema", "policy", "trusted_baseline", "files"}
            and manifest["schema"] == "S07-VERIFICATION-r1" and manifest["policy"] == comparison.POLICY,
            "unknown verification schema")
    comparison.compare_value({"tag": "v0.1.1", "K1": BASE_K1, "archives": {
        "tree-sitter-brightscript-v0.1.1-source.zip": [509486, "94891e1f22c4d62840c69d981798ece7c395ee0652a39056d23fc9f1afbc60cd"],
        "tree-sitter-brightscript-v0.1.1-verification.zip": [17195587, "5df890ab9ed9ef2786ba82acd42146f25eb69fc1741f18866d1b474a44ee2486"]}},
        manifest["trusted_baseline"])
    files = verify_files(q, manifest["files"], ("verification-manifest.json",))
    registration = load(registration_path)
    require(set(registration) == {"schema", "commit", "commit_object", "tree", "baseline_K1", "files", "modes"}
            and registration["schema"] == "S07-CANDIDATE-r1", "unknown candidate schema")
    count = verify_source(source, registration["files"])
    require(set(registration["files"]) == set(registration["modes"]), "source mode inventory differs")
    tree = source_tree(source, registration["modes"])
    require(type(registration["commit_object"]) is str, "commit object type")
    commit_data = registration["commit_object"].encode("utf-8")
    require(git_object("commit", commit_data).hex() == registration["commit"]
            and commit_data.startswith(("tree " + tree + "\n").encode())
            and tree == registration["tree"], "candidate Git graph differs")
    require(registration["baseline_K1"] == BASE_K1, "candidate baseline differs")
    for name, path in (("verify_public.py", Path(__file__)), ("replay_compare.py", Path(comparison.__file__)),
                       ("check_maintenance_012.py", Path(__file__).parent / "check_maintenance_012.py")):
        require(registration["files"]["scripts/" + name] == sha(path) == sha(member(q, name)),
                "running public tool differs from candidate: " + name)
    require("check_maintenance_012" not in sys.modules, "preloaded candidate proof module refused")
    try:
        import check_maintenance_012 as maintenance012
        require(Path(maintenance012.__file__).resolve() == (Path(__file__).parent / "check_maintenance_012.py").resolve(),
                "candidate proof import path differs")
        proof = maintenance012.compare({n: member(baseline, n).read_bytes() for n in maintenance012.COMPONENTS},
                                       {n: member(source, n).read_bytes() for n in maintenance012.COMPONENTS})
    finally:
        sys.modules.pop("check_maintenance_012", None)
    require(proof == load(member(q, "candidate-product-proof.json")) and proof["baseline_K1"] == BASE_K1,
            "candidate product proof differs")
    return {"source_files": count, "verification_files": files, "registration_sha256": sha(registration_path),
            "commit": registration["commit"], "tree": tree, "product_proof": proof,
            "scope": "source bytes, registered modes, Git object graph and narrow metadata proof; release eligibility is separate"}


class Replay:
    def __init__(self, runs):
        self.runs, self.used, self.by_key = runs, set(), {}
        process_ids = set()
        for i, row in enumerate(runs):
            require(type(row["budget"]) in (int, float) and type(row["budget"]) is not bool, "budget type")
            process = (row["report"]["pid"], row["report"]["creation_filetime"])
            require(process not in process_ids, "duplicate native execution identity")
            process_ids.add(process)
            key = (row["build"], row["op"], row["case"], row["budget"], row["tag"])
            self.by_key.setdefault(key, deque()).append(i)

    def run(self, build, op, case, budget, tag=""):
        queue = self.by_key.get((build, op, case, budget, tag))
        require(bool(queue), "missing registered run")
        index = queue.popleft()
        require(index not in self.used, "run consumed twice")
        self.used.add(index)
        return self.runs[index]

    def finish(self):
        require(len(self.runs) == len(self.used) == 8875 and not any(self.by_key.values()), "incomplete replay")


def import_baseline(source):
    require(not (set(MODULES) & set(sys.modules)), "preloaded baseline module refused")
    for name, (path, digest) in MODULES.items():
        require(sha(member(source, path)) == digest, "unreviewed baseline module: " + name)
    saved_path = sys.path[:]
    # The complete baseline source inventory was already checked against the
    # pinned public manifest; it cannot contain an added shadow module. Put its
    # four modules before the current verifier package's same-named sources.
    # Its stdlib dependencies have already been loaded by the isolated entrypoint.
    sys.path[:0] = [str(source / "scripts"), str(source / "scripts/qualify")]
    try:
        import corpus
        import cases
        import gates
        import check_maintenance
        for name, (path, digest) in MODULES.items():
            module = sys.modules[name]
            require(Path(module.__file__).resolve() == (source / path).resolve() and sha(module.__file__) == digest,
                    "actual import differs: " + name)
        return gates, check_maintenance
    except BaseException:
        for name in MODULES:
            sys.modules.pop(name, None)
        raise
    finally:
        sys.path[:] = saved_path


def verify(bundle, baseline_source, candidate_source=None, candidate_registration=None):
    require(__debug__, "optimized Python unsupported")
    bundle, source = Path(bundle).resolve(), Path(baseline_source).resolve()
    require(sha(member(bundle, "SOURCE-MANIFEST.json")) == BASE_MANIFEST, "untrusted baseline manifest")
    file_count = verify_files(bundle, load(bundle / "SOURCE-MANIFEST.json")["files"], ("source-manifest.json",))
    registration = load(bundle / "session/candidate-registration-r03.json")
    source_count = verify_source(source, registration["files"])
    require(sha(source / MODULES["cases"][0]) == MODULES["cases"][1], "case source changed")
    gates, maintenance = import_baseline(source)
    try:
        proof = maintenance.compare({n: member(bundle / "baseline-product", n).read_bytes() for n in maintenance.COMPONENTS},
                                    {n: member(source, n).read_bytes() for n in maintenance.COMPONENTS})
        recorded = load(bundle / "session/equivalence-proof-r03.json")
        require(proof["K0"] == recorded["K0"] and proof["K1"] == recorded["K1"] == BASE_K1, "baseline product differs")
        rounds = {}
        for rnd in ("q1", "q2", "q3"):
            directory = bundle / "baseline" / rnd
            runs = [comparison.strict_json(s) for s in (directory / "runs.jsonl").read_bytes().splitlines()]
            results = load(directory / "gates.json")["results"]
            require([r["gate"] for r in results] == list(comparison.GATES), "gate set/order differs")
            wanted = {r["gate"]: r for r in results}
            seed = load(directory / "identity.json")["seed"]
            require(type(seed) is int, "seed type")
            replay = Replay(runs)
            plan = [gates.b5_01_memory, gates.b5_02_lifecycle, lambda r: gates.a5_01_cost(r, seed), gates.cancel,
                    gates.overshoot, gates.gaps_and_cleanup, gates.large_input, gates.query_malformed,
                    lambda r: gates.valid_parse(r, seed), lambda r: gates.support(r, ["0.25.1", "0.26.13"]), gates.sweep]
            checked = []
            for function in plan:
                got = function(replay)
                for result in got if isinstance(got, list) else [got]:
                    normalized = comparison.strict_json(json.dumps(result, allow_nan=False))
                    checked.append(comparison.compare_gate(wanted[result["gate"]], normalized))
            checked.append(comparison.compare_gate(wanted["ABS-MEMORY"],
                           comparison.strict_json(json.dumps(gates.abs_memory(runs), allow_nan=False))))
            replay.finish()
            require(len(checked) == 13 and len({r["gate_id"] for r in checked}) == 13, "recomputed gate count")
            rounds[rnd] = {"evidence_mode": "REPLAYED_RAW", "used_runs": len(replay.used),
                           "recomputed": checked, "recorded_not_recomputed": {r["gate"]: r["status"] for r in results
                           if r["gate"] not in {g["gate_id"] for g in checked}}}
        candidate = None
        require((candidate_source is None) == (candidate_registration is None), "both candidate arguments required")
        if candidate_source is not None:
            candidate = verify_candidate(bundle, source, candidate_source, candidate_registration)
        return {"assessment": "PASS", "policy": comparison.POLICY, "public_files": file_count,
                "baseline_source_files": source_count, "baseline_K1": proof["K1"], "candidate": candidate,
                "environment": {"python": platform.python_version(), "implementation": platform.python_implementation(),
                                "platform": platform.platform(), "libc": platform.libc_ver()},
                "imports": {n: {"path": p, "sha256": h} for n, (p, h) in MODULES.items()}, "rounds": rounds,
                "scope": "offline integrity and raw adjudication replay; no native run or release authorization"}
    finally:
        for name in MODULES:
            sys.modules.pop(name, None)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", required=True)
    parser.add_argument("--baseline-source", required=True)
    parser.add_argument("--candidate-source")
    parser.add_argument("--candidate-registration")
    args = parser.parse_args()
    print(json.dumps(verify(args.bundle, args.baseline_source, args.candidate_source, args.candidate_registration),
                     ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
