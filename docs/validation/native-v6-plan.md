# Native protocol v6 qualification

Qualification and publication completed for candidate `82784b8`; the
[publication receipt](../reports/0.1.4-release.md) records the source/tag identity
and public asset verification. Maintenance closure follows final documentation
CI and handoff.

This prospective plan applies [ADR-0012](../design/decisions/ADR-0012-cooperative-cancellation-contract.md),
the owner's explicit normal-completion/cancellation distinction. The four
250 ms allowances, stock runtime and all other v5 requirements remain.
The [v5 plan](native-v5-plan.md) and its failed cohort remain historical.

## Implementation and controls

- Keep historical judge defaults unchanged. Only v6 CANCEL enables the new
  normal-completion outcome; FIRST/HALF remain mandatory actual cancellation.
- Keep elapsed-budget `reached` true for a normal return at/after B. Require
  allocator counterpart growth exactly as before; never turn it into an
  inapplicable memory point. Allocator timings remain diagnostic.
- Record natural outcomes as NOT_TRIGGERED, with no request-to-return value.
  For issued requests, validate request/crossing/cancelled/null-tree coherence
  and both plain return bounds. Invalid or missing observations remain FAIL.
- Add boundary, overrun, request-ignored, cancelled-without-request, late
  callback, missing-growth, extra-sample and malformed-record controls.
- Collect once; replay v5 at 250 ms and v4.1 at 100 ms from the same complete
  records. Evidence construction and both ZIP levels require the full raw
  replay, including historical bodies, plus exact new policy content/hash.

## Ordered execution

1. Finish focused controls, historical replay equality and independent review.
2. Preassign one exact commit for the manual `response-v6` three-OS preflight;
   existing 30-minute bounds and the four response result names remain.
3. Freeze the final candidate. Before inspecting either result, preassign two
   independent first-attempt full cohorts with all 17 purposes and repeated
   W12 on Windows x64, Ubuntu 24.04 x64 and macOS 15 ARM64. Every job must pass,
   with exact cross-OS functional equality and equal per-OS image/tool identity.
4. Audit raw records and the nested six-job evidence ZIP; complete common CI
   and independent evidence review. Failure or missing evidence remains HOLD.
5. Verify the authorized merge's source tree, publish the source-only v0.1.4
   tag/Release and nonbinary evidence ZIP, verify public downloads, then add
   the publication receipt through a separate reviewed documentation change.
   Close tracking and freeze only after its exact CI and final handoff.

All prior FAILs, the unadopted runtime experiments and the extra long-expression
query watchdogs remain disclosed. No old observation supplies new v6 release
qualification, and no timing threshold or other purpose is changed by this plan.
