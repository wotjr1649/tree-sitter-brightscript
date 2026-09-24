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
and every `run` command of a CI step is `npm ci`, a check script or git, with
no shell metacharacters (`scripts/test_tscli.py` enforces all three).
Once per process `tscli.py` copies the installed binary into a private
directory, compares the copy's SHA-256 with its record in
[upstream-sources.md](../provenance/upstream-sources.md) and its version with
the pin, and from then on runs only that copy: a binary that differs is never
run, a binary replaced or retargeted after the check is not run by that
process, and no DLL beside the installed binary is loaded. Out of scope:
another process of the same user writing into the private directory during
the run. The working tree's record and scripts are trusted, and the programs
the CLI starts itself (node for `generate`, the C compiler for the first
build) are not identity-bound; V1 drift detects a divergent `generate`. `python scripts/tscli.py test` is the verified form of
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
| KL-002 | active; accepted for 0.1.0 by the owner on 2026-09-24 | none is violated (robustness only); the constructs involved are the prefix operators of BS-EXP-012, 018, 027 and their nesting (BS-EXP-028) | Error recovery time grows with the square of the number of consecutive malformed prefix-operator pairs in one expression: a prefix operator (`+`, `-`, `not`) followed by a token that cannot start an operand and forces the pending prefix operators to reduce (`*`, `/`, `,`, `)`, `<`, …), repeated, as in `x = ` + `+*`×k or `x = (` + `not)`×k, also inside closed `(…)`, `[…]` or call arguments and after `print`, `return`, `if`. Memory stays small (≤ 20 MiB at 16 KB); the runtime's progress callback stops it. Runtimes 0.25.1, 0.26.13 and 0.27.0 behave alike and generators 0.26.13 and 0.27.0 emit identical files. Valid input, scattered errors and one malformed statement per line stay linear. Measurements, cause and mitigation: [0.1.0-performance.md](../reports/0.1.0-performance.md#known-limitation-kl-002) | W13 seed `KL-002 B-01 witness k=1000` and the KL-002 row of the recovery scaling guards |
| KL-003 | active; accepted for 0.1.0 by the owner on 2026-09-24 as an explicit exception to the bounded-memory condition for known limitations | none is violated (robustness only); the construct involved is the right-associative `^` of BS-EXP-011 | Error recovery on a run of `^` each followed by a token that cannot start an operand, in one expression (`x = ` + `2^*`×k, `2^)`, `2^,`), grows quadratically. With `*` and similar tokens memory grows quadratically too: the pinned CLI needs 86 MiB at 6 KB, 326 MiB at 12 KB and 1.13 GiB at 24 KB, and the cost lies in the runtime's end-of-input acceptance, which the progress callback does not interrupt (a 200 ms limit stopped a 24 KB input after 2.0 s). A minimal grammar with only a right-associative `^` behaves the same; no grammar change that keeps BS-EXP-011 and the tree was found. Measurements and mitigation: [0.1.0-performance.md](../reports/0.1.0-performance.md#known-limitation-kl-003) | W13 seed `KL-003 exponent witness k=2000` and the KL-003 row of the recovery scaling guards |

KL-002, KL-003 and the V10 bound. W06's per-input bound (10 s, 1 GiB) still
applies to every W06 input and W13 seed, the KL-002 and KL-003 witnesses
included. An input of either family large enough to exceed it is a `FAIL` of
that bound, not a pass: KL-002 inputs exceed the time bound from about 9 KB
through the pinned CLI; KL-003 inputs exceed the time bound from about 13 KB
(`2^)`) and the memory bound from about 23 KB (`2^*`). They are accepted for
0.1.0 as KL-002 and KL-003, they are not W06 inputs, and V10 supports no time
or memory claim for them beyond the recorded measurements. A fix is recorded
by re-measuring, retiring the limitation and turning its guard into a scaling
regression test.

Recovery scaling guards. `scripts/check_robustness.py` runs, with W13 locally
and in hosted CI, one guard per row of its `RECOVERY_GUARDS` table: the
witness `x = ` + unit×k at two sizes, the minimum of three CLI parse times for
each, and the peak memory of the CLI process for the larger one. A guard
fails if the local exponent of the two times, the larger time or that peak
memory exceeds the row's bound:

| Row | Unit, sizes | Exponent | Larger parse | Peak memory | Kind |
|---|---|---|---|---|---|
| KL-002 | `+*`, k = 250 and 1,000 | ≤ 2.5 | ≤ 3 s | ≤ 256 MiB | disclosed limitation: worse than quadratic, or a large constant-factor slowdown, fails |
| R-A-01 | `f(*`, k = 500 and 2,000 | ≤ 1.5 | ≤ 1 s | ≤ 256 MiB | regression test of the Session 05-1 fix (before it: exponent 1.7–2.1, 3 s, 1.27 GiB) |
| KL-003 | `2^*`, k = 500 and 2,000 | ≤ 2.5 | ≤ 3 s | ≤ 512 MiB | disclosed limitation, memory included (observed 86–89 MiB at k = 2,000) |

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
