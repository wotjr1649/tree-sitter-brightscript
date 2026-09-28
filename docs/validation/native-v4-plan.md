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

## Phase 1 results and phase 2 registration

[Phase 1, 36361881253](https://github.com/wotjr1649/tree-sitter-brightscript/actions/runs/36361881253)
completed all nine jobs at `7b55d27`. Each OS's three jobs had equal image,
compiler and input identities. Ubuntu passed all five selected gates in both
builds. Windows failed PRINT cleanup in all six measurements (107.6–123.1 ms).
macOS retained A5, valid-parse or ACTUAL cancellation failures in both build
modes. The amalgamation hypothesis did not resolve the failures.

A local four-item PRINT grouping experiment preserved corpus 228/228 and
SEM-PUBLIC 2,811/2,811. Its 1 MiB PRINT allocations fell from 1,572,892 to
524,326 and peak live bytes from 147,066,304 to 54,792,840; cleanup was 28.8 ms
against the local frozen baseline's 67.1 ms. Its A5 gate failed, so it was not
adopted. The experimental grammar and raw results remain in the local trial
record. The product sources were regenerated back to the frozen baseline.

Phase 2 compares the default condition with a diagnostic-only scheduled
condition, on the same frozen sources and three independent jobs per OS.
On Windows the probe pins its own thread to the lowest allowed process-mask
bit and verifies the thread mask. On macOS it requests `USER_INITIATED` QoS
with relative priority zero and verifies the requested class by readback.
Linux is unchanged. API errors stop the probe. Neither treatment changes
other processes or host settings; QoS does not prove use of a performance core.
Candidate, H and BEFORE_PRINT receive the same condition. This is a separate
experiment and does not change the default qualification condition.

Before each profile's original measurements, all A5 case/operation pairs get
an A/A control: two aliases of exactly the same binary and query, alternating
in seeded order, one warmup plus five samples each. Every result/work signature
must agree and the larger median divided by the smaller must be at most 1.5.
Missing, censored, nonpositive or non-finite observations fail. A failed A/A
control means that condition has not established repeatable comparison.
Growth remains an independent performance verdict under the original bounds;
a growth failure alone is not evidence of measurement invalidity. All trials
and individual raw values are retained. A/A success does not qualify a release
or retrospectively resolve a default-condition failure.

API contracts checked for the experiment:
[SetThreadAffinityMask](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-setthreadaffinitymask),
[GetThreadGroupAffinity](https://learn.microsoft.com/en-us/windows/win32/api/processtopologyapi/nf-processtopologyapi-getthreadgroupaffinity),
[Apple pthread QoS](https://github.com/apple-oss-distributions/libpthread/blob/main/include/pthread/qos.h).

## Phase 3: additional independent cold samples

Phase 2's macOS scheduled A/A control still failed in an observed trial:
the same binary's NAV_FIELD medians were 0.242 and 0.444 ms (ratio 1.835).
Scheduling alone is therefore insufficient. A proposed in-process batch was
rejected before implementation because it would change cache/allocator state
and the measured quantity. No batch execution path was added.

Phase 3 retains independently launched single-operation processes and the same
median statistic. It compares scheduled `single5` (one warmup plus five
measurements) with scheduled `single15` (one warmup plus fifteen) for A/A,
paired A5/VALID costs and the three registered diagnostic sweep families.
The same binary/query, input and scheduling condition are used in both.
Only the sample count changes. Exact completed counts and unique process
identities are required; every value and trial is retained. Cancellation,
callback gap, cleanup, memory and their maximum-value rules are unchanged.

The experiment is three jobs per OS, at most 60 minutes per job. Exceeding
execution or evidence-size limits makes it incomplete; no sample or raw field
is dropped to fit. If `single15` fails, it does not automatically trigger more
samples or replacement runs. v4 adoption still requires an independent review
of all three cohorts and their performance verdicts. Existing `single5` FAILs
remain failures.

## Phase 3 result and phase 4 cancellation control

[Phase 3, 36364118813](https://github.com/wotjr1649/tree-sitter-brightscript/actions/runs/36364118813)
completed all nine jobs at `23a3c59`. All three records within each OS share
runner image, compiler, product, probe, harness and input hashes; no record
exceeded the 64 MiB raw limit. This is diagnostic completion, not PASS.

- Windows: both profiles passed A/A in all three jobs, but PRINT cleanup
  failed throughout. One `single15` profile also failed timed cancellation.
- macOS: `single15` passed A/A in two jobs and failed in one. The failed
  identical-binary NAV_CURSOR comparison on `A501J-k01000` measured medians
  0.124 and 0.281 ms (2.266 ratio), with identical work signatures and all
  16 records per side. A5 or VALID failures remained in every `single15` job.
- Ubuntu: both profiles passed A/A and cost/valid/cancellation; the third job
  failed MAX-CALLBACK-GAP in both profiles.

No phase 3 condition is adopted for release. These observations do not prove
that every failure is host noise or that the OS cannot meet the requirements.
The next performance investigation must isolate a cause; it cannot be another
unbounded sample-count or favourable-run search.

Phase 4 executes only the separately reviewed first-callback cancellation
control, with the frozen product, default scheduling and three jobs per OS
(20-minute job timeout). It does not repeat phase 3 cost experiments. Each
of the seven registered families gets one warmup, five plain executions and
one allocator execution. All 49 process identities must be unique. Every run
must return a null tree after exactly callback 1, report its own equal request
and crossing timestamps, the entire registered source length, `has_error=-1`,
zero allocator live bytes after cleanup, confirmed exit and no descendants.
All plain runs, including warmup, must return within 100 ms of their own
request and clean up within 100 ms. A null tree's `-1` deletion sentinel
contributes zero time. The allocator run must observe less than 64 MiB growth
from its own callback through completed parser cleanup; allocator timings
are diagnostic only. Missing, non-finite, negative or contradictory records
fail. Natural completion or no callback fails.

The first implementation review found that temporary allocation during
parser cleanup escaped the post-trigger peak. The correction retains tracking
through cleanup only for this new control, publishes the cleanup peak and
requires `parse peak <= cleanup peak <= overall peak`. A 128 MiB cleanup
growth negative control rejects that defect. Independent static re-review
closed the finding. Native confirmation on all three OS remains required.
The existing v3 SAFETY/ACTUAL implementation and verdicts are unchanged;
phase 4 does not promote its control into a v4 release gate.

[Phase 4, 36365332865](https://github.com/wotjr1649/tree-sitter-brightscript/actions/runs/36365332865)
at `d03c312` passed all nine jobs: 441/441 native executions, with equal
per-OS image/compiler/product/probe/harness identities and clean checkouts.
Each OS contributed 126 plain runs and 21 allocator runs. Maximum plain
request-to-return / cleanup times (ms) were Windows 0.0076 / 0.0476,
Ubuntu 0.000201 / 0.006853, and macOS 0.001 / 0.007. Each OS's maximum
post-callback growth through cleanup was 64 bytes. Every run confirmed exit
and zero remaining descendants. This closes this diagnostic control's
cross-platform native evidence; it does not close the remaining release gates.

## Phase 5: preserve the pairing in the estimator

Phase 3's failing macOS A/A raw values show both aliases changing from roughly
0.12 ms to roughly 0.28 ms during the same point. Exploratory calculation of
per-pair ratios suggests a cause to test: the existing alternating measurement
design loses its pair relationship when it divides two independent medians.
These are different estimands, not an arithmetic bug. No old trial is
reclassified. Independent adversarial design review approved this diagnostic
after its growth sample counts and floor rules were made explicit.

Before any new observation, fix the experiment as follows:

- Frozen v0.1.3 product and phase 3 scheduled condition, three jobs per OS,
  at most 60 minutes and 64 MiB raw evidence per job. No in-process batching.
- For each family/operation, execute 16 rounds. Round 0 is warmup; all 15
  remaining rounds count. In each round, seeded shuffle visits every size
  once; at each size another seeded shuffle orders candidate/reference.
  The seed is 5707 plus the registered trial number. No invalid observation
  may be removed, replaced or reassigned to another round.
- Cost is `median(candidate_i / reference_i) <= 1.5`. A/A uses
  `max(r, 1/r) <= 1.5` for that median `r`. Preserve the old ratio of medians,
  its verdict, every pair ratio, order, unique process IDs and raw values.
  Keep the existing cost floor: a reference median below 0.1 ms makes the
  bound inapplicable but never excuses invalid data or unequal work.
- Growth uses the ratio of the two sizes in the same round, followed by
  `log(median(ratios)) / log(size ratio)`. The middle-size observation is
  shared by two contrasts, so these contrasts are correlated; no extra
  middle-size execution is introduced. Use the original last-three sizes
  for A5 (bound 1.5) and VALID (bound 1.2). A5 retains its large-size median
  0.1 ms applicability floor. VALID has no growth floor.
- The three registered diagnostic sweep families retain sizes 100, 400,
  4000 and 20000, once per round, and contrasts 400/20000 and 4000/20000.
  Preserve the aggregate small-size floor by scaling every small sample by
  `max(median(small), 0.1) / median(small)` before taking paired ratios.
  Record both estimators and the scale; bound remains 1.5. This diagnoses
  growth only and does not replace the full sweep's memory gate.
- A/A covers all 16 A5 cases with four operations and all 39 VALID parse
  cases. Candidate/reference cost and growth use the same complete sets.
  A separate native negative control adds a measured 2 ms busy delay to
  NAV_CURSOR on `A501J-k01000`, using the same traversal and work digest.
  It counts as detection only with valid equal work and a paired ratio above
  1.5, never because identity, termination or work validation failed.
- Exactly 6,816 native executions per job, including warmups and the slow
  control. Global uniqueness concerns actual executions; a growth contrast
  referring to an existing observation does not constitute a new execution.
  Any missing, nonpositive, non-finite, censored, duplicate or contradictory
  observation makes its comparison invalid. Preserve failed trials.

Judge controls cover label exchange, common unit scaling, shared speed
changes, candidate-only slowdown, the 1.5 boundary, missing/duplicate rounds
and floor rules. Normal qualification builds contain no delay or scheduling
treatment. Maximum latency, cancellation and memory requirements are unchanged.
If any new cohort's A/A, equal-work, slow or completeness control fails, do not
adopt this method or automatically change its estimator/sample count. Even
if controls pass, performance verdicts and v4 adoption require separate review;
the diagnostic always records release HOLD.

Implementation review found and closed missing supervisor-state and duplicate
event/final timing validation. Negative controls now reject those missing or
contradictory fields. Local judge tests passed 8/8, including exact execution
counts and floor locations. A separate Windows native 64-execution screen
measured identical-binary paired ratio 0.99786 and detected the same-work
2 ms control at ratio 21.8559; raw rejudgement with the strengthened validator
passed. These local controls do not replace the new hosted cohort.
