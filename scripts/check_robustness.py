"""V10 robustness: workloads W06, W07, W08 and W13 (docs/validation/workload-matrix.md).

Usage: python scripts/check_robustness.py [--fuzz-iterations=N] [--fuzz-seed=N] [--skip-fuzz]

- W06: deterministic generated inputs (nesting, length, repetition); valid
  inputs parse with no error (root has_error unset, hidden MISSING included)
  and invalid ones with an error; every input finishes within 10 s and 1 GiB
  peak resident memory.
- W07: invalid UTF-8 and NUL bytes parse without a crash.
- W08: every negative and recovery corpus input parses with an error and
  without a crash or hang.
- W13: pathological seeds (one or more for every `unresolved` requirement)
  parse without a crash or hang; `tree-sitter fuzz` over the corpus with
  N iterations (default 1000) of up to 10 edits and seed N (default 1,
  TREE_SITTER_SEED) reports no failure. The fuzzer signals failures only in
  its output, so its output is scanned.
Crash = a timeout, an exit status other than 0 or 1, or status 1 without the
CLI's parse-error summary line (status 1 also reports failures to run). Error
state comes from `--cst` (scripts/tscli.py); the timed run uses `--quiet`.
Stdlib only.
"""
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from corpus import ROOT, read_corpus
from tscli import ENV, EXE, cli, cst
TIME_LIMIT = 10.0
MEMORY_LIMIT = 1 << 30


def w06():
    """(name, bytes, valid) for the generated inputs; deterministic."""
    lines = lambda items: "\n".join(items)  # noqa: E731
    nest = lambda open_, body, close, depth: (  # noqa: E731
        "\n".join(open_(i) for i in range(depth)) + "\n" + body + "\n" + "\n".join(close for _ in range(depth)))
    return [
        ("array-10000", "a = [\n" + lines(f"  {i}" for i in range(10000)) + "\n]\n", True),
        ("aa-5000", "aa = {\n" + lines(f"  k{i}: {i}" for i in range(5000)) + "\n}\n", True),
        ("colon-2000", " : ".join(f"x{i} = {i}" for i in range(2000)) + "\n", True),
        ("elseif-1000", "if x = 0 then\n  y = 0\n" + lines(f"else if x = {i} then\n  y = {i}" for i in range(1, 1001))
         + "\nelse\n  y = -1\nend if\n", True),
        ("nested-if-100", nest(lambda i: f"if c{i} then", "x = 1", "end if", 100), True),
        ("nested-for-100", nest(lambda i: f"for i{i} = 1 to 2", "x = 1", "end for", 100), True),
        ("nested-while-100", nest(lambda i: f"while c{i}", "x = 1", "end while", 100), True),
        ("nested-try-100", "\n".join("try" for _ in range(100)) + "\nx = 1\n"
         + "\n".join("catch e\nend try" for _ in range(100)) + "\n", True),
        ("parens-500", "x = " + "(" * 500 + "1" + ")" * 500 + "\n", True),
        ("postfix-2000", "x = a" + "".join((".m", "(1)", "[2]")[i % 3] for i in range(2000)) + "\n", True),
        ("string-1mib", 's = "' + "x" * (1 << 20) + '"\n', True),
        ("functions-50000-lines", lines(f"function f{i}(a as Integer) as Integer\n  b = a + {i}\n  return b\nend function\n"
                                        for i in range(10000)), True),
        ("unterminated-if", "if x then\n  y = 1\n", False),
        ("unterminated-for", "for i = 1 to 2\n  y = 1\n", False),
        ("unterminated-aa", "aa = { a: 1,\n", False),
        ("unterminated-string", 'x = "open\n', False),
        ("unterminated-cc-if", "#if DEBUG\n  x = 1\n", False),
    ]


