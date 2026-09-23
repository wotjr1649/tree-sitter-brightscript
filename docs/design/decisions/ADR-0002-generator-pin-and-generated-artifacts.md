# ADR-0002 — Generator pin and generated artifacts

Status: Accepted (generator version selection deferred to the first generation)
Date: 2026-09-23

## Context

- `grammar.js` is the canonical source; `tree-sitter generate` produces
  `src/parser.c`, `src/grammar.json`, `src/node-types.json` and
  `src/tree_sitter/*`. Downstream consumers use the committed `src/parser.c`.
- The legacy grammar shipped a query that referenced a node its committed
  parser did not contain (`253fdfaa`, fixed by regeneration in `0c534d56`).
  Drift between source and generated files must be mechanically impossible to
  miss.
- With ABI 15, `parser.c` embeds the grammar version from `tree-sitter.json`,
  so a version bump changes generated output.
- Official grammars declare the CLI with caret ranges and their CI installs the
  latest CLI; the common test action (`tree-sitter/parser-test-action` v3)
  checks regeneration drift for `parser.c` only.
- The npm `tree-sitter-cli` package downloads its binary at install time
  without checksum verification.
- At 2026-09-23 the latest stable release is 0.27.0, with open issues #5910
  (runtime error-recovery regression) and #5925 (lexical conflicts can change
  keyword tokenization). See [upstream-sources.md](../../provenance/upstream-sources.md).

## Decision

1. Generate with an **exact stable Tree-sitter release**. Development commits
   and floating version ranges are not allowed.
2. Generate **ABI 15**, passed explicitly.
3. The concrete version is selected in the session that first runs
   `tree-sitter generate`: take the latest stable release after reviewing the
   open regressions (candidate at this date: 0.27.0), record it exactly in
   project-local tool metadata (`package.json` devDependency plus lockfile),
   verify the installed binary's SHA-256 against the release asset digest, and
   record the identity in `docs/provenance/upstream-sources.md`.
4. `src/parser.c`, `src/grammar.json`, `src/node-types.json` and
   `src/tree_sitter/*` are committed and never edited by hand.
5. Drift check: regenerating with the pinned generator must reproduce **all**
   committed generated files byte for byte. Generated output that changes
   without a change to `grammar.js`, `tree-sitter.json` or the pinned toolchain
   is a blocker whose provenance must be explained.
6. Grammar changes and their regenerated files land in the same commit.
   `src/node-types.json` changes are reviewed as public tree changes under
   `docs/specs/tree-schema.md`.
7. Generator upgrades follow: proposal → regenerate → `node-types.json` and
   tree diff → corpus and conformance tests → native oracle → explicit adoption
   recorded here or in a superseding ADR, plus `upstream-sources.md`.

## Adoption procedure

Added 2026-09-23 (Session 02). It makes decision 3 mechanical and adds a
fallback order; it does not change decisions 1–7. The session that first runs
`tree-sitter generate` follows it without asking the user, except in step 7.

1. **Eligible releases.** Tags `vX.Y.Z` of `tree-sitter/tree-sitter` that are
   GitHub releases, not drafts or pre-releases, with `X.Y.Z` ≥ 0.26.0 and a
   `tree-sitter-cli` npm package of the same version. 0.26.0 is the oldest
   stable line whose DSL, test runner and CLI behaviour were checked while the
   grammar design was frozen (Level 3, the tree-sitter clone at tags
   `v0.26.0`, `v0.26.13`, `v0.27.0`; the one difference found, trailing-CR
   handling in the corpus runner, is neutralised by how byte fixtures are
   written, grammar-design §2); 0.25.x lacks the `:cst` test attribute and was
   not checked further, so it is not eligible. Order: descending semantic
   version. The first is the candidate. If the release list cannot be read
   (no network), the procedure is `BLOCKED` and the user is told what is
   missing; no version is guessed.
2. **Issue review.** For every issue listed in this ADR (#5910, #5925) and
   every open issue that names the candidate version in its title and is
   labelled as a bug, record number, state and whether it concerns the
   generator, the CLI test runner or the runtime, in
   [upstream-sources.md](../../provenance/upstream-sources.md). The review
   does not reject a candidate by itself; step 6 decides materiality.
3. **Identity.** Install `tree-sitter-cli@X.Y.Z` exactly (no range) as a
   devDependency with a lockfile. The npm installer downloads the gzip-compressed
   platform asset `tree-sitter-<platform>-<arch>.gz` of GitHub release
   `vX.Y.Z` and decompresses it (`crates/cli/npm/install.js` @ `v0.27.0`), so
   the check has two parts: (a) the SHA-256 of that `.gz` asset, downloaded
   from the release, equals the release's published digest (the API `digest`
   field); (b) the SHA-256 of the decompressed asset equals the SHA-256 of the
   binary npm installed. Both are recorded for the platform the session runs
   on; other platforms are recorded when a CI or another machine first uses
   the pin. A mismatch fails the candidate.
4. **Capability smoke.** With `--abi 15`, generate the bootstrap grammar
   (comments and line terminators only) and run the registry fixtures that use
   nothing else: `BS-LEX-006: CRLF between comment lines` (under
   `test/corpus/bytes/`), `BS-LEX-008: empty file` and
   `BS-LEX-008: only comments and blank lines`. They must pass.
5. **Determinism.** Generate twice from a clean tree; every generated file
   (`src/parser.c`, `src/grammar.json`, `src/node-types.json`,
   `src/tree_sitter/*`) must be byte-identical between the runs.
6. **Material issue during implementation.** If a required gate later fails
   and the failure reproduces with the pinned release but not with the next
   eligible release (same grammar, same fixture), the issue is material:
   switch the pin to that next release, regenerate, rerun every gate, and
   record the reason here and in upstream-sources.md.
7. **Fallback and stop.** A candidate failing step 3, 4 or 5 is replaced by the
   next eligible release in the step 1 order. If no eligible release passes,
   stop and ask the user. A development commit or a version range is never
   used.

The adopted version, tag commit, npm integrity value, binary SHA-256, ABI and
date are recorded in upstream-sources.md in the same commit as the first
generated files. A newer stable release published during the implementation
session is not adopted in that session; upgrades follow decision 7.

## Alternatives considered

- **Pin a development commit** — rejected: exposes unreleased generator API
  changes, needs a source build, and is hard for CI and contributors to
  reproduce.
- **Caret range with the latest CLI in CI (official-grammar practice)** —
  rejected: generated bytes would depend on install time, defeating the drift
  check.
- **Select the generator at execution time and record it (as
  `go-treesitter` does for its oracle)** — suitable for a consumer that
  regenerates evidence, not for a producer whose committed bytes are the
  contract.
- **Pin 0.26.13 now** — rejected for now: avoids #5910 but forgoes 0.27
  generator fixes; the choice is made at first generation with current facts.

## Consequences

- Upgrades are explicit work with their own evidence.
- CI must install the exact pinned version.
- Error-recovery trees can differ between runtimes, so recovery fixtures assert
  error presence unless a recovery shape is itself a requirement
  (`docs/validation/validation.md`).

## Validation / enforcement

- V0 drift check over all generated files (implemented with the first grammar).
- Review of every `node-types.json` diff.
- Recorded generator version, ABI and binary digest in `upstream-sources.md`.

## Revisit conditions

- A newer stable release fixes or introduces regressions affecting this grammar.
- A new ABI becomes the default, or a consumer's accepted ABI range changes.
