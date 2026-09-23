# ADR-0004 — Conditional compilation representation

Status: Accepted; literal-`false` opaque bodies adopted (V1), spike passed 2026-09-23
Date: 2026-09-23

## Context

BrightScript has `#const`, `#if`, `#else if`, `#else`, `#end if` and `#error`.
Constant values come from `#const` lines and from the app manifest
(`bs_const`), which a parser cannot see; since Roku OS 16.0 undefined
constants evaluate to `false`. Roku's documentation presents `#if false … #end
if` as a way to write block comments containing plain prose, and also wraps
whole function declarations in conditional blocks.

Precedent (observed 2026-09-23): tree-sitter-c, -cpp, -c-sharp, a Pascal
grammar and a Swift grammar parse every branch as ordinary code, mostly
without an external scanner. tree-sitter-haskell consumes inactive branches
as opaque text using an external scanner. No scanner-free grammar was found
that treats `#if false` / `#if 0` bodies as opaque. Identities:
[upstream-sources.md](../../provenance/upstream-sources.md#precedents-and-references-cited-by-decisions).

## Decision

1. Conditions are never evaluated.
2. Baseline: every branch is parsed as ordinary BrightScript inside a
   conditional-compilation construct.
3. Target: the body of a branch whose condition is the literal `false`
   becomes opaque text. This is adopted only if a scanner-free implementation
   passes all of:
   - case-insensitive recognition that does not mis-tokenize identifiers such
     as `falsey`, with and without a trailing comment;
   - correct `#else if`, `#else` and `#end if` recognition inside the body;
   - nested conditional blocks balanced by the parser;
   - error recovery that does not swallow text outside the region;
   - incremental-parse equality for edits inside, around and across the region.
   The same spike may extend the rule to the `#else` branch of a literal
   `true` condition.
4. If the spike fails, the baseline stays and the documented block-comment
   idiom becomes a named known limitation (valid source producing `ERROR`).
5. A branch whose condition is a name (`#if DEBUG`) is always parsed as code,
   even if a visible `#const` sets it to `false`.
6. An external scanner for this purpose requires a new ADR under
   [ADR-0005](ADR-0005-external-scanner-policy.md).

## Alternatives considered

- **All conditional bodies opaque** — rejected: loses the structure of
  functions and statements inside every conditional block.
- **External scanner that tracks `#const`** — rejected: still blind to
  manifest constants, needs incremental scanner state and a downstream port.
- **Baseline only** — kept as the fallback; it leaves the documented idiom
  producing errors.

## Consequences

- Code split across branch boundaries (a statement begun in `#if` and
  finished in `#else`) may produce `ERROR`, as in other grammars.
- Queries and tools see both branches of evaluated-at-build-time conditions.
- The public tree must include the conditional construct and, if the target
  succeeds, an opaque-body node.

## Spike specification

Added 2026-09-23 (Session 02); it refines, and does not change, the decision.
Inputs, expected trees, the planned scanner-free
designs to try (V1, then V2) and both outcomes are fixed in
[grammar-design.md §11](../../specs/grammar-design.md#11-conditional-compilation).
The optional extension to the `#else` branch of a literal `true` condition is
not attempted. The spike result updates this ADR's status line; the failure
path activates known limitation KL-001 in
[validation.md](../../validation/validation.md).

## Spike result

2026-09-23 (Session 03, WP15), generator tree-sitter 0.27.0, ABI 15: design
V1 qualified at its first attempt, so V2 was not tried. Evidence:

| Criterion | Evidence | Result |
|---|---|---|
| C1 | fixtures S3, S4, S5, S12 | pass |
| C2 | fixtures `block comment with prose`, S6, S7, S11 | pass |
| C3 | fixture S8 | pass |
| C4 | `scripts/check_spike.py`: in R1 and R2 the only `ERROR` lies in the malformed line and every later node matches the repaired parse; R3 has an error and no crash | pass |
| C5 | `scripts/check_incremental.py` E1–E6: the final `parse --edits` tree equals a fresh parse (default and CST output) | pass |

All fifteen literal-false fixtures take their PASS (V1) expectation; every
baseline COND fixture still passes; no `conflicts` entry and no external
scanner. `inactive_text` is public, E1–E6 stay in workload W10, and KL-001
is retired unused.

Review correction (Session 03, same day; refines the design, not the
decision): the independent review found that C1 had tested only `falsey`, and
that a region line beginning with a longer word such as `#ifdef` lexed as the
directive `#if`, opening a nested block that swallowed the rest of the file.
Such lines are now hidden text (grammar-design §11, "Directive-like lines";
fixture `BS-COND-007: directive-like words inside a false region`), and the C4
check now also compares the nodes before the malformed line and each node's
has-error mark. C1–C5 pass again with the corrected design.

## Validation / enforcement

- Spike acceptance criteria above, recorded with fixtures and V5 results.
- Fixtures for nested blocks, `#error`, and the documented block-comment
  examples (positive if the target succeeds; `KL-*` otherwise).

## Revisit conditions

- The spike result.
- Roku documents richer condition syntax (for example `not`), or changes how
  inactive regions are compiled.