def w07_w13_seeds():
    """(name, bytes) robustness-only inputs: W07 bytes and W13 seeds per unresolved requirement."""
    return [
        ("W07 invalid UTF-8", b"x = \"\xff\xfe\xc3\"\n' \x80\x81\ny = 1\n"),
        ("W07 NUL bytes", b"x = 1\x00\ny\x00 = \"a\x00b\"\n"),
        ("BS-LEX-007 bare CR", b"x = 1\ry = 2\rprint x\r"),
        ("BS-LEX-016 non-ASCII identifier", "café = 1\nprint café\n".encode()),
        ("BS-LEX-020 designators on members", b"x = a.b$ + {k%: 1}\nlabel$:\ngoto label$\n"),
        ("BS-LEX-034 UTF-16 text", "x = 1\n".encode("utf-16-le")),
        ("BS-LIT-013 numeric forms", b"a = 5. : b = &hFF% : c = &h : d = 5.e3 : e = 5$ : f = 1.5% : g = 2.5&\n"),
        ("BS-LIT-018 multi-line string", b'x = "one\ntwo"\n'),
        ("BS-TYPE-002 other type names", b"function f(a as LongInteger, b as Interface) as Invalid\nend function\n"),
        ("BS-EXP-022 adjacent operands", b'x = "a"b"c"\n'),
        ("BS-EXP-023 breaks after operators and in groups", b"x = 1 +\n2\ny = (1\n+ 2)\nz = a[1\n]\n"),
        ("BS-EXP-024 breaks in argument lists", b"f(\n1,\n2\n)\n"),
        ("BS-EXP-025 postfix on literals", b'x = "a"(1) + 5[0] + [1, 2].count() + [1][0]\n'),
        ("BS-STMT-006 other expression statements", b'x\na + b\na.b\n(f)()\n"x".len()\na?.b.c()\nx@y.z = 1\n'),
        ("BS-STMT-014 NEXT with counters", b"for i = 1 to 2\nnext i\nfor j = 1 to 2\nfor k = 1 to 2\nnext k, j\n"),
        ("BS-STMT-021 compact loop words", b"for i = 1 to 2\nexitfor\nendfor\nforeach x in y\nexit\ncontinue\nend for\n"),
        ("BS-STMT-028 GOTO line number", b"goto 100\n"),
        ("BS-STMT-034 LET", b"let x = 1\n"),
        ("BS-FUNC-004 AS on SUB", b"sub s() as void\nend sub\n"),
        ("BS-FUNC-007 breaks after ( in parameters", b"function f(\na,\nb\n)\nend function\n"),
        ("BS-FUNC-012 nested declarations", b"sub outer()\nsub inner()\nend sub\nend sub\n"),
        ("BS-ARRAY-006 several DIM declarators", b"dim a[1], b[2]\n"),
        ("BS-ERR-006 TRY without CATCH", b"try\nx = 1\nend try\n"),
        ("BS-COND-009 compact and spaced directives", b"#if DEBUG\n#elseif X\n#endif\n# if A\n# end if\n#if not DEBUG\n#end if\n#const x = a and b\n"),
        ("BS-COND-010 directives in expressions", b"x = 1 +\n#if A\n2\n#else\n3\n#end if\nif a then\n#if B\nend if\n#end if\n"),
        ("W13 lone quote", b'"'),
        ("W13 lone hash", b"#"),
        ("W13 lone question mark", b"?"),
        ("W13 lone &h", b"&h"),
        ("W13 10000 open parentheses", b"x = " + b"(" * 10000),
        ("W13 10000 colons", b":" * 10000),
        ("W13 #if without #end if", b"#if false\nprose\n#if A\n"),
    ]


def run(path):
    """Parse one file; return (exit code, seconds, peak bytes, output)."""
    start = time.monotonic()
    proc = subprocess.Popen([str(EXE), "parse", "--quiet", str(path)], cwd=ROOT, env=ENV,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        out, _ = proc.communicate(timeout=TIME_LIMIT * 3)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.communicate()
        return None, time.monotonic() - start, 0, b""
    elapsed = time.monotonic() - start
    return proc.returncode, elapsed, peak_memory(proc), out


def peak_memory(proc):
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes

        class Counters(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD)] + [
                (n, ctypes.c_size_t) for n in ("PeakWorkingSetSize", "WorkingSetSize", "QuotaPeakPagedPoolUsage",
                                               "QuotaPagedPoolUsage", "QuotaPeakNonPagedPoolUsage",
                                               "QuotaNonPagedPoolUsage", "PagefileUsage", "PeakPagefileUsage")]
        c = Counters()
        c.cb = ctypes.sizeof(c)
        ok = ctypes.windll.psapi.GetProcessMemoryInfo(wintypes.HANDLE(int(proc._handle)), ctypes.byref(c), c.cb)
        return c.PeakWorkingSetSize if ok else -1
    return -1  # measured by wait4 in run_posix


