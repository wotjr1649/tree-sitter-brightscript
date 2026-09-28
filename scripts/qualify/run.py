"""Release qualification lane runner (docs/validation/validation.md, "Release qualification lane").

    python scripts/qualify/run.py --cc <gcc.exe> --runtime <tree-sitter 0.27.0 source root> --out <new dir>
        [--support 0.25.1=<source root>] [--support 0.26.13=<source root>] [--gates G1,G2,...] [--seed N]

This file and scripts/tscli.py are the only files under scripts/ that start programs (scripts/test_tscli.py
checks it). It starts git (to read the reference grammars), the pinned CLI through tscli (generate), the C
compiler named by --cc, and programs that compiler built under --out; every probe run and every build after the
supervisor's own happens inside the Windows Job-object or POSIX process-group supervisor, self-tested first
(limits: 512 MiB reported host memory metric, 15 s, 8 MiB output, one child at a time). Two steps use the pinned
CLI through tscli outside the supervisor,
with its own time limits: regenerating the reference grammars, and RECOVERY-LOCALITY, which parses each mutant with
`parse --cst` in the candidate and the H checkout (the CLI compiles each grammar once with the --cc compiler into a
private library directory per checkout). A runtime source root is used only if every file listed in
runtime-<version>.sha256 matches.
Results: <out>/runs.jsonl (every run) and <out>/gates.json; the exit status is 0 only if every selected gate
passes.
"""
import argparse
import datetime as dt
import errno
import hashlib
import json
import os
import re
import selectors
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

if sys.platform != "win32":
    import resource
if sys.platform == "darwin":
    import ctypes

    class DarwinUsage(ctypes.Structure):
        _fields_ = [("uuid", ctypes.c_uint8 * 16),
                    *[(name, ctypes.c_uint64) for name in (
                        "user_time", "system_time", "idle_wakeups", "interrupt_wakeups", "pageins",
                        "wired_size", "resident_size", "phys_footprint", "start", "exit")]]

    _libproc = ctypes.CDLL("/usr/lib/libproc.dylib", use_errno=True)
    _libproc.proc_pid_rusage.argtypes = (ctypes.c_int, ctypes.c_int, ctypes.c_void_p)
    _libproc.proc_pid_rusage.restype = ctypes.c_int
    _libproc.proc_listpgrppids.argtypes = (ctypes.c_int, ctypes.c_void_p, ctypes.c_int)
    _libproc.proc_listpgrppids.restype = ctypes.c_int
    _libproc.proc_pidinfo.argtypes = (ctypes.c_int, ctypes.c_int, ctypes.c_uint64, ctypes.c_void_p, ctypes.c_int)
    _libproc.proc_pidinfo.restype = ctypes.c_int

    def darwin_group_pids(pgid):
        pids = (ctypes.c_int * 4096)()
        ctypes.set_errno(0)
        count = _libproc.proc_listpgrppids(pgid, pids, ctypes.sizeof(pids))
        if count < 0 or count >= len(pids) or count == 0 and ctypes.get_errno():
            raise OSError(ctypes.get_errno(), "proc_listpgrppids failed or overflowed")
        return pids[:count]

    def darwin_footprint(pid):
        usage = DarwinUsage()
        if _libproc.proc_pid_rusage(pid, 0, ctypes.byref(usage)):
            raise OSError(ctypes.get_errno(), "proc_pid_rusage failed")
        return usage.phys_footprint

    def darwin_group_footprint(pgid):
        total = 0
        for pid in darwin_group_pids(pgid):
            try:
                total += darwin_footprint(pid)
            except OSError as error:
                if error.errno != errno.ESRCH:
                    raise
        return total

    def darwin_live_group_pids(pgid, leader, leader_exited):
        live = []
        for pid in darwin_group_pids(pgid):
            if pid == leader and leader_exited:
                continue
            info = (ctypes.c_uint8 * 256)()
            ctypes.set_errno(0)
            size = _libproc.proc_pidinfo(pid, 13, 0, info, ctypes.sizeof(info))  # PROC_PIDT_SHORTBSDINFO
            if not size and ctypes.get_errno() == errno.ESRCH:
                continue
            if size < 16:
                raise OSError(ctypes.get_errno(), "proc_pidinfo status unavailable")
            status = ctypes.c_uint32.from_buffer(info, 12).value  # pbsi_status; SZOMB == 5
            if status != 5:
                live.append(pid)
        return live


