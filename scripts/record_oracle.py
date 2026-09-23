"""W12 native oracle (V6): record native Tree-sitter results for the exact grammar identity.

Usage: python scripts/record_oracle.py [--out=DIR]

Parses every corpus input and every test/samples/*.brs with the pinned CLI
(`tree-sitter parse`, default and `--cst` output) and writes, under
artifacts/oracle/<commit>/ (local, Git-ignored) by default:
  inputs/<n>.brs, trees/<n>.txt, cst/<n>.txt, manifest.json, run.json.
The manifest binds the results to the identity (validation.md "Identity
binding"): grammar commit, generator version, ABI, SHA-256 of every generated
file and of the CLI binary, platform, a workload identity (SHA-256 over the
ordered input hashes) and a content identity (SHA-256 over the ordered input,
tree and CST hashes). `has_error` is the root has_error state (hidden MISSING
included). Recording the same identity twice on one platform gives
byte-identical inputs/, trees/, cst/ and manifest.json: the CLI's per-file
`Parse: <ms> ms <n> bytes/ms` timing is removed from the recorded output, and
the recording date and the SHA-256 of the parser library the CLI compiled in a
private library directory (it differs between compilations) go to run.json,
which is not identity. Refuses to record for a dirty tree. Stdlib only.
"""
import datetime
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

from corpus import ROOT, read_corpus
from tscli import EXE, LIBDIR, cst, parse

sha = lambda b: hashlib.sha256(b).hexdigest()  # noqa: E731
# The summary line the CLI prints for a tree with an error (crates/cli/src/parse.rs @ v0.27.0):
# "<path>\tParse: <ms> ms\t<n> bytes/ms[\t(<first error node>)]". Only the timing is dropped.
TIMING = re.compile(r"^INPUT\tParse: *[0-9.]+ ms\t *[0-9]+ bytes/ms", re.M)


def recorded(output, path):
    """CLI output with the input path replaced and the timing removed."""
    text = TIMING.sub("INPUT", output.replace(str(path), "INPUT"))
    if re.search(r"^INPUT\tParse:", text, re.M):
        sys.exit(f"unrecognised timing line in the output for {path}")
    return text.encode("utf-8")


def git(*args):
    r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"git {args[0]} failed: {r.stderr.strip()}")
    return r.stdout.strip()


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
        tree = recorded(parse(path), path)
        has_error, full = cst(path)
        full = recorded(full, path)
        (out / "trees" / f"{n:03d}.txt").write_bytes(tree)
        (out / "cst" / f"{n:03d}.txt").write_bytes(full)
        records.append(dict(n=n, name=name, input_sha256=sha(data), tree_sha256=sha(tree), cst_sha256=sha(full),
                            has_error=has_error, expected_error=expect_error))
    library, = [p for p in Path(LIBDIR).iterdir() if p.suffix in (".dll", ".so", ".dylib")]
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
        workload=dict(cases=len(records), sha256=sha("".join(r["input_sha256"] for r in records).encode())),
        content_sha256=sha("".join(r["input_sha256"] + r["tree_sha256"] + r["cst_sha256"] for r in records).encode()),
    )
    manifest = json.dumps(dict(identity=identity, results=records), indent=2).encode("utf-8") + b"\n"
    (out / "manifest.json").write_bytes(manifest)
    run = dict(date=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
               parser_library_sha256=sha(library.read_bytes()))
    (out / "run.json").write_bytes(json.dumps(run, indent=2).encode("utf-8") + b"\n")
    errors = sum(r["has_error"] for r in records)
    unexpected = [r["name"] for r in records if r["has_error"] != r["expected_error"]]
    print(f"recorded {len(records)} cases ({errors} with an error node) in {out}")
    print(f"workload sha256 {identity['workload']['sha256']}")
    print(f"content sha256 {identity['content_sha256']}")
    print(f"manifest sha256 {sha(manifest)}")
    if unexpected:
        sys.exit(f"error presence differs from the :error expectation: {unexpected}")


if __name__ == "__main__":
    main()
