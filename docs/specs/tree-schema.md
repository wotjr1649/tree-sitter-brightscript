# Tree schema

The parse tree is this repository's public interface: queries, editors and
downstream runtimes depend on node types and field names. This document holds
the stability policy and naming rules now, and the node catalogue once the
grammar exists.

## Tiers

| Tier | Contents | Stability |
|---|---|---|
| Public | Named node types for declarations, statements, expressions, literals, comments and conditional-compilation constructs; their field names; supertypes; every node referenced by a shipped query | Deliberately designed; changes classified below |
| Internal | Hidden rules (`_name`), anonymous tokens, helper nodes not listed in the catalogue | May change freely before 1.0 |

A node becomes public when it is added to the catalogue below.

## Naming and shape rules

- Node types and fields use `snake_case`, named for the BrightScript construct,
  not for a downstream use (no code-graph or editor-specific names).
- Names are chosen independently; they are not taken from the legacy grammar
  or from BrighterScript's AST.
- Every construct a consumer needs to find is a named node; its semantically
  distinct children are reachable by field name rather than position.
- Equivalent spellings (letter case, `END IF` vs `ENDIF`, `?` vs `PRINT`)
  produce the same node types. Whether the original spelling is recoverable
  from anonymous tokens is decided per construct and recorded here.
- Categories that consumers match as a group (statements, expressions) are
  expressed as supertypes where that keeps queries simple.
- Error-recovery trees are not part of the schema.

## Compatibility and versioning

The grammar version in `tree-sitter.json` is embedded in generated
`parser.c`, so a version bump is a regeneration
([ADR-0002](../design/decisions/ADR-0002-generator-pin-and-generated-artifacts.md)).

| Change | Before 1.0 | From 1.0 |
|---|---|---|
| Public node type or field removed or renamed; public structure changed incompatibly | MINOR bump, recorded | MAJOR |
| Public node type or field added | MINOR | MINOR |
| Internal change only | PATCH if `node-types.json` is unchanged, otherwise MINOR | MINOR |
| Fix with no node-type or structure change | PATCH | PATCH |

From 1.0 this matches Tree-sitter's
[publishing guidance](https://tree-sitter.github.io/tree-sitter/creating-parsers/6-publishing.html)
(incompatible node-type or structure changes are major; new node types are
minor).

Any change to the public tier updates the catalogue in the same commit, and
the `src/node-types.json` diff is reviewed. Queries that reference changed
nodes are updated in the same commit.

1.0 freezes the public tier; the other 1.0 conditions are the v1.0 gates in
[validation.md](../validation/validation.md).

## Catalogue

Empty until grammar implementation begins.
