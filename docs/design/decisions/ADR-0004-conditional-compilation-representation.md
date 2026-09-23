# ADR-0004 — Conditional compilation representation

Status: Accepted (literal-`false` opaque bodies pending a feasibility spike)
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

## Validation / enforcement

- Spike acceptance criteria above, recorded with fixtures and V5 results.
- Fixtures for nested blocks, `#error`, and the documented block-comment
  examples (positive if the target succeeds; `KL-*` otherwise).

## Revisit conditions

- The spike result.
- Roku documents richer condition syntax (for example `not`), or changes how
  inactive regions are compiled.
