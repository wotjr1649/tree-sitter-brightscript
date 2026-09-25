# Session 05-4: grammar and schema redesign on the stock runtime

**Status (2026-09-25): 0.1.0 is not released and stays on hold**
(`HOLD_FOR_RELEASE_REMEDIATION`, [0.1.0-release.md](0.1.0-release.md#status-hold)).
This session asked whether a new grammar and public tree, on the unmodified
Tree-sitter 0.27.0 runtime, can meet the seven open blocking findings and the
existing contract together. It tried a bounded set of redesigns in isolated
experiments. No candidate passed the early joint screen, so none was proposed
for adoption: `grammar.js`, the generated files, the public schema, the query,
the pins and every contract are unchanged. All seven findings stay open.

## Baseline

| Item | Value |
|---|---|
| Input | `07c421a8…` (tree `88080078…`) on `session/05-3-repository-owned-hardening`; `main` `2aeb29dc…` untouched |
| Parser | `src/parser.c` `2711f7cc…`, `node-types.json` `dfa5bfce…`, `queries/highlights.scm` `55543bfd…` |
| Runtime | stock 0.27.0 (`6070dbfefd32…`, every `lib/` file equal to the tag), linked statically into small C harnesses |
| Generator | pinned CLI 0.27.0 (windows-x64 `9fbc4f28…`), ABI 15, through `scripts/tscli.py` |
| Platform | Windows 11 x64, gcc 16.2.0 `-O2`, default 2 MiB stack; every native run in the Job-object supervisor (512 MiB commit, 15 s, 8 MiB output), one at a time |

Evidence levels: syntax preservation V3/V4 (projection, direct assertions,
roles), repair V5, scaling and resources V10; runtime and query-cursor
behaviour is read from the 0.27.0 source (L3). Local evidence:
`artifacts/session-05-4-grammar-schema-stock-runtime/` (not tracked).

## Method

- The owner-approved stricter checks of Session 07 (R8 `protocol-v3`) and a
  session protocol were fixed before any candidate was timed. No bound was
  relaxed; the KL-002 policy question deferred in Session 05-3 stays deferred.
- Syntax preservation was checked without requiring equal raw trees. Each tree
  is projected into records of prefix and binary operators, ordered postfix
  operations, parentheses, PRINT items and separators, assignments and updates,
  with byte spans; unknown node types, `ERROR` and `MISSING` nodes are kept or
  fail. The projection reads grouping only from the tree. It rejected 16
  deliberately wrong trees (swapped operands, `a^(b^c)` → `(a^b)^c`, moved
  `?.`, `(a.b)(1)` ↔ `a.b(1)`, merged PRINT items, dropped separators, byte
  vs character offsets, dropped `ERROR`/`MISSING`, unknown nodes, truncated
  output) and accepted three trees that carry the same information in another
  shape. Its first two versions missed dropped `MISSING` and `ERROR` nodes; both
  defects were fixed before any candidate was compared.
- Inputs: the 228 corpus fixtures, the highlight fixtures and samples, the
  2,811 recovery-comparison inputs of Session 05-2, 26 new probes, 79 direct
  assertions written from the precedence table of
  [grammar-design.md](../specs/grammar-design.md) §5 and the registry, and 300
  held-out programs generated after the screen (seed 5401).
- Highlight roles were compared as native captures, `tree-sitter query -c`
  captures and final `highlight --html` roles; the comparison detected five
  deliberately broken queries.

## Hypotheses

At most two per axis were allowed; all but PF2 were registered before
measurement (PF2 is noted below). Historical variants
(whole-list `repeat()`, right or left lists, hidden wrappers, query-only
rewrites, a naive flat prefix rule, runtime patches) were not repeated.

| Id | Axis | Change | Result on its own |
|---|---|---|---|
| PX1 | prefix | A run of `-`/`+` is one `unary_expression` with several `operator` fields; its operand cannot start another sign run (`not` unchanged, mixed runs stay nested) | Syntax preserved (after one implementation fix, r1). `x = +*`×1,000: 470 ms → 6.4 ms; `-f(-)` memory halved but still quadratic; `+f([)` unchanged |
| PX2 | prefix | The same for `not` | Not built: no required check depends on it |
| PR1 | PRINT | Separators split the items into segments held by `repeat()`; only juxtaposed items form a right-recursive run (no public change) | `print a;`×4,000: field access 195 → 1.1 ms, query 482 → 5.3 ms; but `print ,+*`×4,000 memory 13 → 202 MiB (the B4-02 regression) |
| PF1 | postfix | A called member access is one `call_expression` (`object`, `.`/`?.`, `property`, `arguments`), so the method name and its argument list are siblings; the query marks a method as `(["." "?."] . (identifier) @function . (argument_list))` | Rejected: still quadratic, because the plain-call patterns `(call_expression function: …)` wait through the object of every method call |
| PF2 | postfix | PF1 with the plain-call patterns anchored to the first child (`(call_expression . function: …)`) | Method chains of 8,000 links: 2,582 ms → 19.5 ms; mixed 4,122 → 25 ms. First recorded as a revision of PF1 and reclassified after review, since it changes the mechanism |
| C1 | all | PX1 + PR1 + PF2 | Below |

## The integrated candidate C1

Syntax: all 1,570 valid inputs give the same projection, byte spans and
tokens as the release parser; 300 of 300 held-out programs; 79 of 79 direct
assertions; the same accept/reject result on every fixture. Highlighting: the
same native captures, predicate captures and final roles on all valid inputs;
26 inputs with errors change roles (16 runs inside `ERROR` nodes, 10 outside).
In an isolated copy these checks of the repository pass: regeneration, W10
incremental edits, the conditional-compilation spike, the six recovery and two
query scaling guards, and W11 (40 + 98 + 21 assertions, run with the 12
fixtures below excluded). The corpus passes 216 of 228: the 12 others contain
method calls or runs of signs and still expect the current tree. W13 fails for
the same reason (the fuzz run first compares with the expected tree), so the
new node shapes were not fuzzed. The stricter check of the public tree (corpus
228/228 and the current `node-types.json`) therefore holds only after an
approved migration. Parse time of valid 1 MiB inputs is 1.01–1.05 × the
release parser; scattered errors in a 98 KB program cost the same.

The same build against the stricter checks (worst value; the release parser
in brackets, measured in this session unless marked R8, the Session 07
records, or 0.1.0-performance.md):

| Finding | C1 result | Check |
|---|---|---|
| KL-002 prefix family | `x = +*`×8,000 in 53 ms (22.9 s, 0.1.0-performance.md); guard exponent 0.91 (about 2.0 in earlier CI runs) | improved |
| S07-M03 valid chains | method, mixed and statement chains of 16,000 links in 37–44 ms, linear (8,000 links: 2.1–4.1 s) | pass |
| S07-M03 flat `ERROR` | `try`⏎, `(`, `[` ×20,000: 324–784 ms, exponent 2.0–2.1; `-(-[`: 8.8 s (4.2 s) | fail |
| A5-01 | `print a;`×32,000: query 42.7 ms, growth linear (quadratic before), but 1.3–2.5 × the parser before `79d565b` at several sizes (bound 1.5 ×); juxtaposed `print a a …`×8,000: 451 ms (4.2 ms), exponent 1.9–2.7 | fail |
| B5-02 | `print ,+*`×20,000 completes (stack overflow); `print f([)` and `x = -f(-)` ×20,000 overflow the stack | fail |
| B5-01 | `+f([)`×800: 512 MiB cap (cap, R8); `-f(-)`×800: 237 MiB (cap, R8); `{a:@*}<`×600: 130 MiB (130 MiB, R8) | fail |
| S07-M01 | cancellation returns up to 621 ms late, and three cancelled runs hit the memory cap or overflow the stack; callback gaps of 112–829 ms on six inputs, ten more not measurable (cap or crash) (R8: 160 ms late, 544 ms gap) | fail |
| S07-M02 | 7 of 11 malformed 1 MiB families reach the 512 MiB cap (8, R8); `print ,+*` completes at 180 MiB | fail |
| S08-M01 | valid 1 MiB PRINT: 269 MiB (348); deletion 98–101 ms in three alternating runs (up to 110), 157 ms in one run during host slowdown | fail |

C1 is therefore not a qualifying candidate, and no second integrated design
was built: every remaining failure lies outside the three axes.

- Flat `ERROR` nodes: for each node the query cursor scans later siblings until
  a named one (`ts_tree_cursor_current_status`, runtime 0.27.0). Recovery of
  unclosed brackets or `try` leaves one `ERROR` node whose children after the
  first are all anonymous tokens (the same shape on both parsers), so the scan
  is quadratic whatever the pattern: on C1 a query with the single pattern
  `(identifier) @variable` has exponent 1.89–2.11 on five such families. None
  of the three axes changes that shape.
- Unclosed calls, arrays and associative arrays after malformed items keep
  equal-cost recovery paths that the runtime copies at end of input without a
  progress callback (B5-01, S07-M01, S07-M02).
- Juxtaposed PRINT items are documented (BS-STMT-025). A malformed run of them
  has two equal-cost readings whose merged stack the runtime releases
  recursively (B5-02); making the run a `repeat()` removes A5-01 there but
  revives the B4-01 memory growth.
- A valid PRINT of a million items needs about 270 MiB for its tree alone.

What remains useful for a later decision: on the stock runtime a flat sign
run makes the KL-002 prefix family linear (then its witness meets the stricter
gap, cleanup and memory checks directly), a method-call node makes method
chains linear in the query, and the two-level PRINT list makes
separator-delimited PRINT statements grow linearly without changing the public
tree, though more slowly than the parser before `79d565b`. PX1 and PF2 change
the public tree and would need an owner decision and fixture migration; none
of the three closes a finding on its own.

## Findings

| Finding | This session | Release impact |
|---|---|---|
| B5-01 | reproduced; minus family halved on C1 | blocking |
| B5-02 | `print ,+*` family fixed on C1 (not adopted); call family and families outside PRINT still overflow | blocking |
| A5-01 | separated items grow linearly on C1 (not adopted) but miss the time bound; juxtaposed items still quadratic | blocking |
| S07-M01 | reproduced | blocking |
| S07-M02 | reproduced; one family improved on C1 | blocking |
| S07-M03 | method and mixed chains linear on C1 (not adopted); flat `ERROR` remains | blocking |
| S08-M01 | 348 → 269 MiB on C1, still above 256 MiB | blocking |

## Measurement notes

- The timing host was noisy during parts of the session; comparisons were
  therefore made against the release parser (and, for A5-01, against the
  parser before `79d565b`) measured in the same batch, and no bound was
  changed.
- Departures from the session protocol, all disclosed in the local evidence:
  some points were first measured three times and then completed to five; the
  held-out set used 300 random programs and scattered errors instead of the
  registered three-unit combinations, which were not run; PF2 was reclassified
  after its measurement; the cancellation budgets of the 1 MiB set were not
  run.
- Seven tool defects were found and fixed during the session (a duplicated run
  identifier, a missing query identity in run identifiers, relative paths and
  a watchdog in the role harness, a mismatched query mutant, a verdict script
  that mixed cancelled runs into a median, and the two comparator defects
  above); the affected runs are kept and marked in the local evidence. No run
  key that ended at a memory cap, watchdog or crash was repeated.

## Validation

Candidates were generated twice with the pinned generator (byte-identical, no
`conflicts` added) and measured on the stock runtime only. Run: semantic
projection and direct assertions (V3), role comparison (V4), W10 in an
isolated copy (V5), the stricter checks and W06–W08/W13 in an isolated copy
(V10). Not run: fixture migration, W12, a Level 1 refresh, a fresh clone and
hosted CI for any candidate (no candidate was adopted), V7–V9. The report
itself is covered by `scripts/check_v0.py`. A review in a separate context of
the same model re-derived the verdicts from the raw measurements and agreed
with them; it found one material overstatement (A5-01 for separated items)
and six minor ones, all corrected above.
