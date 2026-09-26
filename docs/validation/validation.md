# Validation contract

Defines validation levels (V0–V10; distinct from the source levels L1–L5 in
`docs/provenance/source-policy.md`), the claims each supports, gates, and how
failures are handled. The V0 checklist below is automated by
`scripts/check_v0.py` (items 1–5) and `scripts/check_generated.py` (item 6).

## Validation levels

| Level | Check | Supports the claim | Does not support |
|---|---|---|---|
| V0 | Static integrity: files, metadata, provenance, license, no generated-artifact drift | The repository is internally consistent | Any language claim |
| V1 | `tree-sitter generate` succeeds with the pinned generator | The grammar generates | Correct trees |
| V2 | `tree-sitter test` corpus passes | Fixtures produce their expected trees | Complete syntax coverage |
| V3 | Requirement-derived valid, invalid and recovery fixtures pass | The grammar meets the listed `BS-*` requirements | Behaviour on a Roku device |
| V4 | Queries compile and match intended nodes | The shipped queries work on this grammar | Editor quality |
| V5 | Incremental re-parse equals fresh parse for defined edits | Incremental parsing is consistent | That either tree is correct |
| V6 | Native Tree-sitter runtime results recorded for the exact generated grammar | Reference trees for this identity | Language correctness |
| V7 | Comparison with community parsers (e.g. BrighterScript) | Where they differ | Which one is right |
| V8 | Official Roku device/compiler behaviour | What that device and OS build did | Other devices or OS builds |
| V9 | Same grammar identity through `go-treesitter` matches V6 | The Go runtime path agrees for this identity | Native or language correctness |
| V10 | Robustness: pathological input, fuzzing, time and memory limits | No crash, hang or runaway use on tested input | Correct trees |

Claims must name their level. In particular: native parity does not prove Roku
correctness; agreement with BrighterScript does not prove Roku correctness;
passing corpus tests does not prove complete coverage; incremental equality
does not prove either tree is right.

## Gates

| Level | Every relevant change | v0.x release | v1.0 release |
|---|---|---|---|
| V0 | required | required | required |
| V1 | on grammar change | required | required |
| V2 | on grammar change | required | required |
| V3 | requirements touched | all implemented requirements | every requirement with Level 1 evidence is `covered`, disclosed `provisional`, or a disclosed `KL-NNN`; `unresolved` variants are listed in the release summary |
| V4 | on node-shape change | `highlights.scm` | `highlights.scm`, `tags.scm` |
| V5 | on boundary or ambiguity changes | representative edit set | extended edit set |
| V6 | when the change's blast radius requires | required | required |
| V7 | optional | optional | recommended |
| V8 | — | per Level 2 policy | per Level 2 policy |
| V9 | — | only for integration claims | only for integration claims |
| V10 | — | pathological inputs and a bounded fuzz run (workload W13) | fuzzing |

Hosted CI (`.github/workflows/ci.yml`, Windows and Ubuntu) runs on every push
V0, generation drift (V1), the self-test of the verified CLI path
(`scripts/test_tscli.py`), the registry, schema and corpus checks (V2, V3), V4,
the W03 and W05 checks, V5 (W10) and V10 (W06–W08, W13 with fuzzing, and the
query scaling guards); the commands are in
[workload-matrix.md](workload-matrix.md) "Automation". It never
fetches Roku documentation, so the registry's research-inventory and ambiguity
reconciliations, which read the local `_ref/`, run only locally.

V9 evidence is produced in `go-treesitter`, not here
([ADR-0006](../design/decisions/ADR-0006-downstream-integration-boundary.md)).

The v1.0 column is the single definition of 1.0 readiness; other documents
link here.

A **session gate** is met when V0 and every check the Gates table requires for
the session's changes are `PASS`, or `NOT_RUN`/`BLOCKED` with a recorded
reason; a `FAIL` of any of those checks means the gate is not met. A level the
table does not require for the session's changes (for example V7, or V9
without an integration claim) may still be run; its `FAIL` is recorded and
disclosed, does not by itself fail the session gate, and supports no claim of
that level.

## Release candidate (0.x)

A 0.x release candidate is declared only when the v0.x column above holds and
every row below is `PASS`. Workload sets are defined in
[workload-matrix.md](workload-matrix.md).

