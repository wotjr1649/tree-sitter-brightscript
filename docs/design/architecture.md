# Architecture

## Purpose

This repository produces an independently written Tree-sitter grammar for
Roku BrightScript, its generated parser artifacts, syntax queries, and the
evidence that ties each grammar rule to official Roku documentation.

## Pipeline

```text
Roku documentation (Level 1) ──► requirement registry (BS-*)
        │                                   │
        └── local snapshot + identities     ▼
                                        grammar.js
                                            │  pinned `tree-sitter generate`, ABI 15
                                            ▼
                                  src/parser.c, grammar.json,
                                  node-types.json, tree_sitter/*
                                            │
                     V0–V6, V10 validation ─┤
                                            ▼
                              release identity (commit, generator,
                              ABI, file hashes, snapshot ID)
                                            │
             ┌──────────────────────────────┴───────────────────────┐
             ▼                                                      ▼
   go-treesitter (ts2go, own V9 evidence)            editors and other consumers
                                                     (src/ plus their own queries)
```

## Ownership

Owned here: BrightScript lexical and syntactic grammar; the public parse-tree
shape; generated parser artifacts; syntax queries; requirement traceability;
conformance and regression fixtures; provenance and release evidence.

Not owned: Roku runtime and SceneGraph semantics; name and type resolution;
Roku OS compatibility checking; code graphs; application policy;
`go-treesitter`'s runtime, conversion tooling and integration evidence.

## Repository layout

Present now:

```text
LICENSE  README.md  AGENTS.md  .gitignore  .gitattributes
package.json  package-lock.json   private; exact tree-sitter-cli pin
tree-sitter.json                  grammar metadata; all bindings disabled
grammar.js                        canonical grammar source
src/                              generated parser artifacts (never hand-edited)
test/corpus/                      requirement fixtures (bytes/ is byte-exact)
test/samples/                     composite programs (workload W03)
queries/highlights.scm            highlighting query (workload W11)
test/highlight/                   highlight assertions
scripts/                          V0, drift, registry, schema and workload checks
.github/workflows/ci.yml          hosted CI (Windows, Ubuntu)
docs/README.md  docs/roadmap.md
docs/specs/        grammar-contract, language-conformance, grammar-design, tree-schema
docs/design/       architecture, decisions/ (ADRs)
docs/provenance/   source-policy, upstream-sources
docs/validation/   validation, workload-matrix, known-regressions
```

Added only when justified: language bindings or WASM artifacts (per consumer
demand), `queries/tags.scm` (before 1.0) and other queries, fuzzing tools
beyond `tree-sitter fuzz`, further validation and report documents.

Local only and Git-ignored: `_ref/` (reference evidence), `docs/prompts/`,
`docs/plans/`, `artifacts/` (validation output, handoffs), `.work/`.

## Artifact scope

- No language bindings initially. Editors consume `src/` and maintain their
  own queries; `go-treesitter` converts `src/parser.c`
  ([ADR-0006](decisions/ADR-0006-downstream-integration-boundary.md)).
  A binding is added only for a named consumer or registry.
- `queries/highlights.scm` is release-critical from the first release;
  `queries/tags.scm` is targeted before 1.0; folds, indents, locals,
  textobjects and injections are optional.

## Session model

Work happens in bounded sessions:
prompt → plan → implementation → validation evidence → canonical promotion →
handoff. Prompts, plans, evidence and handoffs are local material, never
requirements. Anything that changes the durable contract is promoted into
`docs/` in the same work unit. A new session starts from `AGENTS.md`,
[docs/README.md](../README.md), Git state and the latest handoff.

## Design principles

- **Specification-driven**: requirements come from Level 1 evidence and carry
  IDs before grammar work cites them.
- **Generated-source boundary**: `grammar.js` is the source; `src/` is output,
  reproducible byte for byte with the pinned generator.
- **Producer/consumer separation**: this repository publishes identities;
  consumers integrate and validate on their side.
- **Layered evidence**: V0–V10 are distinct claims; none substitutes for
  another.
- **Contract-first tree**: public nodes and fields are designed and versioned
  deliberately.
- **Identity binding**: every result names the exact grammar identity it
  applies to.
- **Ratcheting regression corpus**: failures become named cases; tests are
  never deleted to pass.

Anti-patterns: patching a copied legacy grammar; tests derived from the
implementation instead of the documentation; editing generated files;
changing the grammar to hide a downstream defect; community consensus
overriding Roku documentation; session prompts becoming policy; one large
README holding every contract.

## Decision index

| Topic | Where |
|---|---|
| Source authority, independent implementation | [ADR-0001](decisions/ADR-0001-specification-authority-and-independent-implementation.md), [source-policy.md](../provenance/source-policy.md) |
| Generator pin, generated artifacts | [ADR-0002](decisions/ADR-0002-generator-pin-and-generated-artifacts.md) |
| Language versions | [ADR-0003](decisions/ADR-0003-current-language-superset-grammar.md) |
| Conditional compilation | [ADR-0004](decisions/ADR-0004-conditional-compilation-representation.md) |
| External scanner | [ADR-0005](decisions/ADR-0005-external-scanner-policy.md) |
| Downstream boundary | [ADR-0006](decisions/ADR-0006-downstream-integration-boundary.md) |
| Acceptance policy | [grammar-contract.md](../specs/grammar-contract.md) |
| Line model, tokens, reserved words, precedence, statement boundaries, implementation order | [grammar-design.md](../specs/grammar-design.md) |
| Tree stability, versioning | [tree-schema.md](../specs/tree-schema.md) |
| Validation gates, Level 2 policy | [validation.md](../validation/validation.md) |
| Validation workloads, fixture catalogue, known regressions | [workload-matrix.md](../validation/workload-matrix.md), [known-regressions.md](../validation/known-regressions.md) |
| Git workflow | `AGENTS.md` |
