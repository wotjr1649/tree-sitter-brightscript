# Session 05-3: repository-owned query hardening

**Status (2026-09-25): 0.1.0 is not released and stays on hold**
(`HOLD_FOR_RELEASE_REMEDIATION`, [0.1.0-release.md](0.1.0-release.md#status-hold)).
This session changed only what the repository owns: the highlight query, its
tests and checks, a measurement method and fact statements. The grammar, the
generated files, the public schema, the generator and runtime pins and every
other contract are unchanged. Of the seven open blocking findings it fixed
part of one (S07-M03); all seven stay open.

## Baseline

| Item | Value |
|---|---|
| Input | `78fdf766…` (tree `9b5ff47d…`) on `session/05-2-structural-recovery-safety`; product files as in `b75ec4e`; `main` `2aeb29dc…` untouched |
| Parser | `src/parser.c` `2711f7cc…`, `grammar.js` `77cfdd85…`, `node-types.json` `dfa5bfce…` (unchanged) |
| Query before | `queries/highlights.scm` `69853254…` |
| Query after | `55543bfd…` |
| Runtime | stock 0.27.0 (`6070dbfe`), linked statically into a native harness; every copied runtime file equals the tag byte for byte |
| CLI | 0.27.0, windows-x64 `9fbc4f28…`, through `scripts/tscli.py` (private parser library, empty configuration) |
| Platform | Windows 11 x64, gcc 16.2.0 `-O2`; native runs in a Job-object supervisor (512 MiB commit, 15 s, 8 MiB output), one at a time |

Evidence levels: query and role comparisons V4; repair V5; scaling V10.
Runtime and highlighter behaviour is read from the Tree-sitter source at
`v0.27.0` (L3). Local evidence: `artifacts/session-05-3-repository-owned-hardening/`
(not tracked).

## Query change

The member and attribute patterns waited in every `member_expression` and
`attribute_expression` for the property or attribute field. On a left-deep
chain one query state per ancestor stayed alive, so the query took time
quadratic in the chain length. They now match the operator and the name as
siblings:

```scheme
(["." "?."] . (identifier) @property)
(["@" "?@"] . (identifier) @attribute)
```

Pattern count, capture names and predicates are unchanged.

### Roles

Both queries ran on the same parser, runtime and inputs, with every capture
consumed and no match limit, range, start depth or cancellation set.

| Comparison | Inputs | Valid inputs that differ | Inputs with errors that differ |
|---|---|---|---|
| Native captures, in order and as a multiset (no predicates) | 3,153 run, 3,152 completed (1,634 valid) | 0 | 78 of 1,518 |
| `tree-sitter query -c` (predicates applied) | 3,185 | 0 | 78 |
| `tree-sitter highlight --html` final roles, aligned to the input bytes | 3,185 | 0 | 78 |
| Repair: 34 edit scripts (W10 I01–I12 and E1–E6, earlier recovery edits, 6 new) | 34 | 0 of 34 repaired states | 3 edited states |

The inputs are the corpus, the highlight fixtures and samples, 2,811
recovery-comparison inputs of Session 05-2, and new small cases of member,
attribute, call, mixed and optional chains, comments, line ends, predicates,
`ERROR` and `MISSING` nodes and UTF-8. Valid chains up to 16,000 links give
identical ordered captures and identical HTML. One native run, a valid
500-link mixed chain, hit the watchdog because the harness looks up each
capture's parent, which costs time in the chain depth; its ordered captures
and its HTML match the old query's in the timing and CLI runs. One repaired
state keeps the errors of its base. In one edited state
(`PRINT-middle-error`) the incremental tree differs from a fresh parse, as
recorded before; the captures are the same.

On the 78 inputs with errors the final roles change in four ways:

| Change | Runs | Where |
|---|---|---|
| variable → attribute | 80 | a name right after `@` or `?@` inside an `ERROR` node |
| variable → property | 2 | a name right after `.` inside an `ERROR` node |
| property → variable | 5 | recovery put an `ERROR` between `.` and the name; the name is outside the `ERROR` node |
| attribute → variable | 1 | the same with `@` |

Examples: in `x = a.b.⏎y = c.d` recovery makes `y` the property of the first
line's member expression; the old query colours it as a property, the new
one as a variable. In `printa@b` (all `ERROR`) `b` becomes an attribute. No
role changes at a `MISSING` node. In 43 of the 78 inputs one `ERROR` node
covers at least 90 % of the input. Recovery trees are not contractual
([validation.md](../validation/validation.md) "Fixture rules"). The owner
approved these changes on 2026-09-25 (Gate Q).

### Time

Native, the same work for both queries (every capture hashed), median of 5
runs after a warmup; the old query at 16,000 links ran 3 times.

| Chain (k links) | Before, k = 4,000 | After, k = 4,000 | Exponent over k = 250–4,000 |
|---|---|---|---|
| `x = a` + `.b` | 106.0 ms (k = 16,000: 2,134 ms) | 2.13 ms (k = 16,000: 8.9 ms) | 1.89 → 0.99 (to k = 16,000: 1.98 → 1.00) |
| `x = a` + `@b` | 107.5 ms | 2.08 ms | 1.90 → 1.00 |
| `x = a` + `.b@c` | 437.3 ms | 4.54 ms | 1.97 → 0.99 |
| `a` + `.b` + ` = 1` | 105.8 ms | 2.04 ms | 1.90 → 1.00 |
| `x = a` + `?.b` | 105.7 ms | 2.13 ms | 1.90 → 1.00 |
| `x = a` + `.b(1)[2]` | 821.0 ms | 383.9 ms | 1.98 → 1.91 |
| `x = a` + `.b(1)` | 524.5 ms | 259.6 ms | 1.96 → 1.89 |

Call-only and index-only chains, long PRINT statements (A5-01, still
quadratic) and the samples stay within 1.10 × + 0.5 ms of the old query.
Through the CLI (`query -c --time`, predicates applied) the 16,000-link
member chain takes 2,138 ms before and 9.4 ms after. One machine; no p95
(fewer than 20 samples).

### Not solved: method calls

The method-call pattern `(call_expression function: (member_expression
property: (identifier) @function))` still keeps one state per call ancestor.
Three rewrites were written down before measurement: a last-child anchor
instead of the field, one alternation for both call patterns, and a sibling
group `member_expression . argument_list`. None changed the growth (exponent
1.89–1.91 on method and mixed chains), and the last one also changed 11
method roles in `ERROR` input. The search ended there. As far as the query
cursor source shows (L3; not proven for every query form), a pattern that
decides the method role has to start at the call or member node above the
object, so on the current tree shape it waits while the cursor walks the
object; the remaining options are a grammar or runtime change. The quadratic cursor
scan on a node with many children (flat `ERROR`) does not depend on the
pattern.

## Checks added

- `test/highlight/chains.brs`: 40 assertions of the W11 rows on chains,
  written from the W11 table. Queries that drop `?.` or `?@` from the member or
  attribute pattern pass the older fixtures and fail this one.
- Query scaling guards in `scripts/check_robustness.py`
  ([validation.md](../validation/validation.md) "Query scaling guards"). The
  old query fails both rows (exponent 2.03–2.06, 2.1–2.2 s), the new one
  passes (0.99, 9.4–9.5 ms).
- The comparison method: [validation.md](../validation/validation.md)
  "Highlight query changes". `--query-paths` takes one or more values; an
  input path written after it becomes a query path and the CLI highlights
  empty standard input without an error.

## Measurement notes

- The Session 05-2 records list 72 inputs whose captures differed under the
  private rewrite (71 of the 2,811 recovery-comparison inputs and one malformed
  probe), not 73; the 1,354 valid inputs match. Within that set every
  difference lay inside an `ERROR` node; the new small inputs show the cases
  outside one.
- The KL-002 witness in the Session 07 check set must finish within the
  watchdog to be measured, so it fails the gap, cleanup and memory checks on
  every configuration by construction. Re-read from the Session 07 records,
  every cancelled run of that witness on the current parser returns within
  0.07 ms of its budget, frees tree and parser within 0.81 ms and stays below
  5 MiB. A revision that would judge the witness by cancellation instead was
  proposed; the owner deferred it. The check set and its results are
  unchanged. The proposal would also drop the full-run callback-gap check
  for that witness.
- The message of commit `620475a` gives 1.98 → 1.00 for all five chains;
  the table above has the values per chain and range.

## Findings

| Finding | Observation | Owner | This session | Release impact |
|---|---|---|---|---|
| B5-01 | end-of-input path copies grow quadratically in memory | grammar and runtime | frozen | blocking |
| B5-02 | recursive stack release overflows near 20,000 repetitions | grammar and runtime | frozen | blocking |
| A5-01 | right-recursive PRINT items make query and index access quadratic | grammar change `79d565b` | frozen (a grammar change is outside this session); not made worse | blocking |
| S07-M01 | runtime steps without a progress callback | runtime | frozen | blocking |
| S07-M02 | large-input memory | grammar and runtime | frozen | blocking |
| S07-M03 | quadratic highlight query | query and runtime | member and attribute chains fixed; method chains and flat `ERROR` open | blocking |
| S08-M01 | valid 1 MiB PRINT: 348 MiB, deletion 109–127 ms | grammar and runtime | frozen | blocking |

## Validation

Local, Windows, on the tree of `620475a`: `check_v0`, `check_generated`, `test_tscli`,
`check_registry --complete`, `check_schema`, `tscli test` (corpus 228/228;
highlight 40 + 98 + 21), `check_samples`, `check_spellings`,
`check_robustness` (fuzz 1,000 × 10, seed 1; recovery and query guards),
`check_incremental`, `check_spike`: all pass. The comparators, the HTML
alignment, the repair comparator and the query guard were each checked
against deliberately wrong results. Two reviews in separate contexts of the
same model (query semantics; scope, protocol and hold) found nothing that
blocks the change; their minor findings are corrected here. Hosted CI runs
only after the owner approves a push; its result is not part of this
report.
