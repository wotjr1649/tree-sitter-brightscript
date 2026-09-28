# Roadmap

## Current maturity

v0.1.4 was released on 2026-09-28 KST
([release record](reports/0.1.4-release.md)). All 17 native purposes passed in
two independent jobs per supported OS: Windows x64, Ubuntu 24.04 x64 and
macOS 15 ARM64. Registered functional outcomes agree exactly across six jobs;
source-only distribution now includes a nonbinary evidence ZIP. The earlier
[Session 08 source validation](reports/session-08-cross-platform-source-validation.md)
was post-v0.1.2 evidence; it did not change that release's identity.
The [maintenance freeze](maintenance.md) takes effect after final documentation
CI and handoff; only its concrete triggers reopen triage.
The [v0.1.4 candidate investigation](reports/0.1.4-native-parity-candidate.md)
preserves earlier HOLD/FAIL results. The final v6 contract uses the owner's
250 ms response and cooperative-completion choices. Published v0.1.3 and
earlier identities remain unchanged.

The phases below record the original development roadmap, not automatic next tasks.
Past holds and failed campaigns remain in [qualification history](reports/0.1.0-integrated-qualification.md).
Go integration, device evidence and 1.0 features are not follow-up obligations of this maintenance patch.

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
  2-dependent requirements stay `provisional` or `unresolved`. Any device work needs separate scope and authority.
- Language bindings and WASM artifacts: added only for a named consumer.
- Roku OS compatibility checking: outside this repository's scope.
