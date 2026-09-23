# ADR-0006 — Downstream integration boundary

Status: Accepted
Date: 2026-09-23

## Context

`go-treesitter` is a CGO-free Go syntax layer. It consumes grammars by
converting a checked-in `src/parser.c` with `ts2go`, not through a cgo
language binding. It currently pins the legacy BrightScript grammar at
`253fdfaa`, whose license metadata conflicts. Its C oracle runtime (v0.25.1)
accepts ABI 13–15, and it already consumes an ABI 15 parser
(`tree-sitter-python`); whether `ts2go` accepts every ABI 15 feature this
grammar will use is not yet verified.

## Decision

1. The integration contract is the generated grammar at a commit: `src/*`
   generated files and shipped queries, plus the identity (commit, generator
   version, ABI, file hashes).
2. No cgo Go binding is part of the contract. A Go binding, if ever added, is
   optional and secondary.
3. Downstream tooling, conversions and oracle records for `go-treesitter` stay
   in `go-treesitter`. V9 evidence is produced there; this repository may cite
   it.
4. Order of evidence: native Tree-sitter correctness for an identity first,
   then downstream parity for the same identity.
5. A downstream mismatch is an integration or runtime issue until evidence
   shows the grammar is wrong. The grammar is never changed to hide a
   downstream defect.
6. Replacing the legacy pin is a change in `go-treesitter`, made only when a
   task explicitly authorizes work there.

## Alternatives considered

- **Integrated monorepo with downstream tools here** — rejected: couples the
  grammar to one consumer and risks that consumer becoming the syntax
  authority.
- **cgo Go binding as the contract** — rejected: incompatible with the
  downstream CGO-free architecture.

## Consequences

- Each new grammar identity needs fresh downstream evidence.
- External scanners carry downstream cost ([ADR-0005](ADR-0005-external-scanner-policy.md)).

## Validation / enforcement

- Release identities are recorded so downstream can pin them exactly.
- Review rejects grammar changes justified only by downstream behaviour.

## Revisit conditions

- `go-treesitter` changes how it ingests grammars.
- A second downstream consumer needs a different artifact.
