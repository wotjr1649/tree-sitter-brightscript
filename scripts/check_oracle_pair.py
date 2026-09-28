"""Require two W12 recordings on one host to have identical stable bytes."""
import hashlib
import json
import sys
from pathlib import Path


def stable_files(root):
    if Path(root).is_symlink():
        raise ValueError("linked oracle root")
    root = Path(root).resolve()
    files = {}
    for name in ("inputs", "trees", "cst"):
        folder = root / name
        if not folder.is_dir() or folder.is_symlink():
            raise ValueError(f"missing or linked oracle folder: {name}")
        for path in folder.iterdir():
            if not path.is_file() or path.is_symlink():
                raise ValueError(f"unexpected oracle member: {path.name}")
            if path.stat().st_size > 8 * 2**20:
                raise ValueError(f"oversized oracle member: {path.name}")
            files[f"{name}/{path.name}"] = path.read_bytes()
    manifest = root / "manifest.json"
    if not manifest.is_file() or manifest.is_symlink() or manifest.stat().st_size > 2**20:
        raise ValueError("missing or oversized oracle manifest")
    files["manifest.json"] = manifest.read_bytes()
    record = json.loads(files["manifest.json"])
    expected = {"manifest.json"}
    for n in range(len(record["results"])):
        expected.update((f"inputs/{n:03d}.brs", f"trees/{n:03d}.txt", f"cst/{n:03d}.txt"))
    if set(files) != expected:
        raise ValueError("oracle file count disagrees with manifest")
    for item in record["results"]:
        n = item["n"]
        for folder, key, suffix in (("inputs", "input_sha256", "brs"),
                                    ("trees", "tree_sha256", "txt"),
                                    ("cst", "cst_sha256", "txt")):
            rel = f"{folder}/{n:03d}.{suffix}"
            if hashlib.sha256(files[rel]).hexdigest() != item[key]:
                raise ValueError(f"oracle hash mismatch: {rel}")
    content = "".join(item["input_sha256"] + item["tree_sha256"] + item["cst_sha256"]
                      for item in record["results"]).encode()
    if hashlib.sha256(content).hexdigest() != record["identity"]["content_sha256"]:
        raise ValueError("oracle content digest mismatch")
    return files, record


def compare(first, second):
    a, record = stable_files(first)
    b, _ = stable_files(second)
    if a != b:
        names = sorted(set(a) ^ set(b) | {name for name in a.keys() & b.keys() if a[name] != b[name]})
        raise ValueError(f"oracle repeat differs: {names[:5]}")
    return len(record["results"]), record["identity"]["content_sha256"]


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: check_oracle_pair.py FIRST SECOND")
    count, digest = compare(*sys.argv[1:])
    print(f"W12_REPEAT_PASS cases={count} content_sha256={digest}")