| Area | Condition |
|---|---|
| Requirements | Every `documented`, `provisional` and `tolerated` requirement has its rule and all of its listed fixtures pass (Coverage `covered`); every `invalid` requirement's negative fixtures pass; a `documented` requirement that is not covered is a disclosed `KL-NNN`; `unresolved` and `out-of-scope` rows are reported as they stand; no coverage claim exceeds the registry. |
| Generation | The generator is pinned by the ADR-0002 adoption procedure; generated files are committed; regeneration reproduces every generated file byte for byte. |
| Corpus | W01 and W02 pass. |
| Valid conformance | No positive fixture and no W03 sample contains `ERROR` or `MISSING`, except a fixture that cites its `KL-NNN`. |
| Negative and recovery | W08 passes. |
| Schema | The planned public schema is reconciled with `src/node-types.json`, the catalogue is filled, and every public node and field is reviewed; no unintended public node remains. |
| Queries | `queries/highlights.scm` compiles and W11 passes. |
| Incremental | W10 passes (and the spike's E1–E6 when it passed). |
| Native oracle | W12 is recorded for the candidate identity. |
| Robustness | W06, W07 and W13 show no crash, hang or runaway memory. |
| Release qualification | Every gate of the release qualification lane passes for the candidate identity. |
| Level 1 refresh | A new dated snapshot of the ten Level 1 pages is taken before the candidate and stored beside `roku-docs-2026-09-23` (source-policy refresh rules); for every page whose content-region SHA-256 changed, each citing requirement is reviewed and the outcome recorded in `upstream-sources.md`. |
| Provenance | Generator identity, Level 1 snapshot identity and SHA-256 of every generated file are recorded. |
| Hosted CI | The workflow `.github/workflows/ci.yml` passes on Windows and Ubuntu for the candidate commit, pushed to the session branch; a local run does not substitute. |
| Downstream | V9 is not required; it is run only when the work in `go-treesitter` is authorized, and then must pass before a pin change is proposed there. |
| Review | An independent adversarial review is complete; every material finding is fixed or disclosed as a `KL-NNN` or `provisional` row, and the affected gates were rerun. |

Evidence package, written to `docs/reports/<version>-release-candidate.md` and
reproducible from the committed identity: requirement coverage summary and
status counts; generated-file identity; generator identity; schema
reconciliation (planned vs `node-types.json`); results of W01–W13 with the
commands used; known limitations; `provisional` and `tolerated` requirements;
downstream results if run; review findings and their disposition; the verdict.

## V0 checklist

1. No `_ref/`, `docs/prompts/`, `docs/plans/`, `artifacts/` or `.work/` content
   is staged or tracked.
2. `git check-ignore` confirms local-only paths are ignored and generated
   sources (`src/parser.c`, `src/grammar.json`, `src/node-types.json`,
   `src/tree_sitter/*`) and `package-lock.json` are not.
3. Relative Markdown links in tracked documents resolve.
4. License metadata is MIT everywhere it appears.
5. Tracked text files contain no CR bytes and end with a newline, except
   files under paths marked `-text` in `.gitattributes` (byte fixtures).
   Generator-owned files (item 6) are exempt from the final-newline rule: the
   generator writes `src/grammar.json` and `src/node-types.json` without one,
   and item 6 checks them byte for byte.
6. Once a grammar exists: regeneration with the pinned generator reproduces
   every generated file byte for byte, and no `src/scanner.c` exists without
   an accepted ADR.

## Result vocabulary

- `PASS`, `FAIL`, `NOT_RUN` (with reason), `BLOCKED` (with the missing input).
- Requirement statuses are defined in
  [language-conformance.md](../specs/language-conformance.md).
- Words such as "complete", "full support", "production ready", "compatible
  with Roku OS x", "verified on Roku" or "go-treesitter compatible" are used
  only when the corresponding gate evidence exists.

## Identity binding

Every recorded result names: grammar commit, generator version, ABI,
SHA-256 of the generated files, runtime version (V5, V6, V9), Level 1 snapshot
ID (V3), and date. A result for one identity is never reused for another.

Every check script runs the CLI only through `scripts/tscli.py` (so the check
does not depend on the order of CI steps) and starts no other program but git,
and every `run` command of a CI step, in every workflow file, is `npm ci`, a
check script or git, with no shell metacharacters except the fixed clean-tree
check `test -z "$(git status --porcelain)"`, and `package.json` has no npm
lifecycle script. `scripts/test_tscli.py` checks all of this structurally, in
the forms it recognises: a guard against accidental regressions, not a
sandbox (the scripts are trusted, below). Forms it does not recognise include
`from os import …` and aliases of `os`, `subprocess` reached through another
module or with `**` keywords, `sys.modules`, `ctypes`, `_winapi`,
`multiprocessing`, `pty`, `webbrowser`, `eval` and `exec`, git aliases,
modules outside `scripts/`, YAML keys escaped other than `\x72un` and `\u0072un`, a custom
step `shell:`, local actions, `binding.gyp` and `.npmrc` settings (Session 05-1
delta re-audit C4-01, C4-02).
One file under `scripts/` is exempt: `scripts/qualify/run.py`, the release
qualification runner ("Release qualification lane" below), which is not a
check script, is run by no workflow and reaches the CLI only through
`tscli.py`; it starts git, the C compiler it is given and the programs that
compiler built. `scripts/test_tscli.py` checks that it is the only exemption.
Once per process `tscli.py` copies the installed binary into a private
directory, compares the copy's SHA-256 with its record in
[upstream-sources.md](../provenance/upstream-sources.md) and its version with
the pin, and from then on runs only that copy: a binary that differs is never
run, a binary replaced or retargeted after the check is not run by that
process, and no DLL beside the installed binary is loaded. The self-test
pins the copy's location, the hash before the first run and the version
refusal; these properties otherwise rest on review of `tscli.py`, because it
does not detect every change to it (for example a private directory that is a
link, a copy rewritten after the check, `os.spawn*`, or the environment passed
to the CLI; C4-03). Out of scope:
another process of the same user writing into the private directory during
the run. The working tree's record and scripts are trusted, and the programs
the CLI starts itself (node for `generate`, the C compiler for the first
build) are not identity-bound, nor are environment settings the CLI honours
(`TREE_SITTER_JS_RUNTIME`, `TREE_SITTER_ABI_VERSION`; the check scripts pass
`--abi 15`); V1 drift detects a divergent `generate`. `python scripts/tscli.py test` is the verified form of
`tree-sitter test`. The `generate` and `test` scripts in `package.json` call
the npm-installed binary directly and are conveniences, not evidence.

The Tree-sitter CLI caches a compiled parser by grammar name alone, so a
parser compiled from another checkout can be loaded silently. Every check
script therefore runs the CLI with a private parser-library directory
(`TREE_SITTER_LIBDIR`, `scripts/tscli.py`) and an empty private configuration
directory (`TREE_SITTER_DIR`), so that a user's `parser-directories` cannot
select another grammar for `.brs` files; `python scripts/tscli.py` does the
same for a manual run used as evidence. "No error" means
the root has-error state is unset, read from `--cst` output: the CLI's exit
status and default output omit hidden `MISSING` nodes, and exit status 1 also
reports failures to run, so a check accepts a run only if a tree was printed.
Where only that state is needed, `has_error` in `scripts/tscli.py` reads the
root line and stops the CLI, because the rest of the `--cst` output grows with
tree depth squared (S04-H5; the full output is still read where every node is
compared).

## Failures and known limitations

- No retry-until-green. A failing check is investigated; the fix or the
  failure is recorded.
- Failing tests are not deleted, weakened, skipped or reclassified to get a
  pass.
- A known defect becomes a named known limitation with an ID (`KL-NNN`), the
  affected `BS-*` requirement, the observed behaviour and the fixture that
  demonstrates it. Tree-sitter's `:skip` attribute is allowed only on a fixture
  that cites its `KL-NNN`. A robustness-only limitation, which no `BS-*`
  requirement bounds, names the constructs involved instead and is
  demonstrated by a W13 seed and its recovery scaling guard.

| ID | State | Requirement | Behaviour | Demonstrating fixture |
|---|---|---|---|---|
| KL-001 | retired (unused): the ADR-0004 spike passed with design V1 on 2026-09-23 | BS-COND-007 | A literal-`false` conditional branch whose text is not BrightScript (the documented block-comment idiom) produces `ERROR` nodes | `BS-COND-007: block comment with prose` and the spike fixtures S3, S5–S8, S10–S12, asserted with `:error` |
| KL-002 | retired 2026-09-26: the Session 05-7 error-recovery scanner ([ADR-0008](../design/decisions/ADR-0008-error-recovery-scanner.md)) makes every measured family linear; accepted for 0.1.0 by the owner on 2026-09-24 as a class of behaviour until then | none is violated (robustness only); the constructs involved are right-recursive nestings the grammar accepts: prefix operators (BS-EXP-012, 018; their nesting BS-EXP-027, 028 is provisional), the right-associative `^` (BS-EXP-011), single-line IFs nested in a single-line branch (BS-STMT-009, provisional) and the PRINT item list (BS-STMT-024–026, 040; 026 provisional, 040 tolerated) | Error recovery time grew with the square of the number of repeated malformed pieces that kept such a nesting pending in one statement or its continuation (the measured families and their history: [0.1.0-performance.md](../reports/0.1.0-performance.md#known-limitation-kl-002)). With the scanner a long malformed rest of a line is one token. Through the pinned CLI all 18 known families (prefix operators, also in closed groups, call arguments, after `return`, across lines and `:`; `^` before `*`, `)`, `,`, `-*`; nested single-line IFs and the IF expression across lines; directives in expressions, after `print` and in `f(`; PRINT continued by `,+` and `;-` lines), each with and without a final line break, stay linear from k = 1,000 to 16,000, and so do the lane's regression-sweep families built from the KL-002 units; the figures are in [0.1.0-integrated-qualification.md](../reports/0.1.0-integrated-qualification.md). Nestings that were never measured are not claimed | W13 seeds `KL-002 B-01 witness k=1000`, `KL-002 nested single-line IF witness k=1000`, `KL-002 prefix operators across lines k=1000`, `KL-002 exponent witness k=2000`, `KL-002 PRINT across lines k=500`, kept as regression seeds, and the KL-002 rows of the recovery scaling guards, now scaling regression tests |
| KL-003 | retired 2026-09-24: the `_pow_left` change of Session 05-1 (grammar-design §5) removed its quadratic memory; its quadratic time is part of KL-002, and the owner's exception to the bounded-memory condition is withdrawn | — | Error recovery on a run of `^` each followed by a token that cannot start an operand needed quadratic memory at end of input (1.1 GiB at 24 KB) that the progress callback could not interrupt | — |

KL-002 and the V10 bound. Until its retirement an input of the KL-002 class
large enough to exceed W06's per-input bound (10 s, 1 GiB) was a `FAIL` of
that bound, accepted for 0.1.0 as KL-002. Since Session 05-7 its witnesses
are ordinary W13 seeds under that bound, and its guard rows are scaling
regression tests with the bounds of the other fixed rows.

Recovery scaling guards. `scripts/check_robustness.py` runs, with W13 locally
and in hosted CI, one guard per row of its `RECOVERY_GUARDS` table: the
witness (a prefix followed by the unit k times) at two sizes, the minimum of
three CLI parse times for each, and the peak memory of the CLI process for
each. A guard fails if the local exponent of the two times, the larger time
or the growth of peak memory from the smaller to the larger size exceeds the
row's bound (a growth, so that each OS's base memory cancels out). On Windows
the reading is the CLI process's own peak working set. On Linux it is the
child's `ru_maxrss`, which keeps the pre-`exec` high-water mark of the forked
Python parent, so every reading has that floor (hosted Ubuntu: 46 MiB) and a
growth below it is invisible there; the Windows job sees it:

| Row | Witness, sizes | Exponent | Larger parse | Memory growth | Kind |
|---|---|---|---|---|---|
| KL-002 prefix | `x = ` + `+*`, k = 250 and 1,000 | ≤ 1.5 | ≤ 50 ms | ≤ 8 MiB | regression test of the recovery scanner (before it: exponent 1.92, 505 ms) |
| KL-002 nested IF | `if a⏎*2`, k = 250 and 1,000 | ≤ 1.5 | ≤ 50 ms | ≤ 8 MiB | the same (before it: 1.97, 681 ms) |
| KL-002 exponent | `x = ` + `2^*`, k = 500 and 2,000 | ≤ 1.5 | ≤ 50 ms | ≤ 8 MiB | the same (before it: 2.00, 2.1 s), and a regression test of the `_pow_left` memory fix (before that: 69–84 MiB growth) |
| KL-002 PRINT across lines | `print ` + `,+⏎`, k = 125 and 500 | ≤ 1.5 | ≤ 50 ms | ≤ 8 MiB | the same (before it: 1.99, 972 ms) |
| R-A-01 | `x = ` + `f(*`, k = 500 and 2,000 | ≤ 1.5 | ≤ 300 ms | ≤ 24 MiB | regression test of the Session 05-1 fix (before it: exponent 1.7–2.1, 3 s, 1.24 GiB) |
| B4-01/B5-02 PRINT unclosed calls | `print ` + `f([)`, k = 1,000 and 16,000 | ≤ 1.5 | ≤ 50 ms | ≤ 8 MiB | regression test of the `_print_items` memory fix (before it: 386 MiB at 16 KB through the CLI) and of the Session 05-7 recovery scanner (before it: the CLI overflowed its stack at k = 16,000, B5-02) |
| B5-02 PRINT separators | `print ` + `,+*`, k = 1,000 and 16,000 | ≤ 1.5 | ≤ 50 ms | ≤ 8 MiB | regression test of the recovery scanner (before it: stack overflow at k = 16,000) |
| B5-02 minus and unclosed calls | `x = ` + `-f(-)`, k = 1,000 and 16,000 | ≤ 1.5 | ≤ 50 ms | ≤ 8 MiB | the same outside PRINT (before it: stack overflow at k = 16,000) |
| B5-01 prefix and unclosed calls | `x = ` + `+f([)`, k = 250 and 1,000 | ≤ 1.5 | ≤ 50 ms | ≤ 8 MiB | regression test of the recovery scanner (before it: exponent 2.00, 1.8 s, 778 MiB growth) |
| B5-01 minus statements | `-f(-)` with no prefix, k = 250 and 1,000 | ≤ 1.5 | ≤ 50 ms | ≤ 8 MiB | the same (before it: 1.95, 1.8 s, 773 MiB) |
| B5-01 associative arrays | `x = ` + `{a:@*}<`, k = 250 and 1,000 | ≤ 1.5 | ≤ 50 ms | ≤ 8 MiB | the same (before it: 1.92, 912 ms, 315 MiB; 5.2 GiB at k = 4,000) |
| B5-01 prefix, no final line break | `x = ` + `+f([)`, k = 1,000 and 16,000, no line break after the last unit | ≤ 1.5 | ≤ 50 ms | ≤ 8 MiB | regression test of the end-of-input line end (before it, on `cc664de`: 1.75; 47 ms) |
| B5-02 PRINT calls, no final line break | `print ` + `f([)`, k = 1,000 and 16,000, the same | ≤ 1.5 | ≤ 50 ms | ≤ 8 MiB | the same (before it: 1.58; 23 ms; on `47d4047` the CLI overflows its stack) |
| KL-002 NOT, no final line break | `x = ` + `(not)`, k = 1,000 and 16,000, the same | ≤ 1.5 | ≤ 50 ms | ≤ 8 MiB | the same (before it: 1.72; 40 ms) |
| B5-01 prefix before a final comment | `x = ` + `+f([)`, k = 1,000 and 16,000, then ` ' c` without a line break | ≤ 1.5 | ≤ 50 ms | ≤ 8 MiB | regression test of the end-of-input rest after a long run that stops at a comment (on `b501847`: 1.75; 60 ms) |
| B5-01 prefix before a final NEXT | the same, then ` next` | ≤ 1.5 | ≤ 50 ms | ≤ 8 MiB | the same at a block keyword (on `b501847`: 1.72; 61 ms) |
| B5-01 prefix before END IF and a long final comment | the same, then ` end if ' ` and 300 characters | ≤ 1.5 | ≤ 50 ms | ≤ 8 MiB | regression test of the empty end-of-input line end after a block keyword far from the end (on `e093ac8`, which looked 256 characters ahead: 1.73; 65 ms) |
| KL-002 prefix operators across lines | `x = -⏎` + `-⏎`, k = 1,000 and 4,000 | ≤ 1.5 | ≤ 50 ms | ≤ 8 MiB | regression test of runs over consecutive malformed lines (on `47d4047`: 2.13; 11.9 s) |
| block keywords on one malformed line | `if a then b = ) else ` repeated, k = 1,000 and 8,000 | ≤ 1.5 | ≤ 100 ms | ≤ 8 MiB | regression test of runs that stop at block keywords without re-reading the line (on `86eac11`, which called `get_column`: 1.70; 5.4 s) |
| minified blocks after an error | `x = ) : ` + `if a then : b = 1 : end if : `, k = 1,000 and 8,000 | ≤ 1.5 | ≤ 150 ms | ≤ 8 MiB | the same with `:` before the keywords (on `86eac11`: 1.88; 13.1 s) |
| comments on lines ended by a lone CR | `x = ) ' c` + a lone `CR`, k = 1,000 and 4,000 | ≤ 1.5 | ≤ 100 ms | ≤ 8 MiB | regression test of runs and look-ahead that stop at a lone `CR` (on `b501847`, where the look-ahead after a comment read to the next `LF`: 1.97; 200 ms) |

Query scaling guards. The same script runs one guard per row of its
`QUERY_GUARDS` table: the full highlight query over a witness at two
sizes through `tree-sitter query -c --quiet --time` (every capture with its
predicates; parsing excluded), the minimum of three runs for each. A guard
fails if the local exponent of the two times or the larger time exceeds the
row's bound, or if a run times out or prints no time (so does a recovery
guard).

| Row | Witness, sizes | Exponent | Larger run | Kind |
|---|---|---|---|---|
| member chain | `x = a` + `.b`, k = 2,000 and 16,000 | ≤ 1.5 | ≤ 500 ms | regression test of the Session 05-3 member pattern (before it: exponent 2.06, 2.2 s at k = 16,000) |
| member and attribute chain | `x = a` + `.b@c`, k = 1,000 and 8,000 | ≤ 1.5 | ≤ 500 ms | the same for the attribute pattern (before it: 2.03, 2.1 s) |
| method chain | `x = a` + `.b(1)`, k = 2,000 and 16,000 | ≤ 1.5 | ≤ 500 ms | regression test of the flat method call (tree-schema.md "Re-freeze of 0.1.0"; before it: 2.04, 9.4 s) |
| statement method chain | `a` + `.b(1)`, k = 2,000 and 16,000 | ≤ 1.5 | ≤ 500 ms | the same as a statement (before it: 2.01, 8.5 s) |
| mixed chain | `x = a` + `.b(1)[2]`, k = 1,000 and 8,000 | ≤ 1.5 | ≤ 500 ms | the same with index expressions (before it: 2.00, 3.4 s) |
| optional chain | `x = a` + `?.b?(1)?[2]`, k = 1,000 and 8,000 | ≤ 1.5 | ≤ 500 ms | the same with optional chaining (before it: 1.98, 3.3 s) |
| PRINT items | `print ` + `a;`, k = 2,000 and 16,000 | ≤ 1.5 | ≤ 500 ms | regression test of the flat PRINT item list (A5-01; before it: 2.13, 9.0 s) |
| malformed minus, parenthesis, bracket | `x = ` + `-(-[`, k = 1,000 and 16,000 | ≤ 1.5 | ≤ 500 ms | regression test of the error-only tokens in a flat `ERROR` (QUERY-MALFORMED; before it: 1.80, 5.7 s) |
| malformed parenthesis and minus | `x = ` + `(-`, k = 1,000 and 16,000 | ≤ 1.5 | ≤ 500 ms | the same (before it: 1.98, 1.7 s) |
| malformed parentheses | `x = ` + `(`, k = 1,000 and 16,000 | ≤ 1.5 | ≤ 500 ms | the same (before it: 1.92, 413 ms) |
| malformed brackets | `x = ` + `[`, k = 1,000 and 16,000 | ≤ 1.5 | ≤ 500 ms | the same (before it: 1.91, 369 ms) |
| unclosed TRY blocks | `try⏎` with no prefix, k = 1,000 and 16,000 | ≤ 1.5 | ≤ 500 ms | the same (before it: 1.90, 701 ms) |

Recovery goldens. The same script parses every `test/recovery/*.brs` and
compares the node lines of its `--cst` output with the `.cst` golden beside
it: the scanner unit cases (line breaks, a lone `CR` in a run, between lines
and between valid statements, short and long inputs that end without a line
break, a long last line that ends with a block keyword, a comment or a block
keyword far from the end, NUL, UTF-8, strings with `'`, comments), the lines
after an error (also after a long run, after a second error that follows a
long run on its line or in the ELSE body after it, in a multi-line literal
and a nested one, after an IF header, before a directive closer and at the
end of input inside open blocks) and lines that begin with an operator. In
the cases of its `LOCALITY` list every sub or function declaration must lie
outside every `ERROR` node. The goldens are the recovery trees of the pinned
runtime, not a language contract; they change only with a reviewed grammar,
scanner or runtime change and are never regenerated to make the check pass.
Earlier Session 05-7 scanners fail them: on `cc664de` (the first scanner)
every golden then present differed and two `LOCALITY` cases failed; with the
current set, on `b501847` (a recovery line break at every line break during
recovery) twelve cases differ and six `LOCALITY` cases fail, on `e093ac8`
(the A2 fix, rejected after review A3) fourteen differ and four fail, on
`4ff5633` (the A3 fix, rejected after review A4) six differ and three fail,
on `494ecb2` (one empty end-of-input line end per stack version, changed
after review A5) two differ and fail, and on `d3764a3` (a second one only
after a long run, changed after review A6) one differs and fails. On
`47d4047` two `LOCALITY` cases, `eof-after-keyword-stop` and
`eof-open-bracket`, fail (the candidate keeps more there); in the others
every declaration lies outside every `ERROR` node, and two of them give the
same trees as the goldens (the others differ at least by the error-only
names).

The "before it" values of the rows added or tightened in Session 05-7 are
these guards run on the grammar, parser and query of `47d4047` through the
pinned CLI on the local Windows host (the live known-bad check of Session
05-7); every one of those rows fails there, and the R-A-01, member and
attribute rows pass there as before. The B4-01/B5-02 PRINT row, run with its
bounds at k = 1,000 and 4,000 on `8e2ad7c` (the parser before the
`_print_items` fix; its memory is quadratic, so the larger size is not run),
fails too (exponent 1.89, 872 ms, 339 MiB growth). The same check on the
candidate with a scanner that produces no token fails every B5 row and three
of the four KL-002 rows, and with the method-call pattern in parent form
(`(call_expression property: (identifier) @function)`) every method, mixed
and optional chain row.

## Release qualification lane

The CLI guards above run in hosted CI but cannot measure cancellation,
callback gaps, tree deletion, allocator memory or the stock runtime without
the CLI. The release qualification lane measures them on the local Windows
host for one candidate identity:

    python scripts/qualify/run.py --cc <gcc.exe> --runtime <tree-sitter 0.27.0 source root> --out <new dir>
        --support 0.25.1=<source root> --support 0.26.13=<source root>

It verifies each runtime source root against `scripts/qualify/runtime-<version>.sha256`
(the blob list of the upstream tag), regenerates every generated input and
compares it with `recorded-inputs.json`, builds the Job-object supervisor
(`supervisor.c`) and passes its six-mode self-test (memory cap, watchdog,
output cap, descendant termination, private environment), then builds, inside
that supervisor, the stock runtime, the candidate parser and scanner and the
native probe (`probe.c`: parse, query, navigation, cancellation, incremental
edits and parser reuse through the public C API; a second build counts
allocations), and regenerates the references H (`47d4047`, parser `2711f7cc…`)
and BEFORE_PRINT (`8e2ad7c`, parser `3f3eafd1…`) from their commits. Every run
is limited to 512 MiB of commit, 15 s and 8 MiB of output, one child at a time,
with a private environment. It writes `identity.json`, every run
(`runs.jsonl`) and the gate results (`gates.json`); its exit status is 0 only
if every selected gate passes. A censored run (cap, watchdog, crash) fails its
point. The bounds are those of protocol v3 (Session 05-2) and are not relaxed
by the lane:

| Gate | Inputs | Pass condition |
|---|---|---|
| B5-01-MEMORY | `x = ` + `+f([)` and `-f(-)` k ≤ 800, `x = ` + `{a:@*}<` k ≤ 600 | allocator peak live and working-set growth < 64 MiB; live-memory exponent of every consecutive pair ≤ 1.5 |
| B5-02-LIFECYCLE | `print ` + `f([)` and `,+*`, k 1,000–20,000; `x = ` + `-f(-)` k ≤ 20,000 | parse, tree and parser deletion complete; call exponent 1,000 → 4,000 ≤ 1.5 |
| A5-01-COST | PRINT items `a;`, `1;` k ≤ 32,000 and `a ` k ≤ 8,000 | query and cursor, field and index navigation, paired with BEFORE_PRINT: same work (and the query match limit never exceeded), ratio ≤ 1.5; exponents ≤ 1.5 |
| CANCEL | the v3 cases and seven 1 MiB inputs registered to run past the budget | 200 ms budget: return ≤ 300 ms, deletion ≤ 100 ms, live memory after the budget < 64 MiB, measured from the first allocation or progress callback after the budget (a reached budget without a recorded crossing is `NOT_RUN`, not a pass); the registered inputs are cancelled |
| CANCEL-OVERSHOOT | cancellation and 1 MiB malformed inputs, budgets 25 ms–4 s | overshoot ≤ 100 ms on every point that reaches its budget; the number of such points is reported |
| MAX-CALLBACK-GAP, CLEANUP-ALL | the same and six 1 MiB valid inputs | progress-callback gap ≤ 100 ms; tree and parser deletion ≤ 100 ms |
| LARGE-INPUT | 1 MiB malformed and valid inputs | completes, peak commit ≤ 256 MiB, parse ≤ 10 s (the PRINT-separator input time-exempt as in v3) |
| QUERY-MALFORMED | six unclosed-group families, k 2,000 and 20,000 | full highlight query exponent ≤ 1.5, match limit never exceeded |
| VALID-PARSE | PRINT items, six valid families 4–256 KiB, W03 | paired with H: ratio ≤ 1.5; exponent of the largest pairs ≤ 1.2 |
| SEM-PUBLIC | the 2,811 inputs of the tree comparison | projection of the re-frozen schema onto H's (tree-schema.md "Re-freeze of 0.1.0") equal on every valid input; error presence equal; every mutant of the projection detected |
| INCREMENTAL-REPAIR | 28 edit scripts | incremental parse equals a fresh parse; inverse edits restore the original; both comparators detect a planted difference |
| RESUME-RESET | six registered inputs | resume after cancellation, reset and a new source each equal a fresh parse; an input whose parse ends before the trigger is `NOT_TRIGGERED` and gives no evidence, and at least one must be triggered; two parsers are independent |
| SUPPORT | B5 and A5-01 points on runtimes 0.25.1 and 0.26.13 | complete within the caps (the product runtime is 0.27.0) |
| REGRESSION-SWEEP | 297 context × unit × line-end families (eleven units, the last a block keyword after each malformed piece) (line ends: a line break, `:` and a statement, none), k 100, 400, 4,000, 20,000, 1 warmup and 5 runs each (median) | no crash; memory growth < 64 MiB; exponents 400 → 20,000 and 4,000 → 20,000 ≤ 1.5 with the smaller time clamped to the 0.1 ms floor, the units of the retired KL-002 included |
| ABS-MEMORY | every registered B5, A5-01 and cancellation point | peak commit ≤ 128 MiB |
| RECOVERY-LOCALITY | the 1,699 single-line mutants of `program.brs`, `compact.brs` and `highlights.brs` (ten mutations per line) | rows under `ERROR` or `MISSING` apart from the mutated one, through the pinned CLI: the candidate hides rows that H keeps, by five and by twenty rows or more, in no more mutants than the reverse |

The lane's result supports only the identity it names (`identity.json`:
compiler, supervisor, candidate files, probe images, the lane's own sources,
git HEAD and whether the working tree was clean). The CLI guards are its
hosted subset; a lane gate is never inferred from a CLI guard. After the
Session 05-7 review the lane gained the RECOVERY-LOCALITY gate, the 4,000
sweep point and floor clamp, every B5-01 pair, the match-limit checks, the
callback crossing of CANCEL and two RESUME-RESET inputs that are long enough
to trigger; after the delta review it also gained a sweep unit with a block
keyword after each malformed piece (B2-01). Each change makes a gate stricter
or measures what it could not. RECOVERY-LOCALITY and the regeneration of
the references run the pinned CLI outside the supervisor, with the `--cc`
compiler and a private parser-library directory per checkout.

