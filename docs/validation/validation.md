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
the W03 and W05 checks, V5 (W10) and V10 (W06–W08, W13 with fuzzing); the
commands are in [workload-matrix.md](workload-matrix.md) "Automation". It never
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
modules outside `scripts/`, YAML keys escaped other than `\x72un`, a custom
step `shell:`, local actions, `binding.gyp` and `.npmrc` settings (Session 05-1
delta re-audit C4-01, C4-02).
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
| KL-002 | active; accepted for 0.1.0 by the owner on 2026-09-24 as a class of behaviour | none is violated (robustness only); the constructs involved are right-recursive nestings the grammar accepts: prefix operators (BS-EXP-012, 018; their nesting BS-EXP-027, 028 is provisional), the right-associative `^` (BS-EXP-011), single-line IFs nested in a single-line branch (BS-STMT-009, provisional) and the PRINT item list (BS-STMT-024–026, 040; 026 provisional, 040 tolerated) | Error recovery time can grow with the square of the number of repeated malformed pieces that keep such a nesting pending in one statement or its continuation. Known families (measured): a prefix operator (`+`, `-`, `not`) followed by a token that cannot start an operand and forces a reduction (`x = +*+*…`, `x = (not)not)…`, also inside closed groups, call arguments and after `print`, `return`, `if`, `while`, `for`, `dim`); `^` followed by a non-operand (`x = 2^*2^*…`, `2^)`, `2^,`, `2^-*`, also inside closed groups); a condition broken across a line inside nested single-line IFs (`if a⏎*2if a⏎*2…`, `x = if a then⏎*2…`); a directive inside an expression (`x = #if a⏎*2…`, also after `print`, in `(` and `f(`); a PRINT continued by malformed lines (`print ,+⏎,+⏎…`, `print ;-⏎…`); and each of these continued across line breaks or `:` while every piece starts with a prefix operator or `^` (`x = -` followed by `-` lines). The list is not exhaustive: other right-recursive nestings may behave the same. Memory stays small (about 24 MiB at most for the CLI process in every measured family, 13.5 MiB native for the prefix witness at 16 KB), and the runtime's progress callback stops the parse. The open release-blocking findings B5-01 and B5-02 ([0.1.0-release.md](../reports/0.1.0-release.md#status-hold)) are not covered: there memory grows quadratically, or the parse overflows the stack. On the release parser runtimes 0.25.1, 0.26.13 and 0.27.0 give the same trees and quadratic curves, and generators 0.26.13 and 0.27.0 emit identical files. Valid input, scattered errors and statements separated by valid lines stay linear. Measurements, cause and mitigation: [0.1.0-performance.md](../reports/0.1.0-performance.md#known-limitation-kl-002) | W13 seeds `KL-002 B-01 witness k=1000`, `KL-002 nested single-line IF witness k=1000`, `KL-002 prefix operators across lines k=1000`, `KL-002 exponent witness k=2000`, `KL-002 PRINT across lines k=500`, and the KL-002 rows of the recovery scaling guards |
| KL-003 | retired 2026-09-24: the `_pow_left` change of Session 05-1 (grammar-design §5) removed its quadratic memory; its quadratic time is part of KL-002, and the owner's exception to the bounded-memory condition is withdrawn | — | Error recovery on a run of `^` each followed by a token that cannot start an operand needed quadratic memory at end of input (1.1 GiB at 24 KB) that the progress callback could not interrupt | — |

KL-002 and the V10 bound. W06's per-input bound (10 s, 1 GiB) still applies
to every W06 input and W13 seed, the KL-002 witnesses included. An input of
the KL-002 class large enough to exceed it is a `FAIL` of that bound, not a
pass: through the pinned CLI the measured families pass 10 s from about 5 KB
(PRINT continued by malformed lines), 10 KB (prefix operators, also across
lines), 14 KB (`^`) and 29 KB (nested single-line IFs); none of them
approaches the memory bound (the open finding B5-01 does, [0.1.0-release.md](../reports/0.1.0-release.md#status-hold)). Such inputs are accepted
for 0.1.0 as KL-002, they are not W06 inputs, and V10 supports no time claim
for them beyond the recorded measurements, and no claim that the known
families are the only ones. A fix is recorded by re-measuring, narrowing or
retiring the limitation and turning its guard into a scaling regression test.

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
| KL-002 prefix | `x = ` + `+*`, k = 250 and 1,000 | ≤ 2.5 | ≤ 3 s | ≤ 32 MiB | disclosed limitation: worse than quadratic, a large slowdown or a memory regression fails |
| KL-002 nested IF | `if a⏎*2`, k = 250 and 1,000 | ≤ 2.5 | ≤ 3 s | ≤ 32 MiB | as above |
| KL-002 exponent | `x = ` + `2^*`, k = 500 and 2,000 | ≤ 2.5 | ≤ 5 s | ≤ 24 MiB | as above, and a regression test of the `_pow_left` memory fix (before it: 69–84 MiB growth) |
| KL-002 PRINT across lines | `print ` + `,+⏎`, k = 125 and 500 | ≤ 2.5 | ≤ 5 s | ≤ 32 MiB | as the first row |
| R-A-01 | `x = ` + `f(*`, k = 500 and 2,000 | ≤ 1.5 | ≤ 300 ms | ≤ 24 MiB | regression test of the Session 05-1 fix (before it: exponent 1.7–2.1, 3 s, 1.24 GiB) |
| B4-01 PRINT items | `print ` + `f([)`, k = 1,000 and 4,000 | ≤ 1.5 | ≤ 300 ms | ≤ 24 MiB | regression test of the `_print_items` memory fix (before it: 386 MiB at 16 KB through the CLI) |

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
