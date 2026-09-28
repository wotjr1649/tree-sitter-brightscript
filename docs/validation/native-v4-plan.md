# Native protocol v4 qualification work

Status: diagnostic plan, not an accepted release result. The v0.1.4 candidate
remains HOLD. This plan follows an independent adversarial review on
2026-09-28; it does not change historical protocol-v3 verdicts.
Tracking: [issue #11](https://github.com/wotjr1649/tree-sitter-brightscript/issues/11)
in the existing v0.1.4 milestone and PR #10.

## Follow-up after the frozen pair failed

The `f05d744` pair and every failed purpose remain in the candidate report.
The parent-record retention fix has separate raw-replay and allocation
evidence. Product screens next target hidden repetition allocations in
file-level lines, array elements and the five comma-list call sites. The
same full native gates and first-attempt pair remain mandatory.

Local controls compare all list suffixes through two four-unit boundaries
against the frozen parser. A `_terminator` inline experiment did not reduce
allocation counts and was discarded. Grouping assignment heads reduced the
pending-stack footprint, but changed 12 existing recovery goldens; that
experiment was discarded and its FAIL log retained. No golden was updated.
The list-only candidate restores every existing recovery golden. New hosted
measurements are still needed for the Ubuntu callback/cancellation failures.

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

Phase 5 [run 36366610860](https://github.com/wotjr1649/tree-sitter-brightscript/actions/runs/36366610860)
at `d1eaa61` completed all nine jobs, 61,344 native executions. Every A/A,
same-work slow control, registered cost and growth comparison passed. The
maximum A/A symmetric ratio was 1.148704 and the maximum cost ratio 1.184564.
The closest growth comparison to its bound was VALID nested-if at 1.126818
against 1.2. Slow-control ratios ranged from 8.2079 to 18.8839. Per-OS runner,
compiler, product, probe and harness hashes agree; input hashes agree across
all nine jobs. This supports adopting the paired estimator, subject to new
full qualification of the eventual product and all 297 sweep families.

An offline audit replayed the registered order and every record from each
raw file after checking its SHA-256. All verdicts and fields matched exactly
except one macOS legacy log exponent: 1.0386319426574064 versus the Windows
recalculation 1.0386319426574062. The strict audit failure was retained. The
audit permits at most two ULP only in recalculated log-exponent fields for
platform math-library rounding, while requiring exact verdicts and all other
fields. No native threshold or native decision receives a tolerance.

## Phase 6: progressed cancellation before v4 integration

Adoption review accepted the paired estimator evidence but rejected replacing
all legacy ACTUAL coverage with first-callback cancellation: that alone would
not prove cleanup after parser state has accumulated. The corrected v4 plan
keeps every original timed point and SAFETY requirement. Each warmup, plain
or allocator run that reaches its own budget or records a crossing must
actually cancel. Only normal completion strictly before its own budget is
an allowed legacy ACTUAL exception; preserve the original verdict separately.
Unobserved post-budget growth, late natural completion, wrong results,
censoring, inconsistent records or exceeded limits still fail v4 primary.

Before integration, phase 6 requires FIRST and HALF controls for all seven
families on the frozen product, three scheduled jobs per OS, at most 20
minutes per job. `CANCEL_HALF` asks to cancel at the first progress callback
whose public `TSParseState.current_byte_offset` reaches `ceil(input bytes/2)`.
Require at least two callbacks, the maximum earlier callback offset strictly
below the target, and `target <= request offset < input length`. EOF-only
arrival, no arrival, natural completion or an earlier request fails. This
observes a byte-position milestone; it does not assert that half the syntax
tree has been built. The pinned 0.27.0 public header and implementation define
that state field; no private runtime mutation is used.

Each control has one warmup, five plain and one allocator execution per
family: 98 unique executions per job. All phase 4 exit, null-tree, own-trigger,
100 ms return/cleanup and less-than-64 MiB growth-through-cleanup checks remain.
HALF uses budget zero and no callback-count trigger. Negative controls cover
odd input lengths, missing/invalid offsets, early/EOF request and an already
reached target at an earlier callback. Independent design review closed the
coverage finding; implementation and hosted confirmation remain required.

Independent implementation review found no P1/P2. Its requested additional
negative controls cover 98-run integration with a cross-control duplicate ID,
exact target/prior-offset boundaries and the common time/growth bounds in
HALF mode. The diagnostic also requires the exact seven registered input
hashes. Local judge checks passed 10/10. A Windows native FIRST/HALF screen
passed 98/98 executions: HALF requested cancellation after 2,622–13,108
callbacks, at offsets 524,320–524,442, and its maximum plain cleanup was
31.6216 ms. Hosted confirmation is still required.

The v4 normalized registration is 1,768 keys: retain the exact existing
1,533 keys, plus 206 A/A aliases, one slow control, 14 FIRST and 14 HALF keys.
The existing 2,811 trees, 30 incremental results and 231 repeated W12 inputs
remain required. Registration is not a release result.

[Phase 6, 36368317053](https://github.com/wotjr1649/tree-sitter-brightscript/actions/runs/36368317053)
at `92e637e` passed all nine jobs. Offline replay checked every field, source
hash, process ID, registered order and raw-file SHA-256: 882/882 executions
passed. Per-OS image/compiler/product/harness/probe hashes agree. Maximum
plain cleanup was Windows 73.0684 ms, Ubuntu 25.106737 ms and macOS 33.717 ms;
maximum growth after the trigger through cleanup was 64 bytes on each OS.
This closes the progressed-cancellation prerequisite for v4 adoption.

## v4 integration

Independent design review accepted phase 5's estimator and phase 6's coverage.
The executable contract is now in [validation.md](validation.md#v014-three-os-native-candidate).
The implementation retains v3 judgements, requires the controls in every
affected performance gate, and preserves the exact previous API key set.
Implementation review found that SWEEP's smallest size could escape work
validation because neither exponent uses it. All four sizes are now required
valid, with dedicated warmup-censoring and missing-final negative controls.
This correction preserves the original no-crash/full-observation requirement.
Native candidate screening and final six-job qualification remain pending.

The PRINT grouping candidate subsequently passed its six-purpose local v4
screen, including exact replay of 6,931 records. Details and remaining limits
are in the [candidate report](../reports/0.1.4-native-parity-candidate.md#print-candidate-under-v4).
This supports submitting it to full hosted qualification; it is not a
replacement for the six required final jobs.

The first frozen v4 pair at `f05d744` failed; its six-job result and the
subsequent inherited-RSS diagnosis are retained in the
[candidate report](../reports/0.1.4-native-parity-candidate.md#frozen-v4-pair-f05d744--fail-retained).
Reducing redundant Python record retention preserves every raw byte and
judge input. Its local controls and six-job offline replays pass, but native
Linux confirmation is pending. Remaining single-run cleanup, callback and
late-natural-cancellation failures require separate root-cause work.

## List candidate follow-up and Windows accounting correction

The second frozen pair, `9ad11bb`, passed all 17 purposes on both Ubuntu
jobs but failed on Windows and macOS; the [retained report](../reports/0.1.4-native-parity-candidate.md#frozen-list-candidate-9ad11bb--fail-retained)
records each failure. Independent design and implementation review accepted
the bounded root-only Job-accounting correction. Native safety controls and
the pinned safety-profile checks passed; a rare settling transition remains
unobserved locally. Historical FAILs are preserved.

Next, measure CPU time and callback byte positions in a separate diagnostic
build to distinguish expensive parser work from time spent off CPU. Keep the
unchanged plain and allocator builds as controls, retain all samples and
source/tool identities, and make no release judgement from diagnostic
timings. Existing wall-clock maxima, timed cancellation growth requirements
and all 17 purposes remain unchanged. A material correction, independent
review and a newly preregistered full pair are still required.

The bounded diagnostic uses five unchanged 1 MiB inputs (L-WHILE,
L-FOREACH, L-ANON, V-FLAT, V-LONGEXPR), budgets 0/100/200 ms, four repetitions
and four builds: original plain/allocator and diagnostic plain/allocator.
All 240 executions per OS are retained in fixed alternating order. One
20-minute job per supported OS runs on a separate diagnostic branch. This
does not constitute either cohort of a final qualification pair.

The diagnostic build observes head, interior and tail gaps with fixed
CPU-then-wall snapshots at parse start, every callback and parse return. It
also records cleanup CPU time, callback ordinal and byte positions. CPU
accounting uses [GetThreadTimes](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-getthreadtimes)
on Windows and [getrusage](https://developer.apple.com/library/archive/documentation/System/Conceptual/ManPages_iPhoneOS/man2/getrusage.2.html)
for the single-threaded POSIX probe (official API contracts checked
2026-09-28). API errors stop the process. The diagnostic maximum must match
the existing measured gap including edges. CPU resolution and observation
overhead limit interpretation; wall minus CPU does not identify a particular
scheduler or system cause. Compare plain/diagnostic elapsed times, callback
counts and cancellation positions before drawing conclusions.

Without the diagnostic macro, both plain and allocator executables must be
byte-identical to builds of the pre-diagnostic probe at `f3f67fa` using the
same compiler, grammar, runtime and executable basename. Different PE image
basenames produced a failed initial identity check; the comparison now keeps
the basename fixed in separate task-owned directories. The byte equality
requirement itself is unchanged. The diagnostic protocol and output are
explicitly ineligible for release qualification.

Independent design and implementation review found no P1/P2. The local
Windows plan completed all 240 observations and verified both unchanged
binary identities. A cancelled parse's tail endpoint is the last observed
callback offset, not a new parser-position observation; diagnostic CPU
values include instrumentation overhead. These observations do not replace
hosted diagnosis or final qualification.

[Hosted diagnosis 36377524645](https://github.com/wotjr1649/tree-sitter-brightscript/actions/runs/36377524645)
at `417a7c5` completed all 720 observations and both original-binary identity
checks per OS. The unrelated common CI stopped because the newly fixed
diagnostic workflow commands had not been registered in the CLI-path guard;
the two exact commands now replace the old characterization commands, with
negative controls for mixed modes, altered compiler/runtime/output, gate
selection and shell suffixes. No new launcher exemption or wildcard is added.

The short diagnostic did not reproduce the earlier Windows 109/195 ms gaps
or macOS missing timed-growth evidence. Ubuntu's diagnostic L-WHILE maximum
gap was 103.892254 ms wall and 103.822 ms CPU near EOF; its original maximum
was 88.871563 ms. This establishes substantial CPU work in the instrumented
EOF interval, not the cause of the earlier Windows outliers. The previous
failures remain open; successful diagnostic completion does not justify
another unchanged final qualification attempt.

### Short Windows witnesses with final root CPU observation

The retained Windows sweep contains two small-input outliers:
`SW-y203d205b-2920else20-colon-k00400` has 16 samples with median 1.02595 ms,
maximum 190.8754 ms and interior gap 189.8284 ms; `SW-3f20-5b12c-eof-k00400`
has median 0.9431 ms, maximum 128.017 ms and gap 127.0413 ms. Their original
CPU usage was not recorded. They motivate a lower-overhead observation plan;
they do not prove the cause of earlier L-ANON/V-LONGEXPR failures.

After independent design review, a single Windows job alternates these two
unchanged witnesses 5,000 times each at budget zero with the original plain
probe: 10,000 executions, 20-minute job limit, no automatic extension or
retry. The supervisor reads final root user/kernel CPU after confirmed exit;
the original probe is unchanged and the previous binary identity check
remains mandatory. CPU query errors fail closed. Retain every raw record,
process/image/tool identity, UTC start and elapsed campaign duration.

Only complete observations can inform interpretation. A gap much larger
than total root CPU supports time not accounted for by CPU execution, subject
to counter granularity; a larger CPU total cannot determine what happened
inside that gap. Neither outcome identifies a particular system service or
relabels a historical failure. Non-reproduction remains inconclusive. The
fixed workflow command receives the same exact allowlist and argument-
mutation checks; no new launcher is exempted.

Implementation review found and closed one P2: the initial completeness
check did not require successful execution of the intended PARSE workload.
The validator now reuses the registered result/error-state check and binds
both input hashes, byte lengths, budget zero, non-cancellation, supervisor
exit, and exact event/final timings. Non-finite values and a gap exceeding
parse time are rejected. Positive and planted-defect controls join the
existing native-evidence tests in common CI. The local campaign already in
progress at that finding retains its original source and completion record;
its stronger post-run audit is separate from execution by the corrected
validator. The final-CPU supervisor passed stock/extended safety controls,
including normal/sleep CPU observations, before prospective hosted use.

The corrected hosted [Windows witness run 36379409698](https://github.com/wotjr1649/tree-sitter-brightscript/actions/runs/36379409698)
at `88172dc` completed all 10,000 observations in 270.1267 seconds. The two
inputs' median parse times were 1.2105/0.9067 ms; maximum gaps were
18.7662/15.4048 ms. No gap exceeded 100 ms, so this campaign did not reproduce
the retained outliers or establish their cause. Exact offline validation of
registration, 10,000 process identities, input/source/image hashes and every
summary field passed. Common three-OS CI and POSIX preflight also passed.
This finite campaign is complete; it is not repeated until a new material
hypothesis or correction exists. Historical latency failures remain open.

## Prospective v4.1 CANCEL allocator sampling

The owner chose review of the fixed six-allocator-sample proposal. Independent
adversarial review accepted the design with a factual, fail-closed check for
the single missing-counterpart exception. The operative contract is in
[validation.md](validation.md#v014-three-os-native-candidate): original 105,
fixed 75 additions, unchanged FIRST49/HALF49, 278 unique registered runs.
No numeric limit or input changes. Record original v4 point dispositions and
legacy v3 results; all original and extra execution failures remain blocking.

Order: implement the new protocol and exact registration checks; test missing
coverage, late natural return, censoring, wrong result, cleanup and growth
violations (including combined violations); independently review the diff;
then run one preassigned CANCEL-only pilot on each supported hosted OS at one
commit. The pilot is diagnostic, not a full qualification cohort. Preserve
all results. If all six allocator samples still miss required growth, retain
HOLD without another sample-count increase. Windows historical latency
failures remain a separate unresolved prerequisite for a new full cohort.

Implementation review found and closed P2: an invalid added tag had changed
the retained original sampling verdict. Original verdicts are now computed
before the 75 additions; tag/order/case/budget/identity mutants prove their
preservation and the new gate's failure. A local native trial completed all
278 executions but failed judgement because compressed FIRST/HALF records
omitted registration fields. That failure and raw data are retained; the
runner now retains those 98 control records in full. Its offline replay is
separate from the failed execution. The corrected fresh local trial passed
all 278 executions and exact raw replay. The increased retained records must
also satisfy full-qualification memory limits; a size estimate is no waiver.

Independent static re-review found no open P1/P2 for the pilot. Local checks
passed: 14 evidence/judgement tests (also registered in common CI), 12 CLI
guard tests, six original gate tests, ten characterization tests, V0 and
diff checks. A compiler-path error before the first local trial launched no
probe and is retained separately from the judgement failure. No hosted pilot
or full-qualification result is claimed by these local observations.

The preassigned [hosted pilot 36381377616](https://github.com/wotjr1649/tree-sitter-brightscript/actions/runs/36381377616)
at `bcc5755` passed on all three OS, 278 executions each. Exact raw replay of
all 834 records and source/hosted identity checks passed. Common CI and POSIX
preflight also passed. All 15 original sampling points already passed on
each host, so this pilot did not reproduce the earlier missing counterpart.
Independent review confirms HOLD: neither this pilot nor the completed
non-reproducing Windows diagnostics establishes a latency cause or correction.
No new full pair is registered. The current result and evidence needed to
reopen are recorded in the [candidate report](../reports/0.1.4-native-parity-candidate.md#v41-cancel-pilot-bcc5755--pass-within-its-scope).

## One bounded Windows ETW diagnostic

The owner approved one ephemeral GitHub-hosted Windows VM job (30 minutes),
at most 120 seconds of tracing in total, at most 64 MiB of capture buffers,
no environment/command-line collection, and no automatic raw-trace publication.
The existing 100 ms limits and historical FAILs remain unchanged. This is
diagnosis, not another full qualification attempt.

The original Windows B trace at `9ad11bb` starts its L-ANON maximum-gap point
after 5,833 native executions. Its first measured plain medians for L-ANON,
V-LONGEXPR and V-FLAT were about 1.76, 1.47 and 1.51 times Windows A's, based
on only three retained samples each. Earlier short diagnostics did not replay
this prefix. This supports testing accumulated host/workload conditions; it
does not establish scheduler interference or CPU affinity as the cause.

`scripts/qualify/etw-prelude.json` freezes that exact ordered command tuple
prefix, derived from run 36374461333's Windows `runs.jsonl` (SHA-256
`60d981591a6ab33d8ad4dab7eb4dad95b8e8457f12352854d118f3db29bcd307`).
The same generated inputs, scheduled probes and baseline references replay
with tracing inactive. Then stock plain probes execute eight reference calls:
L-ANON, V-FLAT and V-LONGEXPR 1 MiB twice each, followed by the two existing
short witnesses once each. The eight calls repeat under one trace with a
separate QPC-marker probe; eight final stock calls follow verified absence of
our owned trace session. They are time-ordered references, not a randomized
ETW-overhead or affinity A/B experiment. Plain/allocator probe byte identity
against the pre-instrumentation source remains mandatory.

The native collector enables only CSwitch, Dispatcher ReadyThread and
NO_SYSCONFIG, uses raw QPC timestamps, and decodes documented numeric prefixes.
It records no ETL, process/thread-start, image, stack or system-configuration
payload. Requested ETW buffers total 16 MiB; the fixed numeric array is under
24 MiB. Actual settings, loss, malformed records and overflow are checked.
Only target-phase derived durations, bounded metadata, identities and hashes
are uploaded; the numeric trace remains inside the disposable VM.

Before the prefix, two live negative controls deliberately crash/stall the
collector. Each must prove termination and GUID-bound cleanup of its own
session; a collision or cleanup failure stops further work. The collector's
measurement self-stop is 30 seconds, its separate existing safety-profile
Job watchdog 40 seconds, outer grace five seconds, cleanup watchdog two
seconds plus five-second grace. Each control reserves 13 seconds and the
measurement reserves 60 seconds (86 total). Conservative parent-clock bounds
include launch through confirmed session absence. Missing absence evidence is
FAIL with unknown final lifetime, never a claim of compliance with 120 seconds.
Original qualification supervisor limits and source remain unchanged.

Offline controls cover decoding, interval state consistency, loss/overflow,
probe/collector failure, stop-file write failure and cleanup failure. Only the
preassigned first-attempt hosted Windows job can activate tracing; local checks
never activate ETW. The workflow uses explicit dispatch with an expected-commit
input, no push trigger. Both workflow and runner bind the exact reviewed commit.
There is one authorized dispatch; a further explicit dispatch needs new scope.

Implementation review found two P1 and two P2 items: a stop-file write exception
could skip cleanup; push triggers could unintentionally repeat ETW; target
switches sharing marker ticks were discarded; future schema versions were
accepted without a layout check. Remediation retains stop-write failure while
continuing cleanup, removes automatic triggers, rejects ambiguous boundary
ticks and permits only documented Thread_V2 24-byte CSwitch/8-byte ReadyThread.
It also requires target switch-in before parse and switch-out after cleanup;
individual phases may correctly contain no switch. All have planted-defect
controls. Independent re-review closed all four items with no additional P1/P2.
Local native evidence (20 tests), CLI controls (12), C codec controls, stock and
extended supervisor controls (seven each), V0 and diff checks passed. Plain and
allocator binaries match the earlier source byte for byte; a native marker
observation's QPC durations match its original timing fields. Local ETW entry
was rejected before launching anything. Hosted lifecycle checks remain unrun.

GitHub's [dispatch documentation](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#workflow_dispatch)
allows CLI/API dispatch against a branch after a workflow has run at least once;
this repository already has registered workflow ID `368659596`. The exact
commit and one dispatch are recorded in issue 11 before execution.

Interpretation: target CSwitch/ReadyThread events distinguish scheduled,
ready, waiting and unknown intervals, bound to the probe's PID/creation identity,
TID and QPC phase markers. Scheduled duration is not CPU execution time: ISR,
DPC and hypervisor pauses are outside this collection's attribution. Boundary
thread-CPU counters are complementary and have finite granularity. Lack of
reproduction remains inconclusive and does not close the earlier FAILs.

Official references checked 2026-09-28:
[StartTrace lifetime and system logger scope](https://learn.microsoft.com/en-us/windows/win32/api/evntrace/nf-evntrace-starttracew),
[buffer and EnableFlags properties](https://learn.microsoft.com/en-us/windows/win32/api/evntrace/ns-evntrace-event_trace_properties),
[CSwitch schema](https://learn.microsoft.com/en-us/windows/win32/etw/cswitch),
[ReadyThread schema](https://learn.microsoft.com/en-us/windows/win32/etw/readythread),
[QPC and affinity guidance](https://learn.microsoft.com/en-us/windows/win32/sysinfo/acquiring-high-resolution-time-stamps).

The single dispatch at `108401d` completed with diagnostic FAIL; the
[candidate report](../reports/0.1.4-native-parity-candidate.md#etw-run-108401d--diagnostic-fail-cleanup-verified)
records verified cleanup/buffer limits, the incomplete capture and exact raw
native audit. No retry is authorized by the one-job choice. Follow-up local
hardening records the first rejection's numeric descriptor without accepting
unknown schemas, stops additional probes after collector termination, and
rejects target transitions within +/-1 QPC tick of phase boundaries. A short
compatibility-only capture is a proposed new scope; it requires a separate
owner choice before activation. Historical FAILs and the 100 ms bounds stand.

The owner subsequently approved exactly one compatibility-only job: Windows
ephemeral VM, 10 minutes overall, one capture session with launch-through-
confirmed-cleanup bounded by 60 seconds, 64 MiB capture buffer limit. It builds
and offline-checks the existing collector under the checked Job supervisor,
requests one second of collection, and retains the existing self-stop/watchdog/
cleanup reservation. It runs zero parser probes and no 5,833-run prefix.
Capture rejection remains FAIL; its four unsigned first-rejection fields are
the intended evidence. The exact commit must be preassigned before the one
explicit dispatch. No raw trace is uploaded; no full latency or qualification
rerun is included in this additional authorization.

Independent static implementation review found no P1/P2 in this mode. Local
native evidence controls (21 tests), CLI controls (12), V0 and diff checks
passed. The one-second request does not guarantee every event shape appears;
no rejection would leave the earlier decoder failure unexplained. Rejection
collects its descriptor while preserving the failed capture verdict.

Compatibility run `36388250168` identified the first rejected shape as
CSwitch `(opcode=36, version=5, length=28)`; its session was cleaned up within
1.0535505 seconds, with no parser executions or raw publication. The
[retained receipt and primary implementation basis](../reports/0.1.4-native-parity-candidate.md#compatibility-run-7413acb--first-rejection-identified)
support adding that exact shape, without admitting arbitrary future versions
or interpreting its added tail. Local positive/negative codec controls pass;
hosted validation of the correction remains unrun. The authorized compatibility
job is complete and is not repeated automatically.

After the v5 correction, the owner authorized continued cause-specific fixes
and additional diagnostics until the diagnostic succeeds. Each execution
retains the original 30-minute Windows job, 120-second cumulative trace/
cleanup, 64 MiB capture-buffer and raw-nonpublication limits. Each candidate
is independently reviewed, checked locally, preassigned by exact commit and
explicitly dispatched. A new execution requires a material correction or new
discriminating evidence; unchanged lucky retries and historical FAIL replacement
remain prohibited. Diagnostic success alone does not release the parser.

### Follow-up after same-job stock L-ANON reproduction

The corrected `5b59373` diagnostic completed, with two stock L-ANON gaps above
100 ms; its separate traced calls were below 100 ms. The
[receipt](../reports/0.1.4-native-parity-candidate.md#corrected-etw-run-5b59373--diagnostic-complete-latency-reproduced)
preserves both facts. An independent adversarial design review approved one
new discriminating execution: retain the exact 5,833-run prefix, increase
only the fixed L-ANON target count from two to twenty, and retain the other
six targets. Before/traced/after each contain all 26 targets, totaling 5,911
native executions. All records count; no warmups or outliers are discarded.

Keep the existing 15-second measurement launch deadline, collector self-stop,
60-second capture lifecycle reservation, 120-second cumulative session bound,
30-minute job and 64 MiB buffer limit. Runtime duration estimates are not a
guarantee. Deadline exhaustion remains FAIL, with no target reduction or cap
increase. Preassign one exact candidate and first-attempt dispatch after
implementation review. If a traced L-ANON gap exceeds 100 ms, interpret only
that execution's gap. Non-reproduction or incomplete capture leaves the cause
unresolved. Ordered stock/traced groups do not establish overhead or affinity
causality. Historical failures, the earlier complete diagnostic and release
HOLD remain preserved.

The preassigned `519f18d` follow-up completed all 5,911 registrations and
classified a same-execution 100.6212 ms L-ANON gap as scheduled 97.6292 ms
and ready 2.9920 ms. The
[retained result](../reports/0.1.4-native-parity-candidate.md#targeted-etw-run-519f18d--same-execution-gap-classified)
records coverage, bounds, normal exits and the independent interpretation
review. This fulfills the follow-up's diagnostic purpose, not the release
gate. Exact runtime-operation attribution and a verified correction remain
open. Do not repeat the unchanged ETW campaign after this completion.

### Product requirement clarification: background analysis

The owner identified background code analysis and indexing as the primary
consumer use case. The inherited 100 ms response criteria were adopted by
the earlier Gate A; the examined canonical history does not derive that
number from a consuming application's required cancellation deadline.
The owner also confirmed that no required cancellation/termination time has
yet been set. Record that requirement as unspecified; do not invent a new
numerical bound from the observed failure times.
This clarification does not change any current gate, authorize a threshold
increase or convert a failure into PASS. A future product-contract proposal
must state the required end-to-end cancellation deadline and ownership of
the worker/supervisor, alongside throughput, scaling and memory objectives.
The 17 agreed validation purposes remain in scope. Cross-OS functional
agreement does not imply an identical maximum wall time on hosted VMs.