## Highlight query changes

A change to `queries/highlights.scm` that keeps roles is compared with the
query it replaces on the same parser, runtime and inputs (valid inputs and
inputs with `ERROR` or `MISSING` nodes), at equal work: every capture
consumed, with no match limit, range, start depth or cancellation set.
Three results are compared:

- the native captures, in cursor order and as a multiset of capture name,
  node kind, byte range and missing flag (no predicates);
- `tree-sitter query -c`, which applies the text predicates;
- the final roles of `tree-sitter highlight --html --layout fragment --style
  minimal <input> --query-paths <dir>/highlights.scm`, aligned to the input
  bytes. The default theme holds every capture name of the query.
  `--query-paths` takes one or more values, so the input goes before it; it
  reads only a file named `highlights.scm`.

Valid inputs must give identical results in all three. A difference on an
input with `ERROR` or `MISSING` nodes is a change of meaning: it is
classified (inside an `ERROR` node, at a `MISSING` node, elsewhere) and the
owner approves it before the query changes. W11 still passes. The Session
05-3 comparison is in
[session-05-3-repository-owned-hardening.md](../reports/session-05-3-repository-owned-hardening.md).

## Fixture rules

- Recovery and negative fixtures assert that an error occurs (`:error`) unless
  a requirement specifies the recovery shape, because recovery trees differ
  between runtimes.
