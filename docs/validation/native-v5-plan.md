# Native protocol v5 qualification

Historical plan. [Protocol v6](native-v6-plan.md) prospectively supersedes only
the timed CANCEL normal-completion condition after the owner's explicit choice;
all v5 observations and FAILs retain their original meaning.

Status: owner-approved 250 ms requirement; implementation/qualification pending.
Tracking: issue #11, PR #10, milestone #2, branch `session/10-v014-native-parity`.
Decision: [ADR-0011](../design/decisions/ADR-0011-background-response-contract.md).

The owner accepted stock-runtime qualification and selected 250 ms for the
four response measurements. The [v4 plan](native-v4-plan.md) and
[candidate report](../reports/0.1.4-native-parity-candidate.md) retain their
historical 100 ms requirements, failures and diagnostic stop conditions.
The new product decision supplies a prospective qualification contract;
none of those old observations qualifies v5 or becomes a historical PASS.

## Fixed contract

`scripts/qualify/response_policy.py` is the executable policy: protocol, four
250 ms limits and the retained OVERSHOOT collection rule. A canonical JSON
SHA-256 identifies that exact policy in all evidence. No CLI option selects
a different numerical limit. Shared historical judges default to 100 ms.

The entry point collects each response gate's full returned records once,
validates each observation, computes the active v5 verdict and replays the
same registration through the historical default judge. It retains
`legacy_v4_1_100ms` beside the active result and binds the active policy hash.
Budget-zero full records are retained in this bounded response window even
though the runner's general history compacts them. Replay cannot execute a
native process, omit a record or request another sample.

- Timed return uses the existing `parse_start + B` reference; FIRST/HALF uses
  the actual callback request timestamp. No end-to-end process SLA is inferred.
- CANCEL still has 278 unique ordered executions, 15 timed points, fixed six
  allocator observations per point, FIRST49 and HALF49. Memory observation,
  cancellation and result conditions retain their existing meanings.
- OVERSHOOT still requests three extra observations when its first cancelled
  observation is in the old 80–120 ms range or above 100 ms. The response limit
  changes the judgement only, never this collection rule or which records count.
  Every first/additional observation must be valid and return within B + 250 ms.
  Natural completion supplies no actual-cancellation evidence; that separate
  requirement belongs to CANCEL's registered timed points and FIRST/HALF.
- Gap/cleanup use the same full parse observations and individual maxima.
- All other native purposes, input hashes, v4 performance sampling/limits,
  supervisor caps and the macOS sampled-memory controls remain unchanged.
- Stock 0.27.0 is the main runtime; existing support checks for 0.25.1 and
  0.26.13 remain. No runtime experiment is selected for qualification.

## Ordered execution

1. Implement shared judges and exact v5 policy/evidence binding. Run historical
   default-equivalence controls, 250/250.001 ms boundaries, invalid/censored
   observations, late natural returns, missing growth, policy/protocol mutation,
   duplicate/reordered registrations and mixed/rehashed artifact controls.
2. Independently review the implementation, then preassign one exact commit
   for `response-v5` in the manual diagnostic workflow. Run Windows x64,
   Ubuntu 24.04 x64 and macOS 15 ARM64 with the existing 30-minute job bounds.
   This preflight runs CANCEL, CANCEL-OVERSHOOT and shared gap/cleanup (four
   result names). Publish identity, gates, RUN and command records only.
   It is not a full qualification or an evidence carry-forward exception.
3. Freeze the final candidate. Preassign two independent first-attempt full
   three-OS cohorts before either result is inspected. Use the existing
   native-qualification workflow, all 17 purposes and two W12 recordings per
   job. All six results must pass. Match per-OS image/compiler/CLI/probe/
   supervisor identities, exact candidate source and the exact v5 policy.
4. Replay/audit raw evidence, compare exact functional results, verify the
   nested six-job evidence ZIP, and complete independent release review and
   common CI. Missing or inconsistent evidence remains HOLD. Retain every
   failed attempt; changes require a newly frozen candidate and registration.
   Both evidence construction and ZIP packaging recompute all four active
   response results and their complete historical results from the registered
   raw segment; missing legacy points remain invalid even after rehashing.
5. Follow the authorized merge method and verify the merged source identity.
   Publish v0.1.4 sources plus the nonbinary evidence ZIP, verify downloaded
   assets, update the release receipt and close only fully satisfied tracking.

The known V-LONGEXPR QUERY_ONLY stress watchdogs remain in the candidate report.
The release claim remains functional equality within the registered scope;
downstream go-treesitter integration and unrestricted input guarantees are not
implied. A new required failure is investigated on its evidence, not converted
to PASS by increasing the owner-selected bound again.