def run_posix(path):
    start = time.monotonic()
    proc = subprocess.Popen([str(EXE), "parse", "--quiet", str(path)], cwd=ROOT, env=ENV,
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    deadline = start + TIME_LIMIT * 3
    while True:
        pid, status, usage = os.wait4(proc.pid, os.WNOHANG)
        if pid:
            proc.returncode = os.waitstatus_to_exitcode(status)
            return proc.returncode, time.monotonic() - start, usage.ru_maxrss * 1024, proc.stdout.read()
        if time.monotonic() > deadline:
            proc.kill()
            os.wait4(proc.pid, 0)
            return None, time.monotonic() - start, 0, b""
        time.sleep(0.01)


def check(name, data, want_clean, want_error, tmp, fail):
    path = tmp / "input.brs"
    path.write_bytes(data)
    code, secs, peak, out = (run if sys.platform == "win32" else run_posix)(path)
    problems = []
    if code is None:
        problems.append("hang (killed)")
    elif code not in (0, 1) or (code == 1 and b"\tParse:" not in out):
        problems.append(f"crash (exit {code})")
    if secs > TIME_LIMIT:
        problems.append(f"{secs:.1f} s")
    if peak > MEMORY_LIMIT:
        problems.append(f"{peak / 2**20:.0f} MiB")
    elif code is not None and peak < 0:
        problems.append("peak memory not measured")
    if (want_clean or want_error) and code in (0, 1):
        has_error = cst(path, timeout=TIME_LIMIT * 3)[0]
        if want_clean and has_error:
            problems.append("ERROR or MISSING in a valid input")
        if want_error and not has_error:
            problems.append("no error in an invalid input")
    print(f"  {name}: {len(data):,} bytes, {secs:.2f} s, {peak / 2**20:.0f} MiB, exit {code}"
          f"{' FAIL ' + ', '.join(problems) if problems else ''}")
    fail += [f"{name}: {p}" for p in problems]


def main():
    fail = []
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        (tmp / "warm-up.brs").write_bytes(b"x = 1\n")
        cst(tmp / "warm-up.brs", timeout=600)  # compiles the parser before any timed run
        print("W06 generated inputs")
        for name, text, valid in w06():
            check(name, text.encode("utf-8"), valid, not valid, tmp, fail)
        print("W07 and W13 seeds (robustness only)")
        for name, data in w07_w13_seeds():
            check(name, data, False, False, tmp, fail)
        print("W08 negative and recovery fixtures")
        corpus, _ = read_corpus()
        for name, t in corpus.items():
            if ":error" in t["attrs"]:
                check(name, t["input"], False, True, tmp, fail)
    if "--skip-fuzz" not in sys.argv:
        iterations = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--fuzz-iterations=")), "1000")
        seed = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--fuzz-seed=")), "1")
        print(f"W13 tree-sitter fuzz: {iterations} iterations x up to 10 edits per corpus test, seed {seed}")
        start = time.monotonic()
        code, stdout, stderr = cli("fuzz", "--iterations", iterations, "--edits", "10", timeout=3600,
                                   env={"TREE_SITTER_SEED": seed})
        r = subprocess.CompletedProcess([], code)
        out = stdout + stderr
        markers = [m for m in ("Incorrect parse", "Unexpected scope change", "failed fuzzing", "leak", "panicked")
                   if m.lower() in out.lower()]
        tests = out.count(". brightscript - corpus")
        print(f"  {tests} corpus tests fuzzed in {time.monotonic() - start:.0f} s, exit {r.returncode}, "
              f"failure markers: {markers or 'none'}")
        if r.returncode or markers or tests == 0:
            fail.append(f"fuzz: exit {r.returncode}, markers {markers}, tests {tests}")
            sys.stdout.buffer.write(out[-4000:].encode("utf-8"))
    if fail:
        print("FAIL")
        for x in fail:
            print("  -", x)
        sys.exit(1)
    print("PASS")


if __name__ == "__main__":
    main()