- Positive expectations are written from the specification, never generated
  with `tree-sitter test --update`; a mismatch is investigated against the
  specification before either side changes.
- Corpus files are LF text. Fixtures whose bytes matter (CR bytes, byte-order
  mark) live under `test/corpus/bytes/`; the commit that adds the first of
  them adds `test/corpus/bytes/** -text` to `.gitattributes` (likewise for
  `test/samples/program-crlf.brs`).
- Every registry fixture exists exactly once in the corpus; inputs and
  expectations are catalogued in [workload-matrix.md](workload-matrix.md),
  together with the validation sets W01–W14.
- `unresolved` forms have no corpus fixture; they appear only as V10 seeds.
  Out-of-scope "guard" fixtures assert that semantically invalid but
  well-formed code parses without `ERROR`.
- Defects of earlier grammars that must not recur are listed in
  [known-regressions.md](known-regressions.md) with their guarding checks.
- Generated-artifact drift checks cover every generated file, not only
  `src/parser.c`.

## Level 2 policy

- A requirement that needs Level 2 evidence carries either a dated Level 2
  record (device model, OS build, date, probe description, derived verdict) or
  a disclosed `provisional`/`unresolved` status. This applies to 1.0 as well.
- Only derived verdicts are recorded; raw device or console output is not
  published.
- A device campaign starts only after the owner has reviewed the Roku
  developer license terms and explicitly authorized it. Level 2 checks are
  not rerun in CI.
- Whether a campaign is planned is tracked in `docs/roadmap.md`.
