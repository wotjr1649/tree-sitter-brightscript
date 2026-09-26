# ADR-0007 — Pre-release schema re-freeze of 0.1.0

Status: Accepted
Date: 2026-09-26

## Context

- Grammar version 0.1.0 has never been published: on 2026-09-26 the
  repository has no tag and no GitHub Release, and no package is published
  ([roadmap.md](../../roadmap.md)). The release is on hold with seven open
  findings (B5-01, B5-02, A5-01, S07-M01, S07-M02, S07-M03, S08-M01;
  [0.1.0-structural-recovery-safety.md](../../reports/0.1.0-structural-recovery-safety.md)).
- The versioning table in [tree-schema.md](../../specs/tree-schema.md) governs
  changes between published versions. It does not say whether the public tier
  of a version that was frozen but never published may still change.
- Session 05-4 showed that some findings depend on the public tree shape on
  the stock runtime: a highlight query cannot stay linear on method-call
  chains while the called name and its argument list are not siblings
  ([session-05-4-grammar-schema-stock-runtime.md](../../reports/session-05-4-grammar-schema-stock-runtime.md)).
- The release-candidate line (Sessions 05-1 to 05-4) lives on
  `session/05-4-grammar-schema-stock-runtime` at `47d4047`; `main` is at
  `2aeb29d`, an ancestor that predates that line.

## Decision

1. Until 0.1.0 is first published (its `v0.1.0` tag or GitHub Release exists),
   the public tier may be re-frozen for the resource-safety work of
   [ADR-0008](ADR-0008-error-recovery-scanner.md) and the open findings. The
   version stays 0.1.0.
2. A re-freeze change is made like any public-tier change: the catalogue in
   tree-schema.md, the reviewed `node-types.json` diff, the fixtures and the
   queries change in the same commit.
3. Every `documented`, `provisional` and `tolerated` form keeps its
   acceptance, and every change preserves the syntactic information of the
   old tree: operator binding and associativity, postfix order, PRINT item
   boundaries, statement structure and source spans. Preservation is checked
   against a common projection of old and new trees and against
   specification-derived expectations, not against old tree hashes.
4. Changed expectations in the corpus are rewritten from the specification;
   `tree-sitter test --update` is not used.
5. After the first publication the versioning table of tree-schema.md applies
   unchanged.
6. The work continues on one branch created from `47d4047`
   (`session/05-7-integrated-release-development`), an exception to the rule
   in `AGENTS.md` that session branches start from `main`: the release line
   has not been merged into `main`. The finished candidate is merged into
   `main` with `--no-ff` only after its release approval.

## Alternatives considered

- **Keep the frozen shape and publish with the findings disclosed** —
  rejected by the release gates: the findings are blocking and no limitation
  covers them.
- **Publish 0.1.0 unchanged, then change the tree in 0.2.0** — would publish a
  release whose gates fail.
- **Bump to 0.2.0 before any publication** — rejected: no consumer has
  received 0.1.0, so a new number would only record internal history.

## Consequences

- `node-types.json`, the W12 native records and the generated-file identities
  of 0.1.0 change; earlier records stay as history for their identities.
- `go-treesitter` needs fresh V9 evidence for the new identity
  ([ADR-0006](ADR-0006-downstream-integration-boundary.md)).

## Validation / enforcement

- `scripts/check_schema.py` reconciles the catalogue with `node-types.json`.
- The projection comparison and its mutants are part of the release evidence.
- The absence of a `v0.1.0` tag and GitHub Release is rechecked before the
  release approval.

## Revisit conditions

- 0.1.0 is published (this ADR then no longer permits changes).
