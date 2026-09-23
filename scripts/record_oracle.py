"""W12 native oracle (V6): record native Tree-sitter results for the exact grammar identity.

Usage: python scripts/record_oracle.py [--out=DIR]

Parses every corpus input and every test/samples/*.brs with the pinned CLI
(`tree-sitter parse`, default and `--cst` output) and writes, under
artifacts/oracle/<commit>/ (local, Git-ignored) by default:
  inputs/<n>.brs, trees/<n>.txt, cst/<n>.txt, manifest.json.
The manifest binds the results to the identity (validation.md "Identity
binding"): grammar commit, clean-tree state, generator version, ABI, SHA-256
of every generated file and of the CLI binary, date, and a workload identity
(SHA-256 over the ordered input hashes). Refuses to record for a dirty tree.
Stdlib only.
"""
import datetime
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

from corpus import ROOT, read_corpus

EXE = ROOT / "node_modules/tree-sitter-cli" / ("tree-sitter.exe" if sys.platform == "win32" else "tree-sitter")
sha = lambda b: hashlib.sha256(b).hexdigest()  # noqa: E731


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True).stdout.strip()


def parse(path, *mode):
    r = subprocess.run([str(EXE), "parse", *mode, str(path)], cwd=ROOT, capture_output=True, timeout=120)
    text = r.stdout.decode("utf-8").replace("\r\n", "\n").replace(str(path), "INPUT")
    return text.encode("utf-8"), r.returncode


def main():
    if git("status", "--porcelain"):
        sys.exit("refusing to record: the working tree is not clean")
    commit = git("rev-parse", "HEAD")
    out = Path(next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--out=")), ROOT / "artifacts/oracle" / commit[:12]))
    for sub in ("inputs", "trees", "cst"):
        (out / sub).mkdir(parents=True, exist_ok=True)
    cases = [(name, t["input"], ":error" in t["attrs"]) for name, t in read_corpus()[0].items()]
    cases += [(p.relative_to(ROOT).as_posix(), p.read_bytes(), False) for p in sorted((ROOT / "test/samples").glob("*.brs"))]
    records = []
    for n, (name, data, expect_error) in enumerate(cases):
        path = out / "inputs" / f"{n:03d}.brs"
        path.write_bytes(data)
        tree, code = parse(path)
        cst, _ = parse(path, "--cst")
        (out / "trees" / f"{n:03d}.txt").write_bytes(tree)
        (out / "cst" / f"{n:03d}.txt").write_bytes(cst)
        records.append(dict(n=n, name=name, input_sha256=sha(data), tree_sha256=sha(tree), cst_sha256=sha(cst),
                            has_error=code != 0, expected_error=expect_error))
    parser_c = (ROOT / "src/parser.c").read_text(encoding="utf-8")
    identity = dict(
        grammar_commit=commit,
        generator=subprocess.run([str(EXE), "--version"], capture_output=True, text=True).stdout.strip(),
        abi=int(re.search(r"#define LANGUAGE_VERSION (\d+)", parser_c).group(1)),
        generated_files={p.relative_to(ROOT).as_posix(): sha(p.read_bytes())
                         for p in sorted((ROOT / "src").rglob("*")) if p.is_file()},
        cli_binary_sha256=sha(EXE.read_bytes()),
        runtime="tree-sitter CLI runtime (same release as the generator)",
        platform=sys.platform,
        date=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        workload=dict(cases=len(records), sha256=sha("".join(r["input_sha256"] for r in records).encode())),
    )
    manifest = json.dumps(dict(identity=identity, results=records), indent=2).encode("utf-8") + b"\n"
    (out / "manifest.json").write_bytes(manifest)
    errors = sum(r["has_error"] for r in records)
    unexpected = [r["name"] for r in records if r["has_error"] != r["expected_error"]]
    print(f"recorded {len(records)} cases ({errors} with an error node) in {out}")
    print(f"workload sha256 {identity['workload']['sha256']}")
    print(f"manifest sha256 {sha(manifest)}")
    if unexpected:
        sys.exit(f"error presence differs from the :error expectation: {unexpected}")


if __name__ == "__main__":
    main()
