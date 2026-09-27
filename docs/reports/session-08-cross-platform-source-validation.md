# Session 08 — source platform validation

Status at the time: session branch candidate. This work validated the existing
v0.1.2 grammar source on additional hosts without changing the v0.1.2 tag or
assets. It was later integrated into the
[v0.1.3 source release](0.1.3-release-candidate.md), which also bumped version
metadata. The grammar, scanner, queries, public tree and ABI remained unchanged.

## Target and evidence

The source distribution targets Windows x64 first, Linux x64 and macOS 15
Apple Silicon ARM64. macOS Intel, other Linux architectures and other OS
versions are outside this session's verified matrix. The common CI runs native
builds and V0–V5/V10 checks on each target. The Windows-only 17-gate release
qualification lane is not ported.

| Commit | CI | Windows x64 | Ubuntu x64 | macOS 15 ARM64 |
|---|---|---|---|---|
| `0af3be3216774c2d0d841d8484d853785935add5` | [run 36333717334](https://github.com/wotjr1649/tree-sitter-brightscript/actions/runs/36333717334) | PASS | PASS | FAIL: archive escape in the offline maintenance control |
| `95461fd1e975e0d63d3c15e9324d0e8fe1210e08` | [run 36333973244](https://github.com/wotjr1649/tree-sitter-brightscript/actions/runs/36333973244) | PASS | PASS | PASS |

The successful jobs used `windows-2025-vs2026` x64, `ubuntu-24.04` x64 and
`macos-15-arm64` images with CPython 3.14.7. Each job reported the expected
0.27.0 platform CLI identity before running parser checks.

The first macOS failure came from a valid archive extracted under the runner's
`/var` path. `Path.resolve()` changed that path to `/private/var`, but the
escape check compared it with the unresolved output root. The second commit
resolves that caller-owned root after validating every ZIP member and before
writing files. The existing hostile archive cases and the valid extraction
case pass on all three CI hosts. The archive bounds, member checks and escape
check remain in force.

The pinned Tree-sitter 0.27.0 macOS ARM64 gzip matched the official release
SHA-256. The decompressed binary hash is recorded in
`docs/provenance/upstream-sources.md`; macOS CI verified its installed copy
before executing it. The runner used CPython 3.14.7 for ARM64. Linux reports
`ru_maxrss` in KiB and macOS reports it in bytes, so V10 now converts each
value to bytes before applying the existing memory limits.

The successful CI run completed generator identity and regeneration (V0–V1),
registry, corpus, samples, queries and incremental checks (V2–V5), recovery,
scaling and fuzz checks (V10), and the offline public replay on every host.
These are observations for the named commit, inputs, runner images and pinned
Tree-sitter toolchain (source level L3). They do not expand Roku syntax
authority (L1), prove device behavior (V8) or establish Go parity (V9).

## Performance and limits

Each host ran the same V10 recovery and query scaling guards with their
unchanged time, memory-growth and exponent limits. This is OS-specific
regression evidence on the registered inputs, not a comparison of raw
milliseconds across different CPUs. No new 17-gate timing campaign, paired
cross-OS benchmark or cross-compiled binary artifact was produced. Windows
remains the only host of the full release qualification lane. A clean CI run
does not prove every Linux distribution, macOS version or BrightScript input.

The work is tracked by [milestone 1](https://github.com/wotjr1649/tree-sitter-brightscript/milestone/1)
and [issues 1–3](https://github.com/wotjr1649/tree-sitter-brightscript/issues).
The published v0.1.2 release and its original Windows/Ubuntu evidence remain
frozen; this is post-release source validation on a session branch.
