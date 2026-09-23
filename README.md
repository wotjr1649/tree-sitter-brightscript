# tree-sitter-brightscript

An independent, specification-driven Tree-sitter grammar for Roku BrightScript.

This project aims to provide a current, well-tested BrightScript syntax grammar based on Roku's official developer documentation, with reproducible generated parser artifacts and explicit conformance evidence.

> [!IMPORTANT]
> This project is not affiliated with or endorsed by Roku.
>
> BrightScript language syntax is defined here from documented language behavior and independently authored tests. Legacy Tree-sitter BrightScript grammars and community parsers may be used as non-normative comparison evidence, but are not the specification authority for this implementation.

## Status

Pre-implementation.

The repository currently contains its foundation contracts only. The grammar, generated parser, conformance corpus, queries and downstream `go-treesitter` integration do not exist yet, and no BrightScript syntax support is claimed. See [docs/roadmap.md](docs/roadmap.md).

No compatibility or completeness claim should be inferred until the corresponding release gate in [docs/validation/validation.md](docs/validation/validation.md) is met.

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

Once implementation begins, `grammar.js` is the canonical grammar source.

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

This repository is intended to be the grammar producer for `go-treesitter`.

`go-treesitter` converts a pinned, generated `src/parser.c` into its CGO-free grammar representation, so the Go integration path does not depend on any cgo language binding. It currently pins a different, legacy BrightScript grammar; switching it to this repository is future work in that repository.

Each release will bind its grammar identity to the source commit, generated parser identity, Tree-sitter generator identity, and validation evidence.

## Documentation

Start with [docs/README.md](docs/README.md) for the documentation map. Contributors and coding agents follow [AGENTS.md](AGENTS.md).

Canonical specifications live in `docs/specs/`, architecture and decisions in `docs/design/`, provenance in `docs/provenance/`, and validation contracts in `docs/validation/`.

Session prompts, temporary plans, raw evidence, local reference repositories, and development artifacts are intentionally excluded from Git.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).
