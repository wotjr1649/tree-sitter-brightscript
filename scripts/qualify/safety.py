"""Explicit test-only Windows safety route of qualify/run.py; no direct process launcher.

python scripts/qualify/run.py --safety-profile capability --cc <pinned gcc> --safety-cc <approved clang> --out <new .work dir>
The stock limits stay unchanged. This route fixes executable hashes, arguments, private environment,
single-job limits and task-contained output. It does not download tools or run a full timing campaign.
"""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import sys

import run
import tscli
from corpus import read_corpus

GCC_SHA = "75e87953e9d04e8a5d81225397292e9f8ae599a0ed85f70ed175767577aaa9f6"
CLANG_SHA = "20ba1856942744291a6aaaf9f2c94f6d0cd7cac5aa9557fce96471dc7ef25d6f"
ASAN_SHA = "75178608bf2dff8ac65a336562e0606f0f90e3276c671d9820a43e8176f6129e"
FUZZER_SHA = "236fb48bdd9942cbfacb0fa6c2907efd1319fa91e668eba2f68812902c71cd46"
CAP, MS, OUTPUT = 2 * 2**30, 360000, 64 * 2**20
CHECKS = ("check_v0", "check_generated", "check_maintenance_generation", "check_maintenance", "test_tscli", "check_registry", "check_schema",
          "check_samples", "check_spellings", "check_incremental", "check_spike", "check_robustness",
          "test_maintenance", "test_gates", "test_safety", "corpus", "oracle")

def check_command(name, lab):
    if name not in CHECKS:
        raise ValueError("unknown check")
    if name == "corpus":
        tail = [run.ROOT / "scripts/tscli.py", "test"]
    elif name == "oracle":
        tail = [run.ROOT / "scripts/record_oracle.py", "--out=" + str(lab.out / "oracle")]
    elif name in ("test_gates", "test_safety"):
        tail = [run.HERE / (name + ".py")]
    else:
        tail = [run.ROOT / "scripts" / (name + ".py")]
        if name == "check_registry":
            tail.append("--complete")
        if name == "check_maintenance_generation":
            tail.append("--out=" + str(lab.out / "generation"))
    return [str(sys.executable), *map(str, tail)]

def checks(lab, names, gcc):
    lab.env["PATH"] = os.pathsep.join([str(gcc.parent), str(Path(sys.executable).parent),
        r"C:\Program Files\nodejs", r"C:\Program Files\Git\cmd",
        str(Path(os.environ["SYSTEMROOT"]) / "System32")])
    lab.env["CC"] = str(gcc)
    lab.env["PYTHONIOENCODING"] = "utf-8"
    lab.allowed_images[Path(sys.executable).resolve()] = run.sha(sys.executable)
    results = []
    for name in names:
        argv = check_command(name, lab)
        lab.python_argv = argv
        report, text = lab.supervise("check-" + name, argv)
        ok = report["termination_reason"] == "COMPLETED" and report["exit_code_raw"] == 0
        results.append({"check":name,"pass":ok,"stdout_tail":text[-1000:]})
        (lab.out / "checks.json").write_text(json.dumps(results, indent=2)+"\n", encoding="utf-8")
        print(name, "PASS" if ok else "FAIL", flush=True)
        if not ok:
            raise RuntimeError("check failed: " + name)
    return results

def replay_inputs(lab):
    rows = [(name, t["input"], "corpus") for name,t in read_corpus()[0].items()]
    for folder in ("samples", "recovery", "highlight"):
        rows += [(p.relative_to(run.ROOT).as_posix(), p.read_bytes(), folder)
                 for p in sorted((run.ROOT / "test" / folder).glob("*.brs"))]
    for k in (15,16,17):
        for tail in (b"", b"\n", b"\r\n", b"\r", b"\x00", b" 'comment", b"\nsub Main()\nend sub\n"):
            rows.append((f"run-{k}-{tail.hex()}", b"x = " + b"+f([)"*k + tail, "scanner-boundary"))
    for n,data in enumerate((b"",b"\x00",b"\xff",b"\xc3",b"\xed\xa0\x80",b"x = \"\xe2\x82",
                            "print \"한글\"\n".encode(), b"if false\ninvalid @ prose\nend if\n")):
        rows.append((f"bytes-{n}",data,"encoding-arbitrary"))
    rows.append(("long-valid-callback", b"x = 1\n"*5000,"valid-cancellation-witness"))
    records=[]
    for i,(name,data,family) in enumerate(rows):
        if len(data)>65536: raise ValueError("replay input above its fixed bound")
        p=lab.out/"inputs/replay"/f"{i:04d}.brs";p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
        records.append({"id":i,"name":name,"family":family,"path":str(p),"bytes":len(data),"sha256":run.sha(p)})
    return records

