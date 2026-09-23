# Documentation map

Canonical documents are tracked here. Each rule has one home; other documents
link to it rather than restate it.

| Document | Purpose | Read when |
|---|---|---|
| [roadmap.md](roadmap.md) | Current maturity and planned phases | Orienting; planning a session |
| [design/architecture.md](design/architecture.md) | Pipeline, ownership, layout, principles, decision index | Starting any work |
| [design/decisions/](design/decisions/) | ADRs: why each architectural decision was made | Changing or questioning a decision |
| [specs/grammar-contract.md](specs/grammar-contract.md) | What the grammar promises; acceptance policy; non-goals | Designing or reviewing grammar rules |
| [specs/language-conformance.md](specs/language-conformance.md) | Requirement IDs, record format, statuses, registry | Adding requirements, rules or fixtures |
| [specs/tree-schema.md](specs/tree-schema.md) | Public tree policy, naming, versioning, node catalogue | Adding or changing nodes, fields or queries |
| [provenance/source-policy.md](provenance/source-policy.md) | Evidence levels, citation, promotion, refresh | Using any source |
| [provenance/upstream-sources.md](provenance/upstream-sources.md) | Dated identities of sources and toolchain | Citing a source; refreshing; selecting the generator |
| [validation/validation.md](validation/validation.md) | Evidence levels, gates, failure handling, Level 2 policy | Claiming anything; preparing a release |

Repository-wide operating rules for contributors and coding agents are in
`AGENTS.md` at the repository root.

## Canonical and local material

Canonical: everything above, `README.md`, `AGENTS.md`, `LICENSE`.

Local and Git-ignored: `_ref/`, `docs/prompts/`, `docs/plans/`,
`artifacts/`. Local material is evidence or working notes. It never becomes a
requirement unless its content is promoted into a canonical document.

## Changing a contract

A change to a durable contract updates its canonical document in the same work
unit. A changed architectural decision gets a new or superseding ADR.
