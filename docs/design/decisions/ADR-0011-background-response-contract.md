# ADR-0011 — Background-analysis response requirements

Status: Accepted product requirement; implementation and release qualification are separate.
Date: 2026-09-28
Authority: the owner approved the stock-runtime/v5 proposal and explicitly selected 250 ms instead of 500 ms.

## Decision

The intended consumer uses background code analysis/indexing and does not
require extreme response optimization. Adopt protocol v5 for prospective
v0.1.4 qualification on Windows x64, Ubuntu 24.04 x64 and macOS 15 ARM64.
Keep stock Tree-sitter 0.27.0; the completion-checkpoint and allocation
experiments remain unadopted evidence. No downstream runtime patch is required.

The owner-selected response requirements are:

| Measurement | v5 bound |
|---|---:|
| Maximum progress-callback gap, including parse edges | 250 ms |
| Timed parse return measured from parse start | budget B + 250 ms |
| FIRST/HALF return measured from its actual callback cancellation request | 250 ms |
| Measured tree-delete plus parser-delete time (null-tree sentinel contributes zero) | 250 ms |

These replace only the four former 100 ms response requirements. They are a
product tradeoff, not an upstream guarantee, a claimed fix of the old failure,
or a threshold fitted by the qualification results. Each prescribed sample
must meet the new bound. Separate timers do not establish a summed end-to-end
deadline from an external request through process/descendant termination.

The same inputs, cancellation budgets and actual-cancellation semantics apply.
The registered CANCEL timed points still require cancellation when their
budget is reached; late natural completion cannot satisfy that purpose.
CANCEL-OVERSHOOT retains its separate return-time purpose: a normal return
within B + 250 ms is allowed and supplies no actual-cancellation evidence.
Keep fixed six-allocator sampling and require observed growth when prescribed.
Keep all 17 purposes, functional equality, memory limits, post-trigger growth,
cost/growth ratios, watchdogs and process cleanup controls. In particular, the
macOS memory-monitor sample/kill 100 ms controls remain unchanged.

## Evidence and history

Native response samples are collected once. Judge those same records under
the new policy and the historical 100 ms policy, retaining separate results.
Historical v3/v4/v4.1 reports and FAILs retain their original meaning. The
historical result of new v5 observations is not a new historical qualification.

The committed policy content and hash are bound through identity, gate records,
normalized common evidence and both levels of release ZIP. A different policy
or mixed protocol is rejected, including a policy that has been edited and
rehash-labelled. Legacy response failures do not assert failure of the new
requirement; every unchanged correctness, cancellation and resource condition
still applies. Historical public replay tools and original source commits
remain available.

Implementation/adverse controls, independent review and a preassigned three-OS
response preflight precede a frozen candidate's six full qualification jobs.
Every final job must pass all 17 purposes and repeated W12, with exact cross-OS
functional equality and matching per-OS image/tool identities. No favourable
replacement run qualifies a failed candidate. Follow [the v5 plan](../../validation/native-v5-plan.md).

Known long-expression query stress watchdogs remain disclosed. This decision
does not claim all inputs/environments are equivalent or that downstream
go-treesitter has been validated by native Tree-sitter results.

## Scope correction after the first implementation preflight

The initial ADR's unqualified "reached timed budget" wording and its review
incorrectly extended CANCEL's actual-cancellation condition to OVERSHOOT.
This was outside the owner's numerical-only response change. Restore the
historical separation above, keep individual validity and return bounds,
and include that scope in the policy identity. The original preflight FAIL
at `2dfaecc` is retained; corrected offline replay is not new qualification.
A new frozen source and preflight precede the six full jobs.
