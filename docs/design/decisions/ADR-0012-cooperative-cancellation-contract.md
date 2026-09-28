# ADR-0012 — Cooperative cancellation and normal completion

Status: Accepted product requirement; new implementation and qualification are required.
Date: 2026-09-28
Authority: the owner explicitly selected "정상 완료·실제 취소 구분 허용" after the v5 full-cohort failure was explained.

## Decision

Adopt prospective protocol v6. Keep stock Tree-sitter 0.27.0 and all four
250 ms response allowances from [ADR-0011](ADR-0011-background-response-contract.md).
Keep the registered inputs, 17 purposes, fixed sampling, resource limits,
cost/growth limits and supported OS/architectures. No runtime fork is adopted.

The timed CANCEL callback checks its deadline B only when the runtime calls
it. A parse can finish after the last callback without ever receiving a
cancellation request. The previous v5 contract required cancellation merely
because elapsed parse time reached B; this new contract distinguishes the
following outcomes for the registered timed points:

| Outcome | Required evidence | Actual cancellation coverage |
|---|---|---|
| Natural completion before B | Correct normal result, no request or contradictory crossing | NOT_TRIGGERED |
| Natural completion at/after B | Correct normal result, no request, no callback after B, plain return at most B + 250 ms and deletion at most 250 ms | NOT_TRIGGERED |
| Request issued at/after B | Coherent request/crossing, actual cancellation and null tree; plain return at most B + 250 ms, request-to-return at most 250 ms, deletion at most 250 ms | TRIGGERED |

No callback is also compatible with normal completion. A reported callback
crossing without a request, a request with a returned normal tree, or a
cancelled result without a request is inconsistent and fails. Finite timing,
normal result, input length, supervisor exit and allocator cleanup checks
remain required. Separate timers do not imply an external-request-to-process-
exit deadline. As before, allocator-instrumented timings are diagnostic;
the six allocator observations remain memory evidence.
The last callback derived from printed parse/tail times permits one unit of
their six-decimal millisecond precision for consistency only; the actual
250 ms return/deletion limits receive no tolerance.

FIRST and HALF still require every registered execution to actually cancel,
with their own trigger, cleanup and growth checks. These prove cancellation
at the registered progress states; they do not prove cancellation at every
wall-time deadline boundary. The owner deliberately accepts this narrower
timed-cancellation coverage for background analysis/indexing.

## Memory is still measured against elapsed budget

Normal completion does not waive memory observation. If any plain timed run
reaches B, at least one of the fixed six allocator runs must reach its own B
and measure its own growth. Every allocator observation is judged; missing
crossing/growth, inconsistent data, exceeded growth or cleanup counters fail.
An allocation crossing and a callback cancellation request are distinct.
The original 64 MiB post-budget-growth limit and all supervisor caps remain.

## Evidence and retained failure

At v5 candidate `0e72e0f`, the primary Ubuntu job returned normally at
200.843550 and 200.726183 ms for B = 200 ms, after last callbacks at about
198.724022 and 198.683311 ms. Both request/crossing markers were absent.
The v5 FAIL is correct under its contract and remains preserved. The other
five OS jobs passed 17/17; all six functional results agreed. Neither this
agreement nor the new product decision turns that pair into a release PASS.

Collect new v6 response observations once and retain complete independent
v6, v5/250 ms and v4.1/100 ms judgements. Bind the new policy to all evidence
levels and reject mixed policies. Follow [the v6 plan](../../validation/native-v6-plan.md)
for controls, review, preflight and two freshly registered full cohorts.

The pinned [Tree-sitter 0.27.0 public API](https://github.com/tree-sitter/tree-sitter/blob/v0.27.0/lib/include/tree_sitter/api.h)
defines callback cancellation; the repository's deadline and response
requirements are consuming-product choices, not upstream timing promises.
