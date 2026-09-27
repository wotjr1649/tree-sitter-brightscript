"""Prepare deterministic source/replay assets from committed blobs and pinned public history.

This preparation command may GET only the two fixed public baseline archives.
The separate verify_public.py entry point is offline. No native execution,
dependency installation, credential access, Git writes or publication occurs.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import stat
import subprocess
import urllib.request
import zipfile

from check_maintenance_012 import COMPONENTS, compare

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://github.com/wotjr1649/tree-sitter-brightscript/releases/download/v0.1.1/"
ASSETS = {"tree-sitter-brightscript-v0.1.1-source.zip":
          (509486, "94891e1f22c4d62840c69d981798ece7c395ee0652a39056d23fc9f1afbc60cd"),
          "tree-sitter-brightscript-v0.1.1-verification.zip":
          (17195587, "5df890ab9ed9ef2786ba82acd42146f25eb69fc1741f18866d1b474a44ee2486")}
K1 = "ebe8c4ce2c5bbe21a1b1e90d1c6a8b9824aca4931074015b6de20ccb35a19f2e"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, check=True, timeout=30).stdout


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def unzip(archive, prefix, out):
    with zipfile.ZipFile(archive) as z:
        rows = z.infolist()
        if len(rows) > 16000 or sum(r.file_size for r in rows) > 160 * 2**20:
            raise ValueError("archive bound")
        names = set()
        for row in rows:
            p = PurePosixPath(row.filename)
            if (row.orig_filename != row.filename or row.filename != p.as_posix() or p.is_absolute()
                    or ".." in p.parts or "\\" in row.filename
                    or ":" in row.filename or not row.filename.startswith(prefix + "/")
                    or any(x.endswith((" ", ".")) for x in p.parts) or row.flag_bits & 1
                    or not stat.S_ISREG(row.external_attr >> 16) or row.filename.casefold() in names):
                raise ValueError("unsafe/duplicate archive member")
            names.add(row.filename.casefold())
        out = out.resolve()
        out.mkdir(parents=True, exist_ok=False)
        for row in rows:
            path = out / row.filename[len(prefix) + 1:]
            if not path.resolve().is_relative_to(out):
                raise ValueError("archive escape")
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("xb") as stream:
                stream.write(z.read(row))


def deterministic_zip(path, files, prefix):
    # Stored members make the exact public bytes independent of the host's zlib.
    with zipfile.ZipFile(path, "x", compression=zipfile.ZIP_STORED) as z:
        for name, data, mode in sorted(files):
            info = zipfile.ZipInfo(prefix + "/" + name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = mode << 16
            info.compress_type = zipfile.ZIP_STORED
            z.writestr(info, data)


def prepare(out, baseline_assets=None):
    out = Path(out).resolve()
    if not out.is_relative_to(ROOT / ".work") or out.exists():
        raise ValueError("output must be a new directory under .work")
    if git("status", "--porcelain").strip():
        raise ValueError("commit the exact source before packaging")
    out.mkdir(parents=True)
    downloads = out / "downloads"
    downloads.mkdir()
    for name, (size, expected) in ASSETS.items():
        if baseline_assets is None:
            request = urllib.request.Request(BASE + name, headers={"User-Agent": "tree-sitter-brightscript-replay"})
            with urllib.request.urlopen(request, timeout=60) as response:
                data = response.read(size + 1)
        else:
            data = (Path(baseline_assets) / name).read_bytes()
        if len(data) != size or digest(data) != expected:
            raise ValueError("baseline archive identity differs: " + name)
        (downloads / name).write_bytes(data)
    q = out / "verification"
    q.mkdir()
    unzip(downloads / "tree-sitter-brightscript-v0.1.1-source.zip", "tree-sitter-brightscript-v0.1.1", q / "baseline-source")
    unzip(downloads / "tree-sitter-brightscript-v0.1.1-verification.zip", "tree-sitter-brightscript-v0.1.1-verification", q / "baseline")
    source = out / "source"
    source.mkdir()
    files, modes, packed = {}, {}, []
    for entry in git("ls-tree", "-rz", "--full-tree", "HEAD").split(b"\0"):
        if not entry:
            continue
        meta, encoded_name = entry.split(b"\t", 1)
        mode, kind, oid = meta.split()
        name = encoded_name.decode("utf-8")
        if kind != b"blob" or mode not in (b"100644", b"100755") or any(
                name.startswith(p) for p in (".work/", "_ref/", "artifacts/", "docs/prompts/", "docs/plans/", ".git/")):
            raise ValueError("non-source Git entry")
        data = git("cat-file", "blob", oid.decode())
        path = source / name
        if not path.resolve().is_relative_to(source):
            raise ValueError("source escape")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        files[name], modes[name] = digest(data), int(mode, 8)
        packed.append((name, data, int(mode, 8)))
    version = json.loads((source / "package.json").read_text(encoding="utf-8"))["version"]
    if version != "0.1.2":
        raise ValueError("this packaging contract is only for 0.1.2")
    registration = {"schema": "S07-CANDIDATE-r1", "commit": git("rev-parse", "HEAD").decode().strip(),
                    "commit_object": git("cat-file", "commit", "HEAD").decode("utf-8"),
                    "tree": git("rev-parse", "HEAD^{tree}").decode().strip(), "baseline_K1": K1,
                    "files": files, "modes": modes}
    (q / "candidate-registration.json").write_bytes(json_bytes(registration))
    proof = compare({n: (q / "baseline-source" / n).read_bytes() for n in COMPONENTS},
                    {n: (source / n).read_bytes() for n in COMPONENTS})
    (q / "candidate-product-proof.json").write_bytes(json_bytes(proof))
    for name in ("verify_public.py", "replay_compare.py", "check_maintenance_012.py"):
        (q / name).write_bytes((source / "scripts" / name).read_bytes())
    (q / "tests").mkdir()
    for name in ("test_replay_compare.py", "test_public_verifier.py", "test_maintenance_012.py"):
        (q / "tests" / name).write_bytes((source / "scripts" / name).read_bytes())
    (q / "numeric-policy.md").write_bytes((source / "docs/validation/public-replay.md").read_bytes())
    (q / "README.md").write_text(
        "# v0.1.2 공개 재판정 자료\n\n"
        "source ZIP을 별도 디렉터리에 풀고 Python 3.14에서 다음 명령을 실행한다.\n\n"
        "    python -I -B -X utf8 verify_public.py --bundle baseline --baseline-source baseline-source "
        "--candidate-source <source-root> --candidate-registration candidate-registration.json\n\n"
        "실행은 offline이다. baseline은 공개 v0.1.1 원자료와 원 source다. 후보 source 등록은 별도다. "
        "역사 측정을 새 native 측정으로 표시하지 않는다. 파일 무결성/재판정 성공은 전체 release gate의 대용이 아니다.\n"
        "원 17 gate 중 13개 run 기반 gate를 회차당 8,875개 raw로 재판정한다. 나머지 네 gate는 기록된 결과이며 "
        "이 도구로 독립 재실행하지 않는다. signed zero/subnormal은 exact; 등록된 log 파생값만 최대 2 ULP, "
        "threshold 교차는 부적격이다. 원 FAIL과 자산은 보존한다.\n",
        encoding="utf-8", newline="\n")
    qfiles = [(p.relative_to(q).as_posix(), p.read_bytes(), 0o100644) for p in q.rglob("*") if p.is_file()]
    manifest = {"schema": "S07-VERIFICATION-r1", "policy": "S07-REPLAY-2ULP-r1",
                "trusted_baseline": {"tag": "v0.1.1", "K1": K1, "archives": ASSETS},
                "files": [{"path": n, "sha256": digest(b), "bytes": len(b)}
                                                          for n, b, _ in sorted(qfiles)]}
    (q / "VERIFICATION-MANIFEST.json").write_bytes(json_bytes(manifest))
    qfiles.append(("VERIFICATION-MANIFEST.json", json_bytes(manifest), 0o100644))
    sname, qname = "tree-sitter-brightscript-v0.1.2-source", "tree-sitter-brightscript-v0.1.2-verification"
    deterministic_zip(out / (sname + ".zip"), packed, sname)
    deterministic_zip(out / "source-twin.zip", packed, sname)
    if (out / (sname + ".zip")).read_bytes() != (out / "source-twin.zip").read_bytes():
        raise ValueError("source package non-deterministic")
    deterministic_zip(out / (qname + ".zip"), qfiles, qname)
    result = {"commit": registration["commit"], "tree": registration["tree"], "source_files": len(files),
              "verification_files": len(qfiles), "assets": {n + ".zip": {"sha256": digest((out / (n + ".zip")).read_bytes()),
                "bytes": (out / (n + ".zip")).stat().st_size} for n in (sname, qname)}}
    (out / "prepared.json").write_bytes(json_bytes(result))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    parser.add_argument("--baseline-assets")
    args = parser.parse_args()
    print(json.dumps(prepare(args.out, args.baseline_assets), indent=2))
