# Grammar contract

What the grammar promises, as policy. Individual language requirements live
in [language-conformance.md](language-conformance.md); tree shape policy in
[tree-schema.md](tree-schema.md); validation levels and gates in
[validation.md](../validation/validation.md).

## 1. Scope

**Requirement.** The grammar parses BrightScript source files (`.brs`) as
defined by Roku's official documentation. It is a syntax parser only.

**Evidence.** Level 1 pages listed in
[upstream-sources.md](../provenance/upstream-sources.md);
[ADR-0001](../design/decisions/ADR-0001-specification-authority-and-independent-implementation.md).

**Enforcement.** Every rule traces to a `BS-*` requirement.

## 2. Language version

**Requirement.** One grammar accepts the currently documented language, a
superset of all Roku OS versions. Version availability is recorded per
requirement (`since`), not selected at parse time. Where documentation changed
the meaning of existing text, the current meaning is parsed and the older one
is recorded as a known incompatibility.

**Evidence.** [ADR-0003](../design/decisions/ADR-0003-current-language-superset-grammar.md).

**Enforcement.** `since` field in each requirement record.

## 3. Acceptance policy

**Requirement.**

1. Every syntactic form documented at Level 1 (status `documented`) must parse
   without `ERROR` or `MISSING` nodes. The only exception is a disclosed known
   limitation (`KL-NNN`, see validation), which never counts as coverage.
2. A form is asserted invalid (negative fixture) only when Level 1 or Level 2
   evidence states that it is invalid or unsupported.
3. An undocumented variant may be accepted only as `tolerated`: it needs
   Level 2 evidence, or Level 4 evidence showing the variant accepted as plain
   BrightScript (BrighterScript-only extensions never qualify); it must not
   change the tree of any documented form, and is recorded in the registry.
4. A form with neither kind of evidence is `unresolved`: the grammar makes no
   contractual claim about it either way.
5. A grammar choice made for an ambiguity that needs Level 2 evidence is
   `provisional` and is disclosed as such.
6. Semantic rules never become grammar rules. Examples: meaning of `m`,
   default-parameter ordering, label placement between `TRY` and `CATCH`,
   undefined conditional-compilation constants, type conversion, runtime
   behaviour of built-in functions.
7. Official code examples are evidence of intended syntax, not automatically
   valid fixtures; each is reviewed before becoming one (some mix source with
   output, transcripts or typos).

**Evidence.** Tree-sitter documentation gives no normative guidance on
strictness, so this is project policy, adopted at the Session 01 checkpoint.

**Enforcement.** Registry statuses; fixture review; validation gates.

## 4. Conditional compilation

**Requirement.** Conditions are never evaluated. All branches are parsed as
BrightScript by default. Bodies of branches whose condition is the literal
`false` become opaque text only if the scanner-free approach passes the
acceptance criteria in
[ADR-0004](../design/decisions/ADR-0004-conditional-compilation-representation.md);
otherwise the documented block-comment idiom is a named known limitation.

## 5. Lexical mechanism

**Requirement.** No external scanner unless
[ADR-0005](../design/decisions/ADR-0005-external-scanner-policy.md) is satisfied
by a new, accepted ADR.

## 6. Invalid input and recovery

**Requirement.** Invalid input yields `ERROR` or `MISSING` nodes rather than a
failed parse. The exact shape of error-recovery trees is not part of the
public contract unless a requirement states otherwise, because recovery
differs between Tree-sitter runtime versions.

## 7. Line endings and encoding

**Requirement.** Accepted line terminators, end-of-file handling and source
encoding are open questions to be recorded as requirements with their
evidence status. Fixtures whose bytes matter are stored so that Git does not
normalize them (see validation).

## Non-goals

- Semantic validation, name or type resolution, Roku API or SceneGraph
  knowledge, and code-graph construction.
- Parsing SceneGraph XML or the app manifest (`bs_const`).
- BrighterScript-only syntax.
- Checking compatibility with a particular Roku OS version.
- Evaluating conditional-compilation conditions.
- Rejecting every program that the Roku compiler would reject.
