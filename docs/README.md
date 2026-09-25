# Documentation map

Canonical documents are tracked here. Each rule has one home; other documents
link to it rather than restate it.

| Document | Purpose | Read when |
|---|---|---|
| [roadmap.md](roadmap.md) | Current maturity and planned phases | Orienting; planning a session |
| [design/architecture.md](design/architecture.md) | Pipeline, ownership, layout, principles, decision index | Starting any work |
| [design/decisions/](design/decisions/) | ADRs: why each architectural decision was made | Changing or questioning a decision |
| [specs/grammar-contract.md](specs/grammar-contract.md) | What the grammar promises; acceptance policy; non-goals | Designing or reviewing grammar rules |
| [specs/language-conformance.md](specs/language-conformance.md) | Requirement IDs, record format, statuses, registry, reconciliations | Adding requirements, rules or fixtures |
| [specs/grammar-design.md](specs/grammar-design.md) | Planned tokens, rule families, precedence, statement boundaries, conditional-compilation spike, implementation order | Writing or changing `grammar.js` |
| [specs/tree-schema.md](specs/tree-schema.md) | Public tree policy, naming, versioning, node catalogue | Adding or changing nodes, fields or queries |
| [provenance/source-policy.md](provenance/source-policy.md) | Source levels (L1–L5), citation, promotion, refresh | Using any source |
| [provenance/upstream-sources.md](provenance/upstream-sources.md) | Dated identities of sources and toolchain | Citing a source; refreshing; selecting the generator |
| [validation/validation.md](validation/validation.md) | Validation levels (V0–V10), gates, V0 checklist, failure handling, Level 2 policy | Claiming anything; closing a session; preparing a release |
| [validation/workload-matrix.md](validation/workload-matrix.md) | Validation sets W01–W14 and the catalogue of every corpus fixture | Writing fixtures; running V2–V10 |
| [validation/known-regressions.md](validation/known-regressions.md) | Defects of earlier grammars and the checks that prevent them | Reviewing grammar or generation changes |
| [reports/0.1.0-release-candidate.md](reports/0.1.0-release-candidate.md) | Release-candidate evidence, gate results and verdict for 0.1.0 | Checking what the candidate proves |
| [reports/0.1.0-release-audit.md](reports/0.1.0-release-audit.md) | Independent audit of the candidate, evidence remediation, reverification and promotion verdict | Checking the Session 04 audit |
| [reports/0.1.0-performance.md](reports/0.1.0-performance.md) | Measured parse, recovery, incremental, query and memory baseline of 0.1.0 | Judging performance or a performance change |
| [reports/0.1.0-comparative-conformance.md](reports/0.1.0-comparative-conformance.md) | 0.1.0 against the legacy grammar and BrighterScript, under official evidence | Claiming an improvement over earlier grammars |
| [reports/0.1.0-release.md](reports/0.1.0-release.md) | Final 0.1.0 release record: identity, gates, dispositions, limitations, verdict | Consuming or auditing the 0.1.0 release |
| [reports/0.1.0-structural-recovery-safety.md](reports/0.1.0-structural-recovery-safety.md) | Causes of the open 0.1.0 hold findings, candidates compared, stricter checks and the Gate A decision | Deciding how to remediate the 0.1.0 hold |
| [reports/session-05-3-repository-owned-hardening.md](reports/session-05-3-repository-owned-hardening.md) | The Session 05-3 query change, its role and time comparison, what stays open | Changing the highlight query |
| [reports/session-05-4-grammar-schema-stock-runtime.md](reports/session-05-4-grammar-schema-stock-runtime.md) | Grammar and schema redesigns screened on the stock runtime, why none qualified, what stays open | Considering a grammar or public-tree change for the 0.1.0 hold |

Repository-wide operating rules for contributors and coding agents are in
`AGENTS.md` at the repository root.

## Canonical and local material

Canonical: everything above, `README.md`, `AGENTS.md`, `LICENSE`.

Local and Git-ignored: `_ref/`, `docs/prompts/`, `docs/plans/`,
`artifacts/`, `.work/`. Local material is evidence or working notes. It never becomes a
requirement unless its content is promoted into a canonical document.

## Changing a contract

A change to a durable contract updates its canonical document in the same work
unit. A changed architectural decision gets a new or superseding ADR.
