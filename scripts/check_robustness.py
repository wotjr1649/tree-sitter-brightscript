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
- Recovery scaling guards (validation.md "Recovery scaling guards"): each
  witness of RECOVERY_GUARDS is parsed at two sizes. The local exponent of the
  CLI parse times (minimum of three `--time` runs each) must not exceed the
  row's bound, the larger parse must stay within the row's time, and the peak
  memory of the CLI process may grow from the smaller to the larger size by at
  most the row's bound (a growth, so that each OS's base memory cancels out).
  The exponent is printed so that a fix, or a worse regression, is visible.
- Query scaling guards (validation.md "Query scaling guards"): each witness
  of QUERY_GUARDS is queried at two sizes with the full highlight query
  (`query -c --quiet --time`: every capture with its predicates, parsing
  excluded; minimum of three runs). The local exponent must not exceed the
  row's bound and the larger run must stay within the row's time.
  A guard run that times out or prints no time fails its guard.
- Recovery goldens (validation.md "Recovery goldens"): every test/recovery/*.brs
  parses to the node lines of its .cst golden, the recovery tree of the pinned
  runtime (scanner unit cases, inputs ending without a line break, and lines
  after an error); in the LOCALITY cases every declaration stays outside every
  ERROR node.
Crash = a timeout, an exit status other than 0 or 1, or status 1 without the
CLI's parse-error summary line (status 1 also reports failures to run). Error
state is the root line of `--cst` output, read by scripts/tscli.py `has_error`
without the rest (S04-H5); the timed run uses `--quiet`.
Stdlib only.
"""
import math
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from corpus import ROOT, read_corpus
from tscli import CST_LINE, cli, cst, cst_nodes, has_error, popen
TIME_LIMIT = 10.0
MEMORY_LIMIT = 1 << 30
# (name, prefix, repeated unit, small k, large k, max exponent, max ms of the large parse, max MiB of memory
# growth). Fixed in Session 05-1 (R-A-01: time and memory; exponent and PRINT items: memory) or by the Session 05-7
# recovery scanner (B5-01, B5-02 and the retired KL-002 families: the rest of a malformed line is one token); every
# row must stay so.
RECOVERY_GUARDS = [
    ("KL-002 prefix +/- (B-01, fixed)", b"x = ", b"+*", 250, 1000, 1.5, 50, 8),
    ("KL-002 nested single-line IF (fixed)", b"", b"if a\n*2", 250, 1000, 1.5, 50, 8),
    ("KL-002 exponent (fixed)", b"x = ", b"2^*", 500, 2000, 1.5, 50, 8),
    ("KL-002 PRINT across lines (fixed)", b"print ", b",+\n", 125, 500, 1.5, 50, 8),
    ("R-A-01 unclosed calls (fixed)", b"x = ", b"f(*", 500, 2000, 1.5, 300, 24),
    ("B4-01/B5-02 PRINT unclosed calls (fixed)", b"print ", b"f([)", 1000, 16000, 1.5, 50, 8),
    ("B5-02 PRINT separators (fixed)", b"print ", b",+*", 1000, 16000, 1.5, 50, 8),
    ("B5-02 minus and unclosed calls (fixed)", b"x = ", b"-f(-)", 1000, 16000, 1.5, 50, 8),
    ("B5-01 prefix and unclosed calls (fixed)", b"x = ", b"+f([)", 250, 1000, 1.5, 50, 8),
    ("B5-01 minus statements (fixed)", b"", b"-f(-)", 250, 1000, 1.5, 50, 8),
    ("B5-01 associative arrays (fixed)", b"x = ", b"{a:@*}<", 250, 1000, 1.5, 50, 8),
    ("B5-01 prefix, no final line break (fixed)", b"x = ", b"+f([)", 1000, 16000, 1.5, 50, 8, b""),
    ("B5-02 PRINT calls, no final line break (fixed)", b"print ", b"f([)", 1000, 16000, 1.5, 50, 8, b""),
    ("KL-002 NOT, no final line break (fixed)", b"x = ", b"(not)", 1000, 16000, 1.5, 50, 8, b""),
    ("KL-002 prefix operators across lines (fixed)", b"x = -\n", b"-\n", 1000, 4000, 1.5, 50, 8),
]
# (name, prefix, repeated unit, small k, large k, max exponent, max ms of the larger run). The highlight query on
# left-deep chains (S07-M03): the member and attribute patterns match the operator and the name as siblings, so no
# query state waits in every ancestor; with the parent form a member chain of 16,000 took 2.1 s. Method calls and
# PRINT items are flat since Session 05-7 (tree-schema.md "Re-freeze of 0.1.0"), and so is the ERROR node of an
# unclosed group (QUERY-MALFORMED: error-only tokens instead of nested rules).
QUERY_GUARDS = [
    ("member chain (S07-M03)", b"x = a", b".b", 2000, 16000, 1.5, 500),
    ("member and attribute chain (S07-M03)", b"x = a", b".b@c", 1000, 8000, 1.5, 500),
    ("method chain (S07-M03)", b"x = a", b".b(1)", 2000, 16000, 1.5, 500),
    ("statement method chain (S07-M03)", b"a", b".b(1)", 2000, 16000, 1.5, 500),
    ("mixed chain (S07-M03)", b"x = a", b".b(1)[2]", 1000, 8000, 1.5, 500),
    ("optional chain (S07-M03)", b"x = a", b"?.b?(1)?[2]", 1000, 8000, 1.5, 500),
    ("PRINT items (A5-01)", b"print ", b"a;", 2000, 16000, 1.5, 500),
    ("malformed minus, parenthesis, bracket", b"x = ", b"-(-[", 1000, 16000, 1.5, 500),
    ("malformed parenthesis and minus", b"x = ", b"(-", 1000, 16000, 1.5, 500),
    ("malformed parentheses", b"x = ", b"(", 1000, 16000, 1.5, 500),
    ("malformed brackets", b"x = ", b"[", 1000, 16000, 1.5, 500),
    ("unclosed TRY blocks", b"", b"try\n", 1000, 16000, 1.5, 500),
]
QUERY = ROOT / "queries/highlights.scm"
RECOVERY = ROOT / "test/recovery"
# Recovery cases whose later declarations must survive outside every ERROR node (lines after an error, ADR-0008).
LOCALITY = ["closer-after-stray", "colon-closer", "directive-header", "header-comma", "two-errors-gap"]


def witness(unit, k, prefix=b"x = ", end=b"\n"):
    """`prefix` followed by `unit` k times and `end` (a line end unless stated)."""
    return prefix + unit * k + end


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
        ("binary-chain-100000", "x = " + "+".join(["1"] * 100000) + "\n", True),
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
        ("BS-ARRAY-009 comma-first array", b"a = [\n1\n, 2\n]\n"),
        ("BS-AA-006 comma-first and a break after a colon", b"a = {\nx: 1\n, y: 2\n}\nb = {\nx:\n1\n}\n"),
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
        ("W13 directive-like region lines at line end", b"#if false\n#elsei\n#endi\n#if-then-else notes\n#else:\nx = 1\n#end if\ny = 2\n"),
        ("KL-002 B-01 witness k=1000", witness(b"+*", 1000)),
        ("KL-002 nested single-line IF witness k=1000", witness(b"if a\n*2", 1000, b"")),
        ("KL-002 prefix operators across lines k=1000", witness(b"-\n", 1000, b"x = -\n")),
        ("KL-002 exponent witness k=2000", witness(b"2^*", 2000)),
        ("KL-002 PRINT across lines k=500", witness(b",+\n", 500, b"print ")),
        ("R-A-01 unclosed-call witness k=2000", witness(b"f(*", 2000)),
        ("B4-01 PRINT unclosed-call witness k=4000", witness(b"f([)", 4000, b"print ")),
        ("B4-02 PRINT separator witness k=4000", witness(b",+*", 4000, b"print ")),
    ]


def parse_ms(path):
    """CLI parse time of one file in ms (`--time`), excluding process start and grammar loading."""
    code, out, err = cli("parse", "--quiet", "--time", path, timeout=TIME_LIMIT * 3)
    m = re.search(r"\tParse:\s*([0-9.]+) ms", out)
    if code not in (0, 1) or not m:
        raise RuntimeError(f"parse --time {path} printed no time (exit {code}): {err.strip()[-300:]}")
    return float(m.group(1))


def scaling_verdict(small_bytes, small_ms, large_bytes, large_ms, growth_mib, max_exponent, max_ms, max_growth):
    """(local exponent, problems) of one recovery scaling guard."""
    exponent = math.log(max(large_ms, 0.001) / max(small_ms, 0.001)) / math.log(large_bytes / small_bytes)
    problems = []
    if exponent > max_exponent:
        problems.append(f"exponent {exponent:.2f} > {max_exponent}")
    if large_ms > max_ms:
        problems.append(f"{large_ms:.0f} ms > {max_ms} ms")
    if growth_mib > max_growth:
        problems.append(f"memory grew {growth_mib:.0f} MiB > {max_growth} MiB")
    return exponent, problems


def recovery_guards(tmp, fail):
    for name, prefix, unit, small, large, max_exponent, max_ms, max_growth, *end in RECOVERY_GUARDS:
        sizes, problems = [], []
        try:
            for k in (small, large):
                path = tmp / f"guard-{k}.brs"
                path.write_bytes(witness(unit, k, prefix, *end))
                ms = min(parse_ms(path) for _ in range(3))
                code, _, peak, _ = (run if sys.platform == "win32" else run_posix)(path)
                if code is None or peak < 0:
                    problems.append(f"k={k}: hang or memory not measured")
                sizes.append((path.stat().st_size, ms, peak / 2**20))
        except (RuntimeError, subprocess.TimeoutExpired) as e:
            print(f"  {name}: FAIL {e}")
            fail.append(f"{name} guard: {e}")
            continue
        (sb, sm, speak), (lb, lm, lpeak) = sizes
        exponent, more = scaling_verdict(sb, sm, lb, lm, lpeak - speak, max_exponent, max_ms, max_growth)
        problems += more
        print(f"  {name}: k={small} {sb:,} bytes {sm:.1f} ms {speak:.0f} MiB; k={large} {lb:,} bytes {lm:.1f} ms "
              f"{lpeak:.0f} MiB; exponent {exponent:.2f} (limit {max_exponent})"
              f"{' FAIL ' + ', '.join(problems) if problems else ''}")
        fail += [f"{name} guard: {p}" for p in problems]


def query_ms(path, query=QUERY):
    """CLI time in ms of the full highlight query over one file: every capture with its predicates, parsing excluded."""
    code, out, err = cli("query", "-c", "--quiet", "--time", query, path, timeout=TIME_LIMIT * 3)
    m = re.search("^([0-9.]+)(ns|\u00b5s|ms|s)$", out, re.M)
    if code != 0 or not m or "in-progress captures" in err:
        raise RuntimeError(f"query --time {path} failed (exit {code}): {err.strip()[-300:]}")
    return float(m.group(1)) * {"ns": 1e-6, "\u00b5s": 1e-3, "ms": 1.0, "s": 1000.0}[m.group(2)]


def query_guards(tmp, fail, query=QUERY):
    for name, prefix, unit, small, large, max_exponent, max_ms in QUERY_GUARDS:
        sizes = []
        try:
            for k in (small, large):
                path = tmp / f"query-guard-{k}.brs"
                path.write_bytes(witness(unit, k, prefix))
                sizes.append((path.stat().st_size, min(query_ms(path, query) for _ in range(3))))
        except (RuntimeError, subprocess.TimeoutExpired) as e:
            print(f"  {name}: FAIL {e}")
            fail.append(f"{name} query guard: {e}")
            continue
        (sb, sm), (lb, lm) = sizes
        exponent, problems = scaling_verdict(sb, sm, lb, lm, 0, max_exponent, max_ms, 0)
        print(f"  {name}: k={small} {sb:,} bytes {sm:.2f} ms; k={large} {lb:,} bytes {lm:.2f} ms; exponent {exponent:.2f} "
              f"(limit {max_exponent}){' FAIL ' + ', '.join(problems) if problems else ''}")
        fail += [f"{name} query guard: {p}" for p in problems]


def recovery_goldens(fail):
    """Each test/recovery/*.brs parses to the node lines of its .cst golden (the pinned runtime's recovery tree), and
    in the LOCALITY cases every sub or function declaration lies outside every ERROR node."""
    for src in sorted(RECOVERY.glob("*.brs")):
        _, out = cst(src, timeout=TIME_LIMIT * 3)
        got = [line for line in out.splitlines() if CST_LINE.match(line)]
        want = src.with_suffix(".cst").read_text(encoding="utf-8").splitlines()
        problems = []
        if got != want:
            first = next((i for i, (a, b) in enumerate(zip(got, want)) if a != b), min(len(got), len(want)))
            problems.append(f"differs from its golden at node line {first + 1}")
        if src.stem in LOCALITY:
            nodes = cst_nodes(out)
            errors = [n[:4] for n in nodes if n[5] == "ERROR"]
            decls = [n[:4] for n in nodes if n[5] == "function_declaration"]
            inside = [d for d in decls for e in errors if e[:2] <= d[:2] and d[2:] <= e[2:]]
            if len(decls) < 2 or inside:
                problems.append("a declaration is missing or inside an ERROR node")
        print(f"  {src.stem}: {len(got)} nodes{' FAIL ' + ', '.join(problems) if problems else ''}")
        fail += [f"recovery case {src.stem}: {p}" for p in problems]


def run(path):
    """Parse one file; return (exit code, seconds, peak bytes, output)."""
    start = time.monotonic()
    proc = popen("parse", "--quiet", path, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
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
    proc = popen("parse", "--quiet", path, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
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
        error = has_error(path, timeout=TIME_LIMIT * 3)
        if want_clean and error:
            problems.append("ERROR or MISSING in a valid input")
        if want_error and not error:
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
        print("Recovery scaling guards (minimum of 3 CLI parse times; peak memory of each parse, growth checked)")
        recovery_guards(tmp, fail)
        print("Query scaling guards (minimum of 3 CLI query times, captures with predicates)")
        query_guards(tmp, fail)
        print("Recovery goldens and lines after an error (test/recovery, ADR-0008)")
        recovery_goldens(fail)
    if "--skip-fuzz" not in sys.argv:
        iterations = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--fuzz-iterations=")), "1000")
        seed = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--fuzz-seed=")), "1")
        print(f"W13 tree-sitter fuzz: {iterations} iterations x up to 10 edits per corpus test, seed {seed}")
        start = time.monotonic()
        code, stdout, stderr = cli("fuzz", "--iterations", iterations, "--edits", "10", timeout=3600,
                                   env={"TREE_SITTER_SEED": seed})
        out = stdout + stderr
        markers = [m for m in ("Incorrect parse", "Unexpected scope change", "failed fuzzing", "leak", "panicked")
                   if m.lower() in out.lower()]
        tests = out.count(". brightscript - corpus")
        print(f"  {tests} corpus tests fuzzed in {time.monotonic() - start:.0f} s, exit {code}, "
              f"failure markers: {markers or 'none'}")
        if code or markers or tests == 0:
            fail.append(f"fuzz: exit {code}, markers {markers}, tests {tests}")
            sys.stdout.buffer.write(out[-4000:].encode("utf-8"))
    if fail:
        print("FAIL")
        for x in fail:
            print("  -", x)
        sys.exit(1)
    print("PASS")


if __name__ == "__main__":
    main()
