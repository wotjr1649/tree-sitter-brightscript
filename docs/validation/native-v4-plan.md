# Native protocol v4 qualification work

Status: diagnostic plan, not an accepted release result. The v0.1.4 candidate
remains HOLD. This plan follows an independent adversarial review on
2026-09-28; it does not change historical protocol-v3 verdicts.
Tracking: [issue #11](https://github.com/wotjr1649/tree-sitter-brightscript/issues/11)
in the existing v0.1.4 milestone and PR #10.

## Invariants

- Preserve all 17 native purposes and the registered source inputs.
- Keep the existing 100 ms single-run cleanup, callback-gap and overshoot
  limits, 1.5 cost/growth limits and 1.2 valid-parse growth limit. A measured
  baseline plus a margin is not justification for raising a limit.
- Use calibration to establish measurement validity and reproducibility.
  A baseline run cannot qualify the candidate for release.
- Keep every failed trial. Do not select a favourable rerun or average away
  a failure of a maximum-latency requirement.
- Windows x64, Ubuntu 24.04 x64 and macOS 15 ARM64 are the target platforms.
  Memory metrics retain their OS labels. macOS uses a sampled group footprint
  guard; it does not establish an instantaneous kernel hard limit.

## Ordered work and evidence

1. **Characterize the failure before changing the gates.** On each OS run
   three independent jobs with the frozen v0.1.3 product sources and the same
   pinned 0.27.0 runtime. Compare the current separate runtime translation
   units and the upstream-supported `lib/src/lib.c` amalgamation at `-O2`,
   with assertions retained in both. H and BEFORE_PRINT retain their own
   identities and use the same build flags. Record the full A5 and valid
   parse sets, cleanup/callback inputs, and the three observed failing sweep
   families. Seed the alternating build order before execution. Preserve raw
   records, compiler/runner identities and input hashes. This finite diagnostic
   does not replace full regression coverage or emit a qualification PASS.
2. **Resolve causes and freeze the final protocol.** Improve an actual build
   or implementation defect only with matching evidence. If short timings
   require a different sampling method, first specify its measurement region,
   repetitions, statistic and controls, obtain independent review, then use
   separate calibration and confirmation data. Query/navigation measurements
   must not include parse/setup/cleanup. Keep individual maxima for cleanup,
   callback gap and overshoot. A known-slow control must still be rejected.
3. **Make ACTUAL cancellation portable.** Retain every existing wall-time
   SAFETY observation and the legacy ACTUAL verdict. Add a separate control
   for all seven ACTUAL families that requests cancellation at progress
   callback 1: one warmup, five plain runs and one allocator run per family.
   Every run must actually cancel, clean up within 100 ms and record its own
   trigger; allocator growth after that trigger must be below 64 MiB. A
   natural completion cannot pass. A v4 API-path coverage result is not an
   assertion that the historical 100/200 ms ACTUAL test passed. The precise
   executable contract requires review before qualification.
4. **Validate the sampled macOS guard.** Retain parent, child and orphan
   controls; record maximum sample interval, observed footprint overshoot,
   termination latency and complete process-group cleanup. Observation,
   permission or cleanup failures stop the lane. An observed maximum is not
   a bound on unobserved between-sample peaks or a child that creates a new
   session.
5. **Qualify one frozen candidate.** Two independently allocated full jobs per
   OS must each pass every v4 native purpose, repeated W12 and exact functional
   comparison. All results must have the prescribed runner image/tool
   identities. A product, harness or supervisor failure cannot be excluded or
   replaced. An identity mismatch makes the cohort incomplete. Only a
   checkout/action infrastructure failure before measurement starts may get a
   replacement; retain and link its original failure. Changing the method or
   candidate requires new qualification, not reuse of an earlier result.
6. **Review and release.** Complete independent adversarial review, common CI,
   raw/normalized identity and evidence ZIP verification. Then verify the
   merge identity, publish v0.1.4 sources and the nonbinary evidence ZIP,
   verify public downloads, and close the milestone. Any required FAIL or
   missing evidence preserves HOLD.

## Design review disposition

The initial plan was rejected because a same-implementation baseline could
fit raised thresholds, a shorter cancellation budget could manufacture
coverage, batching could conceal single-run latency, and failed-job replacement
was underspecified. The sequence above addresses those findings. Independent
static re-review found no remaining P1/P2 in this execution plan. Implementation,
measurement validity and release review remain pending.

The build alternative comes from upstream Tree-sitter 0.27.0's
[`AMALGAMATED` option](https://github.com/tree-sitter/tree-sitter/blob/v0.27.0/CMakeLists.txt).
The project does not modify the stock runtime or assume that the alternative
is faster. Diagnosis can legitimately conclude that a cause remains open.