def native(lab, runtime):
    runtime=Path(runtime).resolve()
    units=run.verify_runtime(runtime,"0.27.0")
    flags=["-O1","-g","-fsanitize=address","-fno-omit-frame-pointer",
           "-fsanitize-coverage=inline-8bit-counters,pc-table,trace-cmp",
           "-I",runtime/"lib/include","-I",runtime/"lib/src","-I",run.ROOT/"src"]
    objects=[]
    for i,unit in enumerate([*units,run.ROOT/"src/parser.c",run.ROOT/"src/scanner.c"]):
        obj=lab.out/"build"/f"unit-{i:02d}.o"
        lab.compile(f"instrument-unit-{i:02d}",[*flags,"-c",unit],obj);objects.append(obj)
    target=run.HERE/"safety_target.c"
    replay=lab.out/"build/replay.exe"
    lab.compile("replay",[*flags,"-DTSQ_REPLAY",target,*objects],replay)
    obj=lab.out/"build/fuzz-target.o"
    lab.compile("fuzz-target",[*flags,"-c",target],obj)
    fuzz=lab.out/"build/fuzz.exe"
    lib=lab.cc.parent.parent/"lib/clang/23/lib/windows/libclang_rt.fuzzer-x86_64.a"
    lab.compile("fuzz-link",["-fsanitize=address",obj,*objects,lib,"-lc++"],fuzz)
    lab.env["TSQ_QUERY"]=str(run.ROOT/"queries/highlights.scm")
    lab.env["TSQ_ASAN_DLL"]=str(lab.out/"build/libclang_rt.asan_dynamic-x86_64.dll")
    inputs=replay_inputs(lab)
    protocol={"version":1,"candidate":{n:run.sha(run.ROOT/n) for n in (
        "src/parser.c","src/scanner.c","grammar.js","src/node-types.json","queries/highlights.scm")},
        "runtime_manifest":run.sha(run.HERE/"runtime-0.27.0.sha256"),
        "instrumented_units":[str(p) for p in [*units,run.ROOT/"src/parser.c",run.ROOT/"src/scanner.c",target]],
        "compile_flags":list(map(str,flags)),"input_manifest":inputs,"seeds":[6,106,206],
        "limits":{"invocations":10000,"seconds":300,"max_input_bytes":65536,"input_timeout_seconds":5,
                  "watchdog_ms":MS,"commit_bytes":CAP,"output_bytes":OUTPUT,"corpus_bytes":32*2**20},
        "executables":{"replay":run.sha(replay),"fuzz":run.sha(fuzz)},
        "raw_query_predicates":False,"claims":"memory/lifecycle and bounded coverage, no timing or universal safety"}
    (lab.out/"protocol.json").write_text(json.dumps(protocol,indent=2)+"\n",encoding="utf-8")
    results=[];triggered=0
    for row in inputs:
        report,text=lab.supervise(f"replay-{row['id']:04d}",[replay,row["path"]],ms=5000)
        ok=report["termination_reason"]=="COMPLETED" and report["exit_code_raw"]==0 and "REPLAY_COMPLETE" in text
        summary=re.search(r"TSQ_SUMMARY calls=(\d+) captures=(\d+) nodes=(\d+) cancelled=(\d+)",text)
        ok=ok and bool(summary) and int(summary[1])==1
        triggered+=int(summary[4]) if summary else 0
        results.append({"id":row["id"],"pass":ok,"summary":summary[0] if summary else None})
        (lab.out/"replay-results.json").write_text(json.dumps(results,indent=2)+"\n",encoding="utf-8")
        if not ok:raise RuntimeError("native replay failed: "+row["name"])
    if not triggered:raise RuntimeError("no replay cancellation was observed")
    print("ASAN_REPLAY_PASS",len(inputs),"cancelled",triggered,flush=True)
    rounds=[]
    for seed in (6,106,206):
        corpus=lab.out/"inputs"/f"fuzz-{seed}";corpus.mkdir()
        for row in inputs:shutil.copyfile(row["path"],corpus/f"{row['id']:04d}")
        findings=lab.out/"findings"/str(seed);findings.mkdir(parents=True)
        lab.env["TSQ_FUZZ_CORPUS"]=str(corpus)
        argv=[fuzz,str(corpus),f"-seed={seed}","-runs=10000","-max_len=65536","-timeout=5",
              "-max_total_time=300","-rss_limit_mb=2048","-workers=1","-jobs=0",
              "-artifact_prefix="+str(findings)+os.sep,"-print_final_stats=1","-reload=0"]
        report,text=lab.supervise(f"fuzz-{seed}",argv)
        done=re.findall(r"Done (\d+) runs in (\d+) second",text)
        cov=[int(v) for v in re.findall(r"cov: (\d+)",text)]
        raw_files=[{"name":p.name,"sha256":run.sha(p),"bytes":p.stat().st_size}
                   for p in sorted(corpus.iterdir()) if p.is_file()]
        ok=(report["termination_reason"]=="COMPLETED" and report["exit_code_raw"]==0 and bool(done)
            and int(done[-1][0])>len(inputs) and not list(findings.iterdir())
            and sum(p["bytes"] for p in raw_files)<=32*2**20)
        row={"seed":seed,"assessment":"BOUNDED_COMPLETE" if ok else "FAIL_OR_RESOURCE_LIMITED",
             "done":done[-1] if done else None,"coverage_initial":cov[0] if cov else None,
             "coverage_max":max(cov) if cov else None,"final_corpus":raw_files}
        rounds.append(row)
        (lab.out/"fuzz-results.json").write_text(json.dumps(rounds,indent=2)+"\n",encoding="utf-8")
        print("FUZZ",seed,row["assessment"],flush=True)
        if not ok:raise RuntimeError("fuzz stopped; preserve findings and do not start remaining seeds")
    return {"replay_cases":len(inputs),"observed_cancellations":triggered,"fuzz":rounds}

