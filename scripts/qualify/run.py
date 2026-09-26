"""Release qualification lane runner (docs/validation/validation.md, "Release qualification lane"). Windows.

    python scripts/qualify/run.py --cc <gcc.exe> --runtime <tree-sitter 0.27.0 source root> --out <new dir>
        [--support 0.25.1=<source root>] [--support 0.26.13=<source root>] [--gates G1,G2,...] [--seed N]

This file and scripts/tscli.py are the only files under scripts/ that start programs (scripts/test_tscli.py
checks it). It starts git (to read the reference grammars), the pinned CLI through tscli (generate), the C
compiler named by --cc, and programs that compiler built under --out; every probe run and every build after the
supervisor's own happens inside the Job-object supervisor that is built and self-tested first (limits: 512 MiB
commit, 15 s, 8 MiB output, one child at a time). Two steps use the pinned CLI through tscli outside the supervisor,
with its own time limits: regenerating the reference grammars, and RECOVERY-LOCALITY, which parses each mutant with
`parse --cst` in the candidate and the H checkout (the CLI compiles each grammar once with the --cc compiler into a
private library directory per checkout). A runtime source root is used only if every file listed in
runtime-<version>.sha256 matches.
Results: <out>/runs.jsonl (every run) and <out>/gates.json; the exit status is 0 only if every selected gate
passes.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import cases  # noqa: E402
import gates  # noqa: E402
import tscli  # noqa: E402

CAP, WATCHDOG_MS, OUTPUT_CAP = 512 * 2**20, 15000, 8 * 2**20
REFERENCES = {"h": ("47d40474ca6e2f5ed900baf5075e90545e16747d",
                    "2711f7cc0d22a15ba32e6327e73e529984b4578f064bb51d3b6d5e403bd7cf8d"),
              "bp": ("8e2ad7c", "3f3eafd1f8b5f7c07357998a352b0303ea9adbcef611c8b097c787faebef9443")}
ALL_GATES = ["B5-01-MEMORY", "B5-02-LIFECYCLE", "A5-01-COST", "CANCEL", "CANCEL-OVERSHOOT", "MAX-CALLBACK-GAP",
             "LARGE-INPUT", "QUERY-MALFORMED", "VALID-PARSE", "SEM-PUBLIC", "INCREMENTAL-REPAIR", "RESUME-RESET",
             "SUPPORT", "REGRESSION-SWEEP", "ABS-MEMORY", "RECOVERY-LOCALITY"]


def sha(path):
    with Path(path).open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


class Lab:
    def __init__(self, cc, out):
        self.cc, self.out = Path(cc), Path(out)
        for d in ("build", "raw", "inputs", "env"):
            (self.out / d).mkdir(parents=True, exist_ok=True)
        self.env = {k: v for k, v in os.environ.items() if k.upper() in {"SYSTEMROOT", "WINDIR", "COMSPEC", "SYSTEMDRIVE",
                                                                        "PATHEXT"}}
        self.env["PATH"] = os.pathsep.join([str(self.cc.parent), str(Path(os.environ["SYSTEMROOT"]) / "System32")])
        for name in ("HOME", "USERPROFILE", "APPDATA", "LOCALAPPDATA", "TEMP", "TMP", "XDG_CACHE_HOME", "XDG_CONFIG_HOME",
                     "XDG_STATE_HOME", "TREE_SITTER_LIBDIR", "TREE_SITTER_DIR"):
            p = self.out / "env" / "tsq-private" / name.lower()
            p.mkdir(parents=True, exist_ok=True)
            self.env[name] = str(p)
        self.supervisor, self.supervised_builds = None, False
        self.log = (self.out / "commands.jsonl").open("a", encoding="utf-8", newline="\n")
        self.runs = []

    def record(self, **fields):
        self.log.write(json.dumps({"utc": now(), **fields}, ensure_ascii=False) + "\n")
        self.log.flush()

    def compile(self, tag, args, output):
        """Run the C compiler; only its own output file counts. Before the supervisor has passed its self-test
        (the supervisor and the self-test child) the compiler runs directly with a timeout; afterwards inside the
        supervisor. gcc's children can still be counted by the job right after gcc exits (DESCENDANTS_TERMINATED
        with exit 0); such a build counts only if a second run also exits 0 and writes identical bytes."""
        argv = [str(self.cc), *map(str, args), "-o", str(output)]
        if not self.supervised_builds:
            r = subprocess.run(argv, env=self.env, capture_output=True, text=True, timeout=600)
            self.record(kind="compile", tag=tag, argv=argv, exit=r.returncode, stderr=r.stderr[-2000:],
                        output_sha256=sha(output) if r.returncode == 0 and Path(output).exists() else None)
            if r.returncode:
                raise RuntimeError(f"compile {tag} failed: {r.stderr[-2000:]}")
            return sha(output)
        report, text = self.supervise(f"compile-{tag}", argv)
        if report["termination_reason"] == "COMPLETED" and report["exit_code_raw"] == 0:
            return sha(output)
        if not (report["termination_reason"] == "DESCENDANTS_TERMINATED" and report["exit_code_raw"] == 0):
            raise RuntimeError(f"compile {tag} failed: {report['termination_reason']} {text[-2000:]}")
        first = sha(output)
        Path(output).unlink()
        again, text = self.supervise(f"compile-{tag}-confirm", argv)
        if not (again["termination_reason"] in ("COMPLETED", "DESCENDANTS_TERMINATED") and again["exit_code_raw"] == 0
                and sha(output) == first):
            raise RuntimeError(f"compile {tag} not confirmed: {again['termination_reason']} {text[-2000:]}")
        self.record(kind="build-confirmed-after-descendant-race", tag=tag, output_sha256=first)
        return first

    def supervise(self, cid, argv, cap=CAP, ms=WATCHDOG_MS, output_cap=OUTPUT_CAP):
        requested, n = cid, 1
        while (self.out / "raw" / cid).exists():
            n += 1
            cid = f"{requested}-r{n}"
        raw = self.out / "raw" / cid
        raw.mkdir(parents=True)
        argv = list(map(str, argv))
        command = [str(self.supervisor), str(raw / "supervisor.json"), str(raw / "child.out"), str(cap), str(ms),
                   str(output_cap), argv[0], subprocess.list2cmdline(argv)]
        cp = subprocess.run(command, env=self.env, capture_output=True, timeout=ms / 1000 + 30,
                            creationflags=subprocess.DETACHED_PROCESS)
        report = json.loads((raw / "supervisor.json").read_text(encoding="utf-8"))
        guard = (cp.returncode == 0 and report["win32_error"] == 0 and report["assigned_before_resume"] and
                 report["resumed"] and report["exit_confirmed"] and report["active_processes"] == 0 and
                 Path(report["image_path"]).resolve() == Path(argv[0]).resolve() and
                 report["configured_job_memory_limit_bytes"] == cap)
        self.record(kind="supervised", command_id=cid, argv=argv, image_sha256=sha(argv[0]), report=report, guard=guard)
        if not guard:
            raise RuntimeError(f"supervisor guard failed for {cid}; the lane stops")
        return report, (raw / "child.out").read_text(encoding="utf-8", errors="replace")


class Runner:
    """What the gates call: measurements of built probes on generated inputs."""

    def __init__(self, lab, probes, query, roots=None):
        self.lab, self.probes, self.query, self.roots = lab, probes, query, roots or {}

    def input(self, case):
        path = self.lab.out / "inputs" / f"{case}.brs"
        if not path.exists():
            if case.startswith("W03-"):
                data = (ROOT / "test/samples" / (case[4:] + ".brs")).read_bytes()
            else:
                data = cases.generate(case)
            path.write_bytes(data)
        return path

    def write_input(self, rel, data):
        path = self.lab.out / "inputs" / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists() or path.read_bytes() != data:
            path.write_bytes(data)
        return path

    def write_list(self, rel, paths):
        return self.write_input(rel, ("\n".join(str(p) for p in paths) + "\n").encode())

    @staticmethod
    def json_lines(text):
        out = []
        for line in text.splitlines():
            if line.startswith("{"):
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        return out

    def run(self, build, op, case, budget, tag=""):
        exe, query = self.probes[build]
        report, text = self.lab.supervise(f"{build}-{case}-{op}-{budget}-{tag}",
                                          [exe, "RUN", op, self.input(case), query, budget])
        events = {e["event"]: e for e in self.json_lines(text) if "event" in e}
        final = next((e for e in self.json_lines(text) if e.get("final")), None)
        rec = {"build": build, "op": op, "case": case, "budget": budget, "tag": tag, "report": report,
               "completed": report["termination_reason"] == "COMPLETED" and report["exit_code_raw"] == 0,
               "events": events, "final": final}
        self.lab.runs.append(rec)
        with (self.lab.out / "runs.jsonl").open("a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return rec

    def probe(self, build, args, tag):
        exe, _ = self.probes[build]
        report, text = self.lab.supervise(f"{build}-{tag}", [exe, *args])
        if not (report["termination_reason"] == "COMPLETED" and report["exit_code_raw"] == 0):
            raise RuntimeError(f"{build} {tag}: {report['termination_reason']} {report['exit_code_raw']}")
        return text

    def error_rows(self, build, path):
        """Rows covered by ERROR or MISSING nodes in the pinned CLI's --cst tree of `path` for the checkout of
        `build` ("cand" or a reference), each with its own parser-library directory (the CLI caches by name)."""
        libdir = self.lab.out / "env" / f"libdir-{build}"
        libdir.mkdir(parents=True, exist_ok=True)
        code, out, err = tscli.cli("parse", "--cst", str(path), cwd=self.roots[build], timeout=120,
                                   env={"TREE_SITTER_LIBDIR": str(libdir), "CC": str(self.lab.cc)})
        if code not in (0, 1) or not tscli.CST_LINE.search(out):
            raise RuntimeError(f"{build}: parse --cst {path} printed no tree (exit {code}): {err[-300:]}")
        rows = set()
        for a, _, c, d, _, kind in tscli.cst_nodes(out):
            if kind == "ERROR" or kind.startswith("MISSING"):
                rows.update(range(a, c + (1 if d > 0 else 0)) if c > a else {a})
        return rows

    def probe_final(self, build, args, tag):
        return next((e for e in self.json_lines(self.probe(build, args, tag)) if e.get("final")), None)


def verify_runtime(root, version):
    manifest = [line.split("  ", 1) for line in (HERE / f"runtime-{version}.sha256").read_text().splitlines()
                if line and not line.startswith("#")]
    bad = [name for digest, name in manifest if not (Path(root) / name).is_file() or sha(Path(root) / name) != digest]
    if bad:
        raise RuntimeError(f"runtime {version} at {root}: {len(bad)} files differ from the manifest, e.g. {bad[:3]}")
    lib = (Path(root) / "lib/src/lib.c").read_text(encoding="utf-8")
    return [Path(root) / "lib/src" / u for u in re.findall(r'#include "\./([a-z_]+\.c)"', lib)]


def self_test(lab):
    """Six benign children prove the memory cap, watchdog, output cap, descendant kill and the private environment."""
    exe = lab.out / "build/benign.exe"
    lab.compile("benign", ["-O2", "-Wall", "-Wextra", HERE / "benign.c"], exe)
    env_before = os.environ.get("S05_PRIVATE_CANARY")
    os.environ["S05_PRIVATE_CANARY"] = "must-not-reach-child"  # the child must not see the parent's variables
    results = []
    for mode in ("normal", "sleep", "memory", "output", "descendant", "private-env"):
        report, text = lab.supervise(f"selftest-{mode}", [exe, mode], cap=64 * 2**20,
                                     ms=200 if mode == "sleep" else 3000, output_cap=64 * 2**10)
        ok = {"normal": report["termination_reason"] == "COMPLETED" and "NORMAL_COMPLETED" in text,
              "sleep": report["termination_reason"] == "WATCHDOG_TERMINATED",
              "memory": report["exit_code_raw"] == 73 and "ALLOCATION_DENIED" in text,
              "output": report["termination_reason"] == "OUTPUT_LIMIT_REACHED",
              "descendant": report["termination_reason"] == "DESCENDANTS_TERMINATED" and report["total_processes"] == 2,
              "private-env": report["termination_reason"] == "COMPLETED" and "PRIVATE_ENV_COMPLETED" in text}[mode]
        results.append({"mode": mode, "pass": ok})
    if env_before is None:
        os.environ.pop("S05_PRIVATE_CANARY")
    else:
        os.environ["S05_PRIVATE_CANARY"] = env_before
    if not all(r["pass"] for r in results):
        raise RuntimeError(f"supervisor self-test failed: {results}")
    return results


def reference_grammar(lab, name):
    rev, expected = REFERENCES[name]
    d = lab.out / "build" / f"ref-{name}"
    (d / "src").mkdir(parents=True, exist_ok=True)
    (d / "queries").mkdir(exist_ok=True)
    for rel in ("grammar.js", "tree-sitter.json", "queries/highlights.scm"):
        data = subprocess.run(["git", "show", f"{rev}:{rel}"], cwd=ROOT, capture_output=True, check=True, timeout=60).stdout
        (d / rel).write_bytes(data)
    code, _, err = tscli.cli("generate", "--abi", "15", cwd=d, timeout=900)
    if code or sha(d / "src/parser.c") != expected:
        raise RuntimeError(f"reference {name} ({rev}) did not regenerate its recorded parser: {err[-500:]}")
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cc", required=True)
    ap.add_argument("--runtime", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--support", action="append", default=[])
    ap.add_argument("--gates", default=",".join(ALL_GATES))
    ap.add_argument("--seed", type=int, default=5707)
    args = ap.parse_args()
    selected = [g for g in args.gates.split(",") if g]
    unknown = sorted(set(selected) - set(ALL_GATES))
    if unknown:
        raise SystemExit(f"unknown gates: {unknown}")
    if Path(args.out).exists() and any(Path(args.out).iterdir()):
        raise SystemExit("--out must be a new or empty directory")
    lab = Lab(args.cc, args.out)
    mismatches = cases.check()
    if mismatches:
        raise SystemExit(f"generated inputs differ from the recorded ones: {mismatches}")
    lab.supervisor = lab.out / "build/supervisor.exe"
    lab.compile("supervisor", ["-O2", "-Wall", "-Wextra", "-Werror", "-municode", HERE / "supervisor.c", "-lpsapi",
                               "-Wl,--no-insert-timestamp"],
                lab.supervisor)
    selftest = self_test(lab)
    lab.supervised_builds = True

    def runtime_objects(version, root):
        units = verify_runtime(root, version)
        objs = []
        for u in units:
            o = lab.out / "build" / f"rt-{version}" / (u.stem + ".o")
            o.parent.mkdir(parents=True, exist_ok=True)
            lab.compile(f"rt-{version}-{u.stem}", ["-O2", "-I", Path(root) / "lib/include", "-I", Path(root) / "lib/src",
                                                   "-c", u], o)
            objs.append(o)
        return objs

    def grammar_objects(tag, src):
        objs = []
        for unit in ("parser", "scanner"):
            if (src / f"{unit}.c").exists():
                o = lab.out / "build" / f"{tag}-{unit}.o"
                lab.compile(f"{tag}-{unit}", ["-O2", "-I", src, "-c", src / f"{unit}.c"], o)
                objs.append(o)
        return objs

    def probe(name, grammar, runtime, runtime_root, alloc=False):
        exe = lab.out / "build" / f"probe-{name}.exe"
        flags = ["-DMEASURE_ALLOC"] if alloc else []
        lab.compile(f"probe-{name}", ["-O2", "-Wall", "-Wextra", *flags, "-I", Path(runtime_root) / "lib/include",
                                      HERE / "probe.c", *grammar, *runtime, "-lpsapi", "-Wl,--no-insert-timestamp"], exe)
        return exe

    rt = runtime_objects("0.27.0", args.runtime)
    cand = grammar_objects("cand", ROOT / "src")
    refs = {n: reference_grammar(lab, n) for n in ("h", "bp")}
    ref_objs = {n: grammar_objects(n, d / "src") for n, d in refs.items()}
    query = ROOT / "queries/highlights.scm"
    probes = {"cand": (probe("cand", cand, rt, args.runtime), query),
              "cand-alloc": (probe("cand-alloc", cand, rt, args.runtime, alloc=True), query),
              "h": (probe("h", ref_objs["h"], rt, args.runtime), refs["h"] / "queries/highlights.scm"),
              "bp": (probe("bp", ref_objs["bp"], rt, args.runtime), refs["bp"] / "queries/highlights.scm")}
    support_versions = []
    for spec in args.support:
        version, root = spec.split("=", 1)
        probes[f"cand-rt{version}"] = (probe(f"cand-rt{version}", cand, runtime_objects(version, root), root), query)
        support_versions.append(version)
    lane_files = ["run.py", "gates.py", "cases.py", "probe.c", "supervisor.c", "benign.c", "recorded-inputs.json",
                  "runtime-0.27.0.sha256", "runtime-0.25.1.sha256", "runtime-0.26.13.sha256"]
    status = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True, timeout=60)
    other_files = ["scripts/tscli.py", "scripts/corpus.py", "docs/provenance/upstream-sources.md", "package.json",
                   "package-lock.json", "tree-sitter.json"]
    identity = {"cc": str(lab.cc), "cc_sha256": sha(lab.cc), "supervisor_sha256": sha(lab.supervisor),
                "lane_sources": {**{f: sha(HERE / f) for f in lane_files}, **{f: sha(ROOT / f) for f in other_files}},
                "git_clean": status.returncode == 0 and not status.stdout.strip(),
                "selftest": selftest, "candidate": {f: sha(ROOT / f) for f in (
                    "grammar.js", "src/parser.c", "src/scanner.c", "src/grammar.json", "src/node-types.json",
                    "src/tree_sitter/alloc.h", "src/tree_sitter/array.h", "src/tree_sitter/parser.h",
                    "queries/highlights.scm")},
                "probes": {n: sha(p) for n, (p, _) in probes.items()},
                "git_head": subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True,
                                           timeout=60).stdout.strip(),
                "runtime": "0.27.0", "support": support_versions, "seed": args.seed, "gates": selected}
    (lab.out / "identity.json").write_text(json.dumps(identity, indent=1), encoding="utf-8")
    r = Runner(lab, probes, query, roots={"cand": ROOT, "h": refs["h"]})
    results = []
    plan = {"B5-01-MEMORY": lambda: gates.b5_01_memory(r), "B5-02-LIFECYCLE": lambda: gates.b5_02_lifecycle(r),
            "A5-01-COST": lambda: gates.a5_01_cost(r, args.seed), "CANCEL": lambda: gates.cancel(r),
            "CANCEL-OVERSHOOT": lambda: gates.overshoot(r), "MAX-CALLBACK-GAP": lambda: gates.gaps_and_cleanup(r),
            "LARGE-INPUT": lambda: gates.large_input(r), "QUERY-MALFORMED": lambda: gates.query_malformed(r),
            "VALID-PARSE": lambda: gates.valid_parse(r, args.seed), "SEM-PUBLIC": lambda: gates.sem_public(r, args.seed),
            "INCREMENTAL-REPAIR": lambda: gates.incremental_repair(r), "RESUME-RESET": lambda: gates.resume_and_two(r),
            "SUPPORT": lambda: gates.support(r, support_versions), "REGRESSION-SWEEP": lambda: gates.sweep(r),
            "ABS-MEMORY": lambda: gates.abs_memory(lab.runs), "RECOVERY-LOCALITY": lambda: gates.recovery_locality(r)}
    for g in selected:
        out = plan[g]()
        for res in (out if isinstance(out, list) else [out]):
            results.append(res)
            print(f"{res['gate']}: {res['status']}", flush=True)
            (lab.out / "gates.json").write_text(json.dumps({"identity": identity, "results": results}, indent=1),
                                                encoding="utf-8")
    ok = all(x["status"] == "PASS" for x in results)
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
