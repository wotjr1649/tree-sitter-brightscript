# Validation contract

Defines evidence levels, the claims each level supports, release gates, and
how failures are handled. Validation tooling is built with the grammar; none
exists yet.

## Evidence levels

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
| V3 | requirements touched | all implemented requirements | every Level 1 requirement `covered` or disclosed `provisional`/`unresolved` |
| V4 | on node-shape change | `highlights.scm` | `highlights.scm`, `tags.scm` |
| V5 | on boundary or ambiguity changes | representative edit set | extended edit set |
| V6 | — | required | required |
| V7 | optional | optional | recommended |
| V8 | — | per Level 2 policy | per Level 2 policy |
| V9 | — | only for integration claims | only for integration claims |
| V10 | — | pathological inputs | fuzzing |

V9 evidence is produced in `go-treesitter`, not here
([ADR-0006](../design/decisions/ADR-0006-downstream-integration-boundary.md)).

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

## Failures and known limitations

- No retry-until-green. A failing check is investigated; the fix or the
  failure is recorded.
- Failing tests are not deleted, weakened, skipped or reclassified to get a
  pass.
- A known defect becomes a named known limitation with an ID (`KL-NNN`), the
  affected `BS-*` requirement, the observed behaviour and the fixture that
  demonstrates it. Tree-sitter's `:skip` attribute is allowed only on a fixture
  that cites its `KL-NNN`.
- No known limitations are recorded yet.

## Fixture rules

- Recovery and negative fixtures assert that an error occurs (`:error`) unless
  a requirement specifies the recovery shape, because recovery trees differ
  between runtimes.
- Corpus files are LF text. Fixtures whose bytes matter (CRLF, CR, BOM,
  missing final newline) live under a dedicated path that `.gitattributes`
  marks `-text` when the first one is added.
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
- Current state (2026-09-23): no device is available and none is planned, so
  Level 2-dependent requirements remain `provisional` or `unresolved`.