def output_path(path):
    p = Path(path).resolve()
    if not any(p.is_relative_to(run.ROOT / n) for n in (".work", "artifacts")):
        raise ValueError("output must be task-contained")
    if p.exists() and any(p.iterdir()):
        raise ValueError("output must be new or empty")
    return p

def tools_check(gcc, clang):
    for p, h in ((gcc, GCC_SHA), (clang, CLANG_SHA),
                 (clang.parent / "libclang_rt.asan_dynamic-x86_64.dll", ASAN_SHA),
                 (clang.parent.parent / "lib/clang/23/lib/windows/libclang_rt.fuzzer-x86_64.a", FUZZER_SHA)):
        if not p.is_file() or run.sha(p) != h:
            raise ValueError("unapproved test tool: " + p.name)

class SafetyLab(run.Lab):
    def __init__(self, cc, out):
        super().__init__(cc, out)
        self.allowed_images = {Path(cc).resolve(): run.sha(cc)}
        self.python_argv = None

    def supervise(self, cid, argv, cap=CAP, ms=MS, output_cap=OUTPUT):
        image = Path(argv[0]).resolve()
        if image not in self.allowed_images or run.sha(image) != self.allowed_images[image]:
            raise ValueError("image is not a verified tool or this run's build")
        if image == Path(sys.executable).resolve() and list(map(str, argv)) != self.python_argv:
            raise ValueError("check argv differs from the fixed command")
        if not (16 * 2**20 <= cap <= CAP and 10 <= ms <= MS and 0 < output_cap <= OUTPUT):
            raise ValueError("outside the safety profile")
        return super().supervise(cid, argv, cap, ms, output_cap)

    def compile(self, tag, args, output):
        if not Path(output).resolve().is_relative_to(self.out / "build"):
            raise ValueError("build output outside the owned build directory")
        h = super().compile(tag, args, output)
        if Path(output).suffix.lower() == ".exe":
            self.allowed_images[Path(output).resolve()] = h
        return h

def prepare(args):
    gcc, clang = Path(args.cc).resolve(), Path(args.safety_cc).resolve()
    tools_check(gcc, clang)
    out = output_path(args.out)
    lab = SafetyLab(gcc, out)
    lab.supervisor = out / "build/supervisor-stock.exe"
    base = ["-O2", "-Wall", "-Wextra", "-Werror", "-municode", run.HERE / "supervisor.c",
            "-lpsapi", "-Wl,--no-insert-timestamp"]
    lab.compile("supervisor-stock", base, lab.supervisor)
    stock_sha = run.sha(lab.supervisor)
    # v0.1.4 root-accounting correction; the historical S572 identity is retained in validation.md.
    if stock_sha != "c1fc5d7e0ea00ebc72d4ef6e14d915341bb473cc08aaaca7b8ce72cf01cdb847":
        raise RuntimeError("stock supervisor differs from the verified v0.1.4 image")
    stock_tests = run.self_test(lab)
    stock_tests.append(lab.supervisor_refusal("stock-refuses-safety-cap", CAP, 1000, 1024))
    lab.supervisor = out / "build/supervisor-safety.exe"
    lab.compile("supervisor-safety", ["-DTSQ_SAFETY_PROFILE", *base], lab.supervisor)
    safety_tests = run.self_test(lab)
    for name,cap,ms,output in (("memory",CAP+1,1000,1024),("watchdog",CAP,MS+1,1024),
                               ("output",CAP,1000,OUTPUT+1)):
        safety_tests.append(lab.supervisor_refusal("safety-refuses-"+name,cap,ms,output))
    lab.supervised_builds = True
    lab.cc = clang
    lab.env["PATH"] = os.pathsep.join([str(clang.parent), str(Path(os.environ["SYSTEMROOT"]) / "System32")])
    lab.env["ASAN_OPTIONS"] = "halt_on_error=1:abort_on_error=1:symbolize=0"
    lab.allowed_images[clang] = CLANG_SHA
    shutil.copyfile(clang.parent / "libclang_rt.asan_dynamic-x86_64.dll", out / "build/libclang_rt.asan_dynamic-x86_64.dll")
    return lab, {"stock_supervisor_sha256":stock_sha,"stock_selftest":stock_tests,"safety_selftest":safety_tests,
                 "safety_supervisor_sha256":run.sha(lab.supervisor),"compiler_sha256":CLANG_SHA,
                 "asan_library_sha256":ASAN_SHA,"profile":{"commit_bytes":CAP,"watchdog_ms":MS,"output_bytes":OUTPUT}}

