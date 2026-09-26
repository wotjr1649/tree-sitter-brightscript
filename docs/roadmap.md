# Roadmap

## Current maturity

Grammar version 0.1.0: release candidate (Session 03), independently
audited in Session 04 ([reports/0.1.0-release-audit.md](reports/0.1.0-release-audit.md)),
release-frozen in Session 05 ([reports/0.1.0-release.md](reports/0.1.0-release.md));
Session 05-1 isolated the final-review finding B-01, fixed the
unclosed-call recovery family and the recovery memory of two others (`^` and
PRINT items) found by its re-audits, and disclosed the remaining
quadratic-time recovery behaviour as the class KL-002. Its round-5 re-audit
found three release-blocking findings, and Session 05-1 ended on hold: 0.1.0
is not released ([reports/0.1.0-release.md](reports/0.1.0-release.md#status-hold)).
Sessions 05-2 and 07 found four more material findings and Session 05-3
fixed part of one (member and attribute chains in the highlight query); all
seven stayed open ([reports/0.1.0-structural-recovery-safety.md](reports/0.1.0-structural-recovery-safety.md)).
Session 05-7 re-froze the public schema before the first release
(ADR-0007), added the error-recovery scanner (ADR-0008) and qualified one
candidate that closes all seven and retires KL-002 on the stock runtime
([reports/0.1.0-integrated-qualification.md](reports/0.1.0-integrated-qualification.md));
its release awaits the owner's decision.
The 0.1.0 release will be the commit identified by the `v0.1.0` tag and its
GitHub Release once they are published; no package is published.
Phases 1–5 have their exit evidence in
[reports/0.1.0-release-candidate.md](reports/0.1.0-release-candidate.md) and
the release record. Phase 6 was tried on a local `go-treesitter` branch that
is neither merged nor pushed; it did not pass V9 (recovery-tree differences in
the Go runtime), so no pin change is proposed there, and it is the next piece
of work, in that repository, on the released identity. Phase 7 is later work.

## Phases

| Phase | Scope | Exit evidence |
|---|---|---|
| 1. Foundation | Repository contract, provenance, validation and architecture decisions | Contracts merged to `main` (Session 01) |
| 2. Requirement inventory | Promote the local research inventory (`_ref/normative/roku-docs/notes/`) into `BS-*` requirements with evidence, `since` and status; map ambiguities; derive tree-shape constraints; plan grammar work packages | Populated registry in `docs/specs/language-conformance.md`; `docs/specs/grammar-design.md`; planned schema in `docs/specs/tree-schema.md`; `docs/validation/workload-matrix.md` (Session 02) |
| 3. Grammar bootstrap | Select and verify the generator ([ADR-0002](design/decisions/ADR-0002-generator-pin-and-generated-artifacts.md)); add `grammar.js`, `tree-sitter.json`, tool metadata, drift check; lexical core | V0–V2 passing for the implemented core |
| 4. Grammar build-out | Statements, expressions, functions, arrays and associative arrays, error handling, conditional compilation and its spike ([ADR-0004](design/decisions/ADR-0004-conditional-compilation-representation.md)), requirement by requirement, in the order of `docs/specs/grammar-design.md` §15 | V1–V5 per requirement |
| 5. First release (0.x) | `highlights.scm`, native oracle records, robustness on pathological input, release identity | v0.x gates in `docs/validation/validation.md` |
| 6. Downstream integration | Replace the legacy pin in `go-treesitter` (separately authorized work in that repository) | V9 evidence in `go-treesitter` |
| 7. Toward 1.0 | `tags.scm`, Level 1 requirement coverage, frozen public tier, fuzzing | v1.0 gates in `docs/validation/validation.md` |

## Not planned

- Level 2 device campaign: no Roku device is available or planned. Level
  2-dependent requirements stay `provisional` or `unresolved`. Revisit if a
  device becomes available.
- Language bindings and WASM artifacts: added only for a named consumer.
- Roku OS compatibility checking: outside this repository's scope.
