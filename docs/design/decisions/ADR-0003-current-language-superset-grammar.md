# ADR-0003 — Current-language superset grammar

Status: Accepted
Date: 2026-09-23

## Context

Roku added syntax across OS releases, for example integer division `\` and
bit shifts (6.1), doubled-quote escapes (6.2), string keys in associative-array
literals and `&` LongInteger (7.0), `++`/`--` and compound assignment (7.1),
`TRY`/`CATCH`/`THROW` (9.4), optional chaining `?.` `?@` `?[` `?(` (11.0) and
`CONTINUE FOR`/`CONTINUE WHILE` (11.5). Some changes altered the meaning of
existing text: pre-9.4 code could use `try`/`catch` as names, and `IF x?("…")`
no longer prints.

A Tree-sitter language has no runtime parameter for dialects. Mainstream
grammars (for example tree-sitter-c-sharp for C# 1–14 and tree-sitter-python
with both Python 2 and 3 statements) use one superset grammar; no
version-variant grammar was found.

## Decision

1. One grammar accepts the currently documented BrightScript language.
2. Each requirement records its Roku OS availability in a `since` field
   (`baseline` when no version is documented, `unknown` when unclear).
3. Where documentation changed the meaning of existing text, the grammar
   follows the current documentation, and the requirement records the older
   meaning as a known incompatibility.
4. Checking code against a target Roku OS version is not part of this
   repository; a consumer can build it from the `since` data.

## Alternatives considered

- **Version-selectable modes** — rejected: would need one generated grammar per
  version, multiplied tests and multiple downstream artifacts, with no
  precedent.
- **Superset plus an in-repository compatibility checker** — rejected for this
  repository: version checking is semantic analysis beyond the syntax-only
  scope.

## Consequences

- Code valid only on old firmware may parse differently or with errors; the
  affected requirements say so.
- Syntax newer than a device's OS parses cleanly; the grammar does not warn.

## Validation / enforcement

- `since` is a required field in `docs/specs/language-conformance.md`.
- Fixtures cover current behaviour; known incompatibilities are noted per
  requirement.

## Revisit conditions

- A consumer demonstrates a concrete need for version-specific parse trees.
- Roku removes or reinterprets syntax in a way a superset cannot express.
