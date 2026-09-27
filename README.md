# tree-sitter-brightscript

An independent, specification-driven Tree-sitter grammar for Roku BrightScript.

This project aims to provide a current, well-tested BrightScript syntax grammar based on Roku's official developer documentation, with reproducible generated parser artifacts and explicit conformance evidence.

> [!IMPORTANT]
> This project is not affiliated with or endorsed by Roku.
>
> BrightScript language syntax is defined here from documented language behavior and independently authored tests. Legacy Tree-sitter BrightScript grammars and community parsers may be used as non-normative comparison evidence, but are not the specification authority for this implementation.

## Status

[v0.1.1](https://github.com/wotjr1649/tree-sitter-brightscript/releases/tag/v0.1.1)
was released and publicly verified on 2026-09-27. The [release record](docs/reports/0.1.1-maintenance-release.md)
identifies the documentation, verification-tool and version-metadata maintenance, with language behaviour preserved.
Anonymous downloads matched all five approved assets, and the downloaded source passed its build and smoke checks.
The [maintenance freeze](docs/maintenance.md) is active until a documented trigger requires triage.

The grammar covers the listed requirements and fixtures in the [registry](docs/specs/language-conformance.md).
Provisional, tolerated and unresolved classifications remain disclosed. Validation is not proof of complete
Roku syntax or device compatibility. The [0.1.0 release record](docs/reports/0.1.0-release.md#release-v010)
and [qualification history](docs/reports/0.1.0-integrated-qualification.md) preserve earlier failures and their disposition.
No npm package, language binding or WASM artifact is shipped.

## Use and verification

Consumers use `src/parser.c`, `src/scanner.c` and `src/tree_sitter/`, with
`queries/highlights.scm` for highlighting. Include the scanner when building the native grammar.
For this source checkout, install the locked development generator with `npm ci`, then run
`python scripts/check_generated.py` and `python scripts/tscli.py test`.
The verified CLI uses private binary, configuration and parser-library paths.
The full check list and the limits of each claim are in [validation](docs/validation/validation.md).

## Goals

The project is intended to:

- cover the currently documented Roku BrightScript language syntax;
- preserve case-insensitive BrightScript lexical behavior;
- produce stable and structurally useful Tree-sitter parse trees;
- maintain a traceable mapping from documented language features to grammar rules and tests;
- reject generated-artifact drift between `grammar.js` and `src/`;
- provide Tree-sitter queries for highlighting and structural tooling;
- support deterministic validation against the native Tree-sitter runtime;
- provide a reproducible grammar source for `github.com/wotjr1649/go-treesitter`.

This repository defines syntax. Roku APIs, SceneGraph APIs, runtime type behavior, semantic resolution, and target-device compatibility are outside the grammar's responsibility unless explicitly documented as syntax constraints.

## Source of truth

The normative language authority is Roku's official BrightScript developer documentation.

The detailed source hierarchy, citation rules and snapshot identities are recorded in [docs/provenance/](docs/provenance/source-policy.md).

Community implementations such as BrighterScript may be used for differential testing. They do not override documented Roku syntax.

## Repository model

`grammar.js` is the canonical grammar source.

Generated Tree-sitter artifacts under `src/`, including `parser.c`, `grammar.json`, and `node-types.json`, are committed to the repository and must be reproducible from the pinned Tree-sitter generator, an exact stable release.

Changes to the grammar must update the relevant corpus and conformance tests in the same verified work unit.

No language bindings are shipped initially; consumers use the generated `src/` files directly.

## Validation

A grammar change is not considered validated merely because `tree-sitter generate` succeeds.

Validation is layered and includes:

- generated-artifact consistency;
- Tree-sitter corpus tests;
- specification-derived valid and invalid conformance fixtures;
- query compilation;
- recovery behavior;
- incremental-versus-fresh parsing checks;
- native Tree-sitter oracle comparison where required;
- downstream `go-treesitter` integration checks where required.

The authoritative validation contract is [docs/validation/validation.md](docs/validation/validation.md).

## go-treesitter integration

This repository produces the native grammar sources. The downstream scanner port and V9 evidence
belong to `go-treesitter` under [ADR-0006](docs/design/decisions/ADR-0006-downstream-integration-boundary.md).
The earlier unsuccessful integration record stays historical; this maintenance patch makes no Go compatibility claim.

## Documentation

Start with [docs/README.md](docs/README.md) for the documentation map. Contributors and coding agents follow [AGENTS.md](AGENTS.md).

Canonical specifications live in `docs/specs/`, architecture and decisions in `docs/design/`, provenance in `docs/provenance/`, and validation contracts in `docs/validation/`.

Session prompts, temporary plans, raw evidence, local reference repositories, and development artifacts are intentionally excluded from Git.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).
