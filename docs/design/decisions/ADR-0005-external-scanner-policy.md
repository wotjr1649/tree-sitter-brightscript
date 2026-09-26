# ADR-0005 — External scanner policy

Status: Accepted; superseded in part by
[ADR-0008](ADR-0008-error-recovery-scanner.md) (2026-09-26) for a scanner whose
purpose is the resource safety of error recovery
Date: 2026-09-23

## Context

An external scanner is C code with its own state that must be serialized for
incremental parsing. `go-treesitter` runs grammars on a pure-Go runtime and
carries grammar scanners as Go code (its ADR-0014 at `0f3e720b` refers to
"their Go scanners"; see
[upstream-sources.md](../../provenance/upstream-sources.md#precedents-and-references-cited-by-decisions)),
so a scanner here also implies a port and a parity burden downstream. BrightScript's documented features — case-insensitive keywords
(Tree-sitter supports inline regex flags such as `(?i)`), line-oriented
statements and colon separators — are expected to be expressible with
ordinary grammar rules, but that is not yet demonstrated.

## Decision

No external scanner (`src/scanner.c`) is added unless a new ADR is accepted
first. That ADR must provide:

1. the exact `BS-*` requirements that need it;
2. the scanner-free alternatives tried and evidence of why each failed;
3. the scanner state design, including serialization and deserialization;
4. incremental-parsing tests for edits that cross scanner decisions;
5. native Tree-sitter parity results;
6. an integration analysis for `go-treesitter` (Go port, conversion, parity);
7. fuzzing and error-recovery results.

## Alternatives considered

- **Use a scanner whenever convenient** — rejected: adds C state, incremental
  risk and downstream porting cost without proven need.
- **Forbid scanners permanently** — rejected: a real requirement may prove
  impossible without one.

## Consequences

- Hard lexical cases are solved first with grammar rules, precedence and
  keyword extraction, and documented when they fall short.
- Some documented forms may stay `provisional` or become known limitations
  rather than justify a scanner.

## Validation / enforcement

- Review rejects `src/scanner.c` without an accepted ADR.
- V0 checks can flag a scanner file that has no referencing ADR.

## Revisit conditions

- A requirement is shown to be unrepresentable without a scanner.
