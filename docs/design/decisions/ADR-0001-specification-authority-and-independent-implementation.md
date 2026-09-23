# ADR-0001 — Specification authority and independent implementation

Status: Accepted
Date: 2026-09-23

## Context

The existing community grammar, `ajdelcimmuto/tree-sitter-brightscript`, omits
officially documented syntax (for example `:` statement separators, labels,
`DIM`, hexadecimal and suffixed numeric literals, type designators), disagrees
with the official operator precedence table, has no negative tests, shipped
generated artifacts that did not match its grammar, and declares conflicting
licenses. BrighterScript is well maintained but parses a superset language.
`go-treesitter` consumes whatever grammar it pins and cannot define syntax.

A grammar derived from any of these would inherit their defects and their
licensing, and could not show why any rule exists.

## Decision

1. Language syntax authority follows the levels in
   [source-policy.md](../../provenance/source-policy.md): Roku official
   documentation (Level 1), reproducible official Roku behaviour (Level 2),
   official Tree-sitter for grammar mechanics only (Level 3), comparative
   community tools (Level 4), legacy Tree-sitter grammars (Level 5).
   Downstream consumers have no authority over syntax.
2. A lower level never silently overrides a higher one; disagreements and
   ambiguities are recorded, not resolved by majority or by guessing.
3. The grammar is an independent implementation. Levels 4–5 may be inspected
   for edge cases, defects and differential tests, but no grammar rules,
   generated code, queries, tests, bindings, documentation wording or
   parse-tree design are copied from them.
4. Every grammar rule and fixture traces to a requirement ID whose evidence is
   Level 1 or Level 2.

## Alternatives considered

- **Fork the legacy grammar and patch it** — rejected: inherits missing syntax,
  wrong precedence, drift history and a license conflict, with no traceability.
- **Adopt BrighterScript's grammar as the specification** — rejected: it is a
  superset language and a non-normative implementation.
- **Treat downstream behaviour as the specification** — rejected: a consumer
  cannot define the language it consumes.

## Consequences

- Initial progress is slower; each feature needs a Level 1 citation first.
- Where Level 1 is ambiguous and no Level 2 evidence exists, the requirement is
  marked `provisional` or `unresolved` instead of silently choosing.
- The project owns its tree design and must document it
  (`docs/specs/tree-schema.md`).

## Validation / enforcement

- Requirement records cite evidence (`docs/specs/language-conformance.md`).
- Review rejects grammar rules or fixtures without a requirement ID.
- `_ref/` is Git-ignored; commits are checked for staged `_ref/` content.

## Revisit conditions

- Roku publishes a formal grammar or an official off-device compiler.
- The project is asked to track a different language authority.
