# AGENTS.md — tree-sitter-brightscript

Repository-wide durable rules for humans and coding agents.

This file contains stable operating constraints. Volatile session instructions, prompts, plans, and raw evidence do not belong here.

## What this repository is

This repository is an independently implemented Tree-sitter grammar for Roku BrightScript.

It owns:

- BrightScript lexical and syntactic grammar;
- the public parse-tree shape produced by that grammar;
- generated Tree-sitter parser artifacts;
- syntax-oriented Tree-sitter queries;
- specification-to-test traceability;
- conformance and regression fixtures;
- grammar provenance and release evidence.

It does not own:

- Roku runtime or SceneGraph API semantics;
- semantic name or type resolution;
- code graphs;
- application-specific analysis policy;
- the `go-treesitter` runtime.

`github.com/wotjr1649/go-treesitter` is a downstream consumer of generated grammar artifacts.

## Specification authority

Use evidence in this order:

1. Roku's official BrightScript developer documentation for language syntax.
2. Reproducible behavior from an official Roku compiler/runtime when documentation is ambiguous or incomplete.
3. Official Tree-sitter documentation for grammar-generator and runtime behavior.
4. Community implementations, including BrighterScript, as non-normative differential evidence.
5. Legacy Tree-sitter BrightScript grammars only as historical or defect-comparison evidence.

A lower authority must not silently override a higher one.

When authoritative sources conflict or remain ambiguous, record the ambiguity rather than inventing language behavior.

## Independent implementation boundary

Do not copy grammar rules, generated parser code, queries, tests, bindings, or other implementation text from `ajdelcimmuto/tree-sitter-brightscript` or another BrightScript parser into this repository.

Legacy implementations may be inspected to identify test cases, suspected omissions, or behavioral differences. Re-derive the implementation from normative syntax evidence.

Do not copy Roku documentation wholesale into the repository. Record URLs, retrieval dates, concise derived requirements, and independently authored fixtures instead.

## Local reference repositories

`D:\AIDEV\tree-sitter-brightscript\_ref` contains local research material and is not product source.

Treat `_ref/` as read-only evidence during ordinary implementation work.

Expected reference categories may include:

- upstream Tree-sitter;
- the legacy Tree-sitter BrightScript grammar;
- BrighterScript;
- locally retained Roku documentation evidence.

Do not commit `_ref/`.

`D:\AIDEV\go-treesitter` is a separate downstream repository. Treat it as read-only unless the current task explicitly authorizes integration changes there.

## Canonical sources and generated files

`grammar.js` is the canonical grammar implementation.

Generated files under `src/` are committed artifacts, not independent sources of truth.

After any grammar change, regenerate the parser with the repository-pinned Tree-sitter toolchain and verify that generated output is deterministic.

Never hand-edit `src/parser.c`, `src/grammar.json`, or `src/node-types.json` to simulate a grammar fix.

If generated files change without a corresponding source change, stop and explain the provenance.

## External scanner policy

Prefer a grammar without an external scanner.

An external scanner may be introduced only when a concrete BrightScript syntax requirement cannot be represented correctly and maintainably with ordinary Tree-sitter grammar facilities.

Adding an external scanner requires an ADR, dedicated tests, incremental-state tests, native-runtime comparison, and downstream `go-treesitter` compatibility analysis.

## Documentation model

Canonical product contracts are tracked in Git:

- `docs/specs/` — language and grammar contracts;
- `docs/design/` — architecture;
- `docs/design/decisions/` — ADRs;
- `docs/provenance/` — source authority and identity;
- `docs/validation/` — gates and workloads;
- `docs/reports/` — retained release-relevant summaries.

Session execution material is local and ignored by Git:

- `docs/prompts/`;
- `docs/plans/`;
- `artifacts/`;
- `_ref/`.

A session result that changes the durable product contract must be promoted into the appropriate canonical document before the work unit is considered complete.

## Evidence discipline

Do not equate parser generation with language correctness.

A valid-syntax fixture expected to parse cleanly must not contain unexplained `ERROR` or `MISSING` nodes.

A smoke test is not specification coverage.

Fresh-parse equality is not native Tree-sitter oracle equality.

Native Tree-sitter equality is not proof that the grammar matches Roku's language specification.

Every claim must identify the evidence level that supports it.

Preserve failures and regressions. Do not delete, weaken, skip, or reclassify a failing test merely to obtain a green result.

## Tests

For every language feature, maintain traceability between:

documented requirement → grammar rule → positive fixture → relevant negative or recovery fixture.

When changing a grammar rule:

1. update or add the smallest specification-derived tests;
2. regenerate parser artifacts;
3. run the closest corpus and conformance tests;
4. run query checks if node shape changed;
5. run incremental tests when parsing boundaries or ambiguity changed;
6. widen to native-oracle and downstream integration gates when required by the change's blast radius.

A change that intentionally alters public node shape must update `docs/specs/tree-schema.md` and relevant queries.

## go-treesitter integration

The integration boundary is the generated Tree-sitter grammar, not a cgo Go binding.

Do not change this repository's grammar design merely to hide a defect in `go-treesitter`.

First establish correct native Tree-sitter behavior. Then compare the same grammar identity through the downstream Go runtime.

A downstream mismatch is an integration/runtime issue until evidence establishes that the grammar itself is wrong.

## Git

`main` contains reviewed and verified work.

Perform implementation work on a scoped session or feature branch.

Use one verified work unit per commit. Do not mix unrelated grammar, documentation, and tooling changes unless they form one inseparable contract change.

Record relevant validation in the commit body when practical.

Do not rewrite unrelated history or discard user work.

Do not push, tag, publish packages, create releases, or perform other remote writes unless the current task explicitly authorizes them.

## Session naming

Use:

`YYYY-MM-DD-session-NN-<topic>-<artifact>.md`

Use lowercase kebab-case.

Examples:

`2026-09-23-session-01-tree-sitter-brightscript-foundation-architecture-prompt.md`

`2026-09-23-session-01-tree-sitter-brightscript-foundation-architecture-plan.md`

`2026-09-23-session-01-tree-sitter-brightscript-foundation-architecture-handoff.md`

Do not add session/date prefixes to canonical specifications or ADRs merely because they were created during a session.

## Completion

Complete the authorized lifecycle:

research → requirement traceability → implementation → generation → focused validation → regression validation → review → canonical documentation update → scoped commit → handoff → explicit verdict.

Do not report a syntax feature as supported until its required evidence exists.

If a blocker is external or the language specification is genuinely ambiguous, preserve that state explicitly instead of guessing.