def capability(lab):
    exe = lab.out / "build/control.exe"
    lab.compile("asan-control", ["-O1", "-g", "-fsanitize=address", "-fno-omit-frame-pointer",
                                run.HERE / "safety_control.c"], exe)
    normal, text = lab.supervise("asan-normal", [exe, "normal"], ms=15000)
    if normal["termination_reason"] != "COMPLETED" or normal["exit_code_raw"] or "CONTROL 7" not in text:
        raise RuntimeError("ASan normal control did not complete")
    bad, text = lab.supervise("asan-oob", [exe, "oob"], ms=15000)
    if (bad["termination_reason"] != "COMPLETED" or not bad["exit_code_raw"]
            or "ERROR: AddressSanitizer: heap-buffer-overflow" not in text):
        raise RuntimeError("ASan did not diagnose the real OOB control")
    fuzz = lab.out / "build/coverage-control.exe"
    # The MinGW driver lacks the combined fuzzer switch. Use its supported
    # SanitizerCoverage instrumentation and the same distribution's engine archive.
    obj = lab.out / "build/coverage-control.o"
    lab.compile("coverage-control-object", ["-O1", "-g", "-DTSQ_FUZZ_CONTROL", "-fsanitize=address",
                "-fsanitize-coverage=inline-8bit-counters,pc-table,trace-cmp", "-c",
                run.HERE / "safety_control.c"], obj)
    lib = lab.cc.parent.parent / "lib/clang/23/lib/windows/libclang_rt.fuzzer-x86_64.a"
    lab.compile("coverage-control-link", ["-fsanitize=address", obj, lib, "-lc++"], fuzz)
    seeds = lab.out / "inputs/control"; seeds.mkdir()
    (seeds / "a").write_bytes(b"a")
    report, text = lab.supervise("coverage-positive", [fuzz, str(seeds), "-seed=6", "-runs=1000",
         "-max_len=32", "-timeout=5", "-rss_limit_mb=0", "-max_total_time=10"], ms=15000)
    counts = [int(x) for x in re.findall(r"cov: (\d+)", text)]
    if report["termination_reason"] != "COMPLETED" or report["exit_code_raw"] or not counts or max(counts) <= counts[0]:
        raise RuntimeError("coverage counters did not increase")
    return {"asan_normal":"PASS","asan_real_oob":"DETECTED","coverage_counter_initial":counts[0],
            "coverage_counter_max":max(counts),"coverage":"PASS","leak_detection":"NOT_CLAIMED"}

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--safety-profile", choices=("capability", "checks", "native"), required=True)
    ap.add_argument("--cc", required=True)
    ap.add_argument("--safety-cc", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--runtime")
    ap.add_argument("--check", action="append", choices=CHECKS)
    args = ap.parse_args()
    lab, identity = prepare(args)
    try:
        if args.safety_profile == "capability":
            result = capability(lab)
        elif args.safety_profile == "checks":
            if not args.check: raise ValueError("at least one fixed check is required")
            result = checks(lab,args.check,Path(args.cc).resolve())
        else:
            if not args.runtime: raise ValueError("runtime is required")
            result = native(lab,args.runtime)
        doc = {"identity":identity,"execution_status":"COMPLETED","assessment":"PASS","result":result}
        (lab.out / "result.json").write_text(json.dumps(doc, indent=2)+"\n", encoding="utf-8")
        print(json.dumps(doc), flush=True)
        return 0
    except Exception as error:
        (lab.out / "failure.json").write_text(json.dumps({"execution_status":"STOPPED",
            "assessment":"FAIL_OR_BLOCKED","error":str(error)},indent=2)+"\n",encoding="utf-8")
        raise
    finally:
        lab.log.close()