def posix_live_group_pids(pgid, leader, leader_exited):
    if sys.platform == "darwin":
        return darwin_live_group_pids(pgid, leader, leader_exited)
    live = []
    for path in Path("/proc").iterdir():
        if not path.name.isdecimal():
            continue
        try:
            pid = int(path.name)
            if os.getpgid(pid) != pgid:
                continue
            fields = (path / "stat").read_text(encoding="utf-8", errors="replace").rsplit(") ", 1)[1].split()
        except (FileNotFoundError, ProcessLookupError):
            continue
        if int(fields[2]) != pgid:
            raise RuntimeError("POSIX process group changed during inspection")
        if fields[0] not in ("Z", "X") and (pid != leader or not leader_exited):
            live.append(pid)
    return live

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
        self.cc, self.out = Path(cc).resolve(), Path(out).resolve()
        for d in ("build", "raw", "inputs", "env"):
            (self.out / d).mkdir(parents=True, exist_ok=True)
        if sys.platform == "win32":
            self.env = {k: v for k, v in os.environ.items() if k.upper() in {"SYSTEMROOT", "WINDIR", "COMSPEC",
                                                                            "SYSTEMDRIVE", "PATHEXT"}}
            self.env["PATH"] = os.pathsep.join([str(self.cc.parent), str(Path(os.environ["SYSTEMROOT"]) / "System32")])
        else:
            self.env = {"PATH": os.pathsep.join(dict.fromkeys([str(self.cc.parent), "/usr/bin", "/bin"]))}
        private_names = ("HOME", "USERPROFILE", "APPDATA", "LOCALAPPDATA", "TEMP", "TMP", "XDG_CACHE_HOME",
                         "XDG_CONFIG_HOME", "XDG_STATE_HOME", "TREE_SITTER_LIBDIR", "TREE_SITTER_DIR") if sys.platform == "win32" else (
                         "HOME", "TMPDIR", "XDG_CACHE_HOME", "XDG_CONFIG_HOME", "XDG_STATE_HOME",
                         "TREE_SITTER_LIBDIR", "TREE_SITTER_DIR")
        for name in private_names:
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
        if sys.platform != "win32":
            return self.supervise_posix(cid, argv, cap, ms, output_cap)
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

    def supervise_posix(self, cid, argv, cap, ms, output_cap):
        """One task-owned child/session with pre-exec virtual-memory limit and bounded output."""
        if not (16 * 2**20 <= cap <= 1024 * 2**20 and 10 <= ms <= 15000 and 0 < output_cap <= 8 * 2**20):
            raise ValueError("invalid POSIX supervisor profile")
        requested, n = cid, 1
        while (self.out / "raw" / cid).exists():
            n += 1
            cid = f"{requested}-r{n}"
        raw = self.out / "raw" / cid
        raw.mkdir(parents=True)
        argv = list(map(str, argv))
        if not Path(argv[0]).is_absolute() or not Path(argv[0]).is_file():
            raise ValueError("POSIX supervised image must be an existing absolute path")

        def limits():
            if sys.platform == "darwin":
                return  # The hosted macOS kernel rejected RLIMIT_AS; the parent enforces a sampled footprint limit.
            try:
                _, hard = resource.getrlimit(resource.RLIMIT_AS)
                resource.setrlimit(resource.RLIMIT_AS, (cap, cap))
            except (OSError, ValueError) as error:
                current = resource.getrlimit(resource.RLIMIT_AS)
                os.write(2, f"RLIMIT_AS_FAILED {type(error).__name__} {error} current={current}\n".encode())
                os._exit(92)

        start = time.monotonic()
        start_ns = time.monotonic_ns()
        with (raw / "child.out").open("xb") as output:
            proc = subprocess.Popen(argv, env=self.env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    start_new_session=True, preexec_fn=limits)
            selector = selectors.DefaultSelector()
            selector.register(proc.stdout, selectors.EVENT_READ)
            status, usage, reason, stored, pipe_open, exited, waited = None, None, "COMPLETED", 0, True, False, False
            descendant_pipe = False
            peak_sampled, last_sample, max_sample_gap, samples_after_exit = 0, start, 0, 0
            memory_kill_requested, memory_group_exit = None, None
            group_cleared = False
            try:
                while pipe_open or not exited:
                    if time.monotonic() - start > ms / 1000 + 2:
                        raise RuntimeError(f"POSIX supervisor could not drain or observe exit for {cid}")
                    if not exited:
                        # WNOWAIT retains the group leader PID until descendants are inspected and signalled.
                        exited = os.waitid(os.P_PID, proc.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT) is not None
                    if sys.platform == "darwin":
                        now = time.monotonic()
                        max_sample_gap = max(max_sample_gap, now - last_sample)
                        last_sample = now
                        try:
                            footprint = darwin_group_footprint(proc.pid)
                            peak_sampled = max(peak_sampled, footprint)
                            if exited:
                                samples_after_exit += 1
                        except OSError as error:
                            if error.errno != errno.ESRCH:
                                raise
                            if exited:
                                raise
                            if os.waitid(os.P_PID, proc.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT) is None:
                                raise
                            exited = True
                        if peak_sampled > cap and reason == "COMPLETED":
                            reason = "MEMORY_LIMIT_REACHED"
                            memory_kill_requested = time.monotonic()
                            try:
                                os.killpg(proc.pid, signal.SIGKILL)
                            except ProcessLookupError:
                                pass
                    if time.monotonic() - start > ms / 1000 and reason == "COMPLETED":
                        reason = "WATCHDOG_TERMINATED"
                        try:
                            os.killpg(proc.pid, signal.SIGKILL)
                        except ProcessLookupError:
                            pass
                    events = selector.select(timeout=0.02)
                    for key, _ in events:
                        data = os.read(key.fileobj.fileno(), 65536)
                        if not data:
                            selector.unregister(key.fileobj)
                            pipe_open = False
                            continue
                        room = max(0, output_cap - stored)
                        output.write(data[:room])
                        stored += len(data[:room])
                        if len(data) > room and reason == "COMPLETED":
                            reason = "OUTPUT_LIMIT_REACHED"
                            try:
                                os.killpg(proc.pid, signal.SIGKILL)
                            except ProcessLookupError:
                                pass
                    if exited and pipe_open and not events and reason == "COMPLETED":
                        descendant_pipe = True
                        reason = "DESCENDANTS_TERMINATED"
                        try:
                            os.killpg(proc.pid, signal.SIGKILL)
                        except ProcessLookupError:
                            pass
                if posix_live_group_pids(proc.pid, proc.pid, exited):
                    try:
                        os.killpg(proc.pid, signal.SIGKILL)
                    except (ProcessLookupError, PermissionError):
                        if posix_live_group_pids(proc.pid, proc.pid, exited):
                            raise
                    else:
                        if reason == "COMPLETED":
                            reason = "DESCENDANTS_TERMINATED"
                    deadline = time.monotonic() + 2
                    while time.monotonic() < deadline:
                        if not posix_live_group_pids(proc.pid, proc.pid, exited):
                            break
                        time.sleep(0.01)
                    else:
                        raise RuntimeError(f"POSIX process group did not exit for {cid}")
                group_cleared = True
                if memory_kill_requested is not None:
                    memory_group_exit = time.monotonic()
                _, status, usage = os.wait4(proc.pid, 0)
                waited = True
                proc.returncode = os.waitstatus_to_exitcode(status)
            finally:
                if not group_cleared and not waited:
                    try:
                        os.killpg(proc.pid, signal.SIGKILL)
                    except (ProcessLookupError, PermissionError):
                        pass
                    try:
                        os.kill(proc.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    os.wait4(proc.pid, 0)
                selector.close()
                proc.stdout.close()
        peak = max(peak_sampled, usage.ru_maxrss if sys.platform == "darwin" else usage.ru_maxrss * 1024)
        report = {"termination_reason": reason, "exit_code_raw": proc.returncode,
                  "pid": proc.pid, "creation_monotonic_ns": start_ns,
                  "peak_working_set_bytes": peak, "peak_commit_bytes": peak,
                  "memory_metric": "group_sampled_phys_footprint_bytes" if sys.platform == "darwin" else "peak_rss_bytes",
                  "memory_limit_mode": "group_sampled_kill" if sys.platform == "darwin" else "kernel_rlimit_as",
                  "sampled_peak_footprint_bytes": peak_sampled if sys.platform == "darwin" else None,
                  "sampled_overshoot_bytes": max(0, peak_sampled - cap) if sys.platform == "darwin" else None,
                  "memory_kill_to_group_exit_ms": ((memory_group_exit - memory_kill_requested) * 1000
                                                   if memory_group_exit is not None else None),
                  "process_peak_rss_bytes": usage.ru_maxrss if sys.platform == "darwin" else usage.ru_maxrss * 1024,
                  "max_sample_gap_ms": max_sample_gap * 1000, "configured_job_memory_limit_bytes": cap,
                  "samples_after_exit": samples_after_exit if sys.platform == "darwin" else None,
                  "image_path": str(Path(argv[0]).resolve()), "exit_confirmed": waited,
                  "active_processes": 0 if not pipe_open else None,
                  "descendant_pipe_observed": descendant_pipe,
                  "elapsed_ms": (time.monotonic() - start) * 1000}
        (raw / "supervisor.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
        guard = waited and report["active_processes"] == 0 and report["configured_job_memory_limit_bytes"] == cap
        self.record(kind="supervised", command_id=cid, argv=argv, image_sha256=sha(argv[0]), report=report,
                    guard=guard)
        if not guard:
            raise RuntimeError(f"POSIX supervisor guard failed for {cid}; the lane stops")
        return report, (raw / "child.out").read_text(encoding="utf-8", errors="replace")

    def supervisor_refusal(self, cid, cap, ms, output_cap):
        """Test invalid guard configuration: it must exit before report/child creation."""
        raw = self.out / "raw" / cid
        raw.mkdir()
        argv = [str(self.out / "build/benign.exe"), "normal"]
        command = [str(self.supervisor), str(raw / "supervisor.json"), str(raw / "child.out"),
                   str(cap), str(ms), str(output_cap), argv[0], subprocess.list2cmdline(argv)]
        cp = subprocess.run(command, env=self.env, capture_output=True, timeout=5,
                            creationflags=subprocess.DETACHED_PROCESS)
        ok = cp.returncode == 64 and not list(raw.iterdir())
        self.record(kind="guard-refusal-selftest", command_id=cid, argv=command,
                    exit=cp.returncode, no_child_or_report=not list(raw.iterdir()), passed=ok)
        if not ok:
            raise RuntimeError("supervisor did not refuse the invalid profile")
        return {"id":cid,"pass":ok}


class Runner:
    """What the gates call: measurements of built probes on generated inputs."""

    def __init__(self, lab, probes, query, roots=None, runtime_build="separate"):
        self.lab, self.probes, self.query, self.roots = lab, probes, query, roots or {}
        self.runtime_build = runtime_build

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
               "runtime_build": self.runtime_build,
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
    posix = sys.platform != "win32"
    exe = lab.out / "build" / ("benign" if posix else "benign.exe")
    lab.compile("benign", ["-O2", "-Wall", "-Wextra", HERE / ("benign_posix.c" if posix else "benign.c")], exe)
    env_before = os.environ.get("S05_PRIVATE_CANARY")
    os.environ["S05_PRIVATE_CANARY"] = "must-not-reach-child"  # the child must not see the parent's variables
    results = []
    modes = ["normal", "sleep", "memory", "output", "descendant", "private-env"]
    if posix:
        modes.append("descendant-closed")
    if sys.platform == "darwin":
        modes.extend(("memory-child", "memory-child-orphan"))
    for mode in modes:
        report, text = lab.supervise(f"selftest-{mode}", [exe, mode], cap=(64 if sys.platform == "darwin" else 512 if posix else 64) * 2**20,
                                     ms=200 if mode == "sleep" else 3000, output_cap=64 * 2**10)
        ok = {"normal": report["termination_reason"] == "COMPLETED" and "NORMAL_COMPLETED" in text,
              "sleep": report["termination_reason"] == "WATCHDOG_TERMINATED",
              "memory": (report["termination_reason"] == "MEMORY_LIMIT_REACHED" and
                         report["peak_working_set_bytes"] <= 96 * 2**20 and report["max_sample_gap_ms"] <= 100)
                        if sys.platform == "darwin" else report["exit_code_raw"] == 73 and "ALLOCATION_DENIED" in text,
              "output": report["termination_reason"] == "OUTPUT_LIMIT_REACHED",
              "descendant": report["termination_reason"] == "DESCENDANTS_TERMINATED" and (
                  report["descendant_pipe_observed"] if posix else report["total_processes"] == 2),
              "descendant-closed": (report["termination_reason"] == "DESCENDANTS_TERMINATED" and
                                    not report.get("descendant_pipe_observed")),
              "memory-child": (report["termination_reason"] == "MEMORY_LIMIT_REACHED" and
                               report["peak_working_set_bytes"] <= 96 * 2**20 and
                               report.get("max_sample_gap_ms", float("inf")) <= 100),
              "memory-child-orphan": (report["termination_reason"] in ("MEMORY_LIMIT_REACHED", "DESCENDANTS_TERMINATED") and
                                      "MEMORY_CHILD_ALIVE" in text and
                                      report["samples_after_exit"] > 0 and
                                      report["peak_working_set_bytes"] <= 96 * 2**20 and
                                      report.get("max_sample_gap_ms", float("inf")) <= 100),
              "private-env": report["termination_reason"] == "COMPLETED" and "PRIVATE_ENV_COMPLETED" in text}[mode]
        if sys.platform == "darwin" and report["termination_reason"] == "MEMORY_LIMIT_REACHED":
            ok &= gates.sampled_memory_control(report)
        results.append({"mode": mode, "pass": ok, "detail": text[-120:] if not ok else "",
                        "report": report})
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
    ap.add_argument("--runtime")
    ap.add_argument("--out", required=True)
    ap.add_argument("--preflight", action="store_true")
    ap.add_argument("--characterize", action="store_true")
    ap.add_argument("--support", action="append", default=[])
    ap.add_argument("--gates", default=",".join(ALL_GATES))
    ap.add_argument("--seed", type=int, default=5707)
    args = ap.parse_args()
    if args.characterize and (args.preflight or args.support or args.gates != ",".join(ALL_GATES)):
        raise SystemExit("characterization has a fixed plan and cannot select gates, support or preflight")
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
    if sys.platform == "win32":
        lab.supervisor = lab.out / "build/supervisor.exe"
        lab.compile("supervisor", ["-O2", "-Wall", "-Wextra", "-Werror", "-municode", HERE / "supervisor.c", "-lpsapi",
                                   "-Wl,--no-insert-timestamp"], lab.supervisor)
    selftest = self_test(lab)
    if args.preflight:
        (lab.out / "preflight.json").write_text(json.dumps({"platform": sys.platform, "selftest": selftest}, indent=1),
                                                 encoding="utf-8")
        print("POSIX_PREFLIGHT_PASS" if sys.platform != "win32" else "WINDOWS_PREFLIGHT_PASS")
        return 0
    if not args.runtime:
        raise SystemExit("--runtime is required for qualification")
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

    def probe(name, grammar, runtime, runtime_root, alloc=False, scheduled=False):
        exe = lab.out / "build" / (f"probe-{name}.exe" if sys.platform == "win32" else f"probe-{name}")
        flags = ["-DMEASURE_ALLOC"] if alloc else []
        if scheduled:
            flags.append("-DTSQ_SCHEDULED")
        platform_link = ["-lpsapi", "-Wl,--no-insert-timestamp"] if sys.platform == "win32" else []
        lab.compile(f"probe-{name}", ["-O2", "-Wall", "-Wextra", *flags, "-I", Path(runtime_root) / "lib/include",
                                      HERE / "probe.c", *grammar, *runtime, *platform_link], exe)
        return exe

    rt = runtime_objects("0.27.0", args.runtime)
    cand = grammar_objects("cand", ROOT / "src")
    refs = {n: reference_grammar(lab, n) for n in ("h", "bp")}
    ref_objs = {n: grammar_objects(n, d / "src") for n, d in refs.items()}
    query = ROOT / "queries/highlights.scm"
    probes = {"cand": (probe("cand", cand, rt, args.runtime, scheduled=args.characterize), query),
              "cand-alloc": (probe("cand-alloc", cand, rt, args.runtime, alloc=True, scheduled=args.characterize), query),
              "h": (probe("h", ref_objs["h"], rt, args.runtime, scheduled=args.characterize), refs["h"] / "queries/highlights.scm"),
              "bp": (probe("bp", ref_objs["bp"], rt, args.runtime, scheduled=args.characterize), refs["bp"] / "queries/highlights.scm")}
    support_versions = []
    for spec in args.support:
        version, root = spec.split("=", 1)
        probes[f"cand-rt{version}"] = (probe(f"cand-rt{version}", cand, runtime_objects(version, root), root), query)
        support_versions.append(version)
    lane_files = ["run.py", "gates.py", "cases.py", "probe.c", "supervisor.c", "benign.c", "benign_posix.c", "recorded-inputs.json",
                  "runtime-0.27.0.sha256", "runtime-0.25.1.sha256", "runtime-0.26.13.sha256"]
    if args.characterize:
        lane_files.append("characterize.py")
    status = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True, timeout=60)
    other_files = ["scripts/tscli.py", "scripts/corpus.py", "docs/provenance/upstream-sources.md", "package.json",
                   "package-lock.json", "tree-sitter.json"]
    identity = {"cc": str(lab.cc), "cc_sha256": sha(lab.cc),
                "runner_image": {"os": os.environ.get("ImageOS"), "version": os.environ.get("ImageVersion"),
                                 "runner_arch": os.environ.get("RUNNER_ARCH")},
                "supervisor_sha256": sha(lab.supervisor) if lab.supervisor else None,
                "supervisor_kind": "windows_job" if sys.platform == "win32" else "posix_process_group",
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
    if args.characterize:
        import characterize
        baseline = characterize.BASELINE
        for rel, digest in identity["candidate"].items():
            data = subprocess.run(["git", "show", f"{baseline}:{rel}"], cwd=ROOT, capture_output=True,
                                  check=True, timeout=60).stdout
            if hashlib.sha256(data).hexdigest() != digest:
                raise RuntimeError(f"characterization requires frozen v0.1.3 product: {rel}")
        identity.update(characterization_baseline=baseline, characterization_phase=3,
                        profiles={"single5": {"measured_samples": 5, "warmup": 1},
                                  "single15": {"measured_samples": 15, "warmup": 1}})
        (lab.out / "identity.json").write_text(json.dumps(identity, indent=1), encoding="utf-8")
        r.runtime_build, r.cost_samples = "separate-scheduled-single5", 5
        ar = Runner(lab, dict(probes), query, roots=r.roots, runtime_build="separate-scheduled-single15")
        ar.cost_samples = 15
        characterize.run({"single5": r, "single15": ar}, identity, lab.out, args.seed)
        return 0
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
    if "--safety-profile" in sys.argv:
        import safety
        sys.exit(safety.main())
    sys.exit(main())
