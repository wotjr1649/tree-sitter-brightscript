# Source policy

Defines which sources may establish what, how they are cited, how research
becomes a requirement, and how source drift is handled.

Decision record: [ADR-0001](../design/decisions/ADR-0001-specification-authority-and-independent-implementation.md).
Current source identities: [upstream-sources.md](upstream-sources.md).

## Source classes

| Level | Class | Source | Authoritative for | Never authoritative for |
|---|---|---|---|---|
| 1 | Normative | Roku official BrightScript documentation (`developer.roku.com`) | BrightScript language syntax | Tree-sitter behaviour |
| 2 | Official behaviour | Reproducible results from an official Roku device/compiler | Resolving ambiguity or gaps in Level 1 | Anything it was not observed to show |
| 3 | Toolchain | Official Tree-sitter repositories, documentation and grammars | Grammar DSL, generator, ABI, runtime, test and query semantics | BrightScript syntax |
| 4 | Comparative | BrighterScript and other community BrightScript tools (e.g. `brs`, `brs-engine`) | Discovering edge cases; differential testing; the basis for a `tolerated` status when the tool accepts the variant as plain BrightScript (never a BrighterScript-only extension) | Validity or invalidity of standard BrightScript |
| 5 | Historical | Legacy Tree-sitter BrightScript grammars | Defect discovery; regression candidates | Any requirement |
| — | Downstream | `go-treesitter` and other consumers | Nothing about syntax | Syntax, grammar design |

Rules:

- A lower level never silently overrides a higher one. A disagreement is
  recorded in the affected requirement record (see
  `docs/specs/language-conformance.md`); it is not settled by majority vote
  among community parsers.
- Absence of a construct from Level 1 is not evidence that it is invalid.
- Level 2 evidence is recorded only when it was actually produced; the
  collection policy is in `docs/validation/validation.md`.
- Secondary retellings (search summaries, blog posts, AI summaries) are not
  evidence. When one conflicts with a Level 1 snapshot, the snapshot wins and
  the retelling is discarded.

## Independent implementation

Lower-level implementations (Levels 4–5) may be inspected to find candidate
edge cases, suspected omissions, known defects and differential-test inputs.

Nothing may be copied from them into this repository: no grammar rules,
generated parser code, queries, corpus tests, bindings, documentation wording
or parse-tree design. Every grammar rule and fixture is written independently
from its requirement; Level 4 evidence may justify accepting a variant
(`tolerated`) but never supplies the implementation. Node names and structure
are chosen under `docs/specs/tree-schema.md`.

## Citation

- Cite Roku pages by canonical URL, page section, snapshot identity and
  retrieval date. Paraphrase; quote only short tokens or spellings.
- Do not commit raw Roku HTML or large documentation excerpts.
- Cite Tree-sitter, comparative and historical sources by repository URL and
  full commit SHA (plus tag or issue number where relevant).
- Raw evidence lives in the local, Git-ignored `_ref/` workspace. Its local
  labels (`LEX-01`, `AMB-20`, `VER-18`, …) are handles, not requirement IDs.

## Promotion of research into requirements

1. A research observation (for example a note under
   `_ref/normative/roku-docs/notes/`) identifies a testable syntax statement
   and its Level 1 source, or, for an undocumented variant, the Level 4 or
   Level 2 evidence that supports tolerating it.
2. The statement becomes a requirement record with a stable `BS-*` ID in
   `docs/specs/language-conformance.md`, carrying its evidence pointer,
   `since` version and status.
3. Grammar rules and fixtures cite that ID. Nothing is implemented from a
   research note that has not been promoted.

## Refresh and drift

- Refresh is manual and controlled. It is required before each release
  candidate and recommended before starting work on a grammar area whose pages
  may have changed. There is no scheduled automatic refresh.
- Documentation drift is detected with the content-region SHA-256 and the
  page-declared modification time recorded in
  [upstream-sources.md](upstream-sources.md). Whole-file hashes are not
  comparable across fetches because each response embeds request-specific
  data.
- A refresh stores a new dated snapshot beside the old one. A snapshot cited by
  a requirement is never overwritten until every citing record is reviewed.
- A changed content region triggers review of every requirement citing that
  page. Record the old identity, new identity and outcome in
  [upstream-sources.md](upstream-sources.md).
- Clone-based sources are refreshed by recording the new commit and reviewing
  the commit range; reference clones are never reset or modified in place.
