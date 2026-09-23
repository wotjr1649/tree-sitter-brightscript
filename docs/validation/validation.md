# Validation contract

Defines validation levels (V0–V10; distinct from the source levels L1–L5 in
`docs/provenance/source-policy.md`), the claims each supports, gates, and how
failures are handled. Automated tooling is built with the grammar; until then
V0 is the manual checklist below.

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
| V10 | — | pathological inputs | fuzzing |

V9 evidence is produced in `go-treesitter`, not here
([ADR-0006](../design/decisions/ADR-0006-downstream-integration-boundary.md)).

The v1.0 column is the single definition of 1.0 readiness; other documents
link here.

A **session gate** is met when V0 and every check the Gates table requires for
the session's changes are `PASS`, or `NOT_RUN`/`BLOCKED` with a recorded
reason; any `FAIL` means the gate is not met.

## V0 checklist (manual until automated)

1. No `_ref/`, `docs/prompts/`, `docs/plans/`, `artifacts/` or `.work/` content
   is staged or tracked.
2. `git check-ignore` confirms local-only paths are ignored and generated
   sources (`src/parser.c`, `src/grammar.json`, `src/node-types.json`,
   `src/tree_sitter/*`) and `package-lock.json` are not.
3. Relative Markdown links in tracked documents resolve.
4. License metadata is MIT everywhere it appears.
5. Tracked text files contain no CR bytes and end with a newline.
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
- Whether a campaign is planned is tracked in `docs/roadmap.md`.
