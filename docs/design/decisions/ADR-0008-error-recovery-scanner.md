# ADR-0008 — Error-recovery scanner for resource safety

Status: Accepted as a design principle. Implementation eligibility: Pending
until the release evidence of the implementing candidate exists
(`docs/reports/0.1.0-integrated-qualification.md`, written with that candidate).
Date: 2026-09-26
Supersedes in part: [ADR-0005](ADR-0005-external-scanner-policy.md) (see Decision 7)

## Context

- The seven open 0.1.0 findings are resource failures, not syntax gaps
  ([0.1.0-structural-recovery-safety.md](../../reports/0.1.0-structural-recovery-safety.md)).
  Their mechanisms are in the stock runtime 0.27.0: error recovery keeps
  equal-cost alternatives whose paths the end-of-input step copies (B5-01),
  stack nodes of those alternatives are released recursively (B5-02), and the
  query cursor scans later siblings of every visible node for a named one,
  which is quadratic in an `ERROR` node with many anonymous children
  (S07-M03). Each is triggered by long runs of malformed tokens that recovery
  handles one token at a time, or by long runs of anonymous tokens left on
  the parse stack.
- The runtime is pinned and not patched ([ADR-0002](ADR-0002-generator-pin-and-generated-artifacts.md));
  consumers use stock runtimes. Grammar-only redesigns (Session 05-4) and a
  generation recipe (Session 05-5) did not close the findings together.
- ADR-0005 admits a scanner only for a `BS-*` requirement that grammar rules
  cannot express. Every documented form is expressible without one; that
  stays true. The need here is bounded resource use of error recovery.
- Session 05-6 built an experimental scanner (source SHA-256 `8724b8d9…`) that
  turns only an ASCII `+` into an unusable token during recovery. On the
  registered `x = ` + `+f([)`×400 input it cut the recovery from 496 ms and
  152 MiB to 6 ms and 1.4 MiB on the same generated parser, but it covers one
  character, and on a KL-002 input it changed the recovery shape (one `ERROR`
  plus 249 `MISSING` nodes instead of 250 `ERROR` nodes). It is research
  evidence, not product evidence.
- In Tree-sitter every external token is valid while the parser is in its
  error state, and only then when the grammar uses a token nowhere
  (Level 3: `lib/src/parser.c` at `v0.27.0`, lexing with the error state's
  lex mode). A scanner can therefore know that recovery is running without
  any private runtime access.

## Decision

1. `src/scanner.c` may exist for the resource safety of error recovery. It
   produces no token while a parse is valid; every BrightScript form stays
   expressed by `grammar.js` alone.
2. The scanner acts only when a sentinel external token, used by no grammar
   rule, is valid, which happens only in the error state.
3. It then returns one of two tokens:
   - a **recovery run**: the rest of the physical line, stopping before a
     line break (`LF` or `CR LF`), before a `'` comment outside a string
     literal, or at end of input; never empty;
   - a **recovery line break**: a line break that the grammar accepts only
     where a line of statements may end, not as the terminator of a block
     header and not inside brackets.
   A malformed line then becomes one `ERROR` node that keeps the native
   children of the tokens parsed before the error, and parsing resumes at the
   next line when a statement boundary is within reach of recovery.
4. Tokens that can stay unreduced on the parse stack in long runs without a
   named node between them (the openers `(` and `[`, the prefix operators
   `-`, `+` and `not`, and `try`) get named raw forms that appear only inside
   `ERROR` nodes; every valid tree still shows them under their anonymous
   names. A hidden rule that starts with a second never-produced external
   token lists the raw forms, so that the generator keeps their names, and is
   placed so that no public node lists them as children. The raw names are
   public, documented in tree-schema.md as error-only.
5. The scanner is stateless: `create` returns no payload, `serialize` writes
   no bytes, `deserialize` ignores its input. It allocates nothing, does not
   call `get_column`, does not recurse, and each successful scan advances at
   least one character; a scan is bounded by the length of one line.
6. `src/scanner.c` is hand-written canonical source under the MIT license
   (public `TSLexer` API only, no private runtime structures, no debug output
   or environment dependence in normal builds). It is not a generated file:
   the drift check covers the generator's files and records the scanner's
   hash separately.
7. For this purpose, ADR-0005's first requirement (the `BS-*` requirements
   that need a scanner) is replaced by the resource-safety evidence of the
   implementing candidate. Its other requirements stay: scanner-free
   alternatives and why they failed (Context), the state design (Decision 5),
   incremental tests across scanner decisions, native parity, a
   `go-treesitter` analysis (Consequences) and fuzzing and error-recovery
   results. A scanner for any other purpose still needs a new ADR under
   ADR-0005.

## Alternatives considered

- **No scanner, grammar changes only** — tried in Session 05-4; no candidate
  passed the checks together.
- **A patched runtime** — rejected: consumers use stock runtimes and the pin
  is not changed.
- **A different generation recipe** (`--disable-optimizations`, Session 05-5)
  — reduced one family only.
- **Token-class recovery** (the Session 05-6 idea extended to more
  characters) — kept as the fallback strategy: it changes recovery only for
  the listed characters, and a character list is not a bounded argument.
- **Line-level recovery without the recovery line break** — rejected after a
  trial: recovery resumed inside an open bracket, so the next line was parsed
  as part of an array.
- **Hidden raw token forms** — rejected after a trial: the generator turns a
  hidden single-string rule into a nonterminal, which changes valid trees.
- **A Rust, Wasm or separate-process parser** — out of scope.

## Consequences

- Recovery trees change: a malformed line is one `ERROR` node instead of
  several local ones. Recovery trees are not contractual
  ([grammar-contract.md](../../specs/grammar-contract.md) §6), but native
  `ERROR`/`MISSING` nodes, source coverage, the lines after an error and the
  repair to a valid state are checked.
- When the parse stack holds more unclosed constructs than the runtime's
  recovery summary reaches (16 entries), recovery cannot return to a
  statement boundary; the following lines are absorbed, as without a scanner.
- `go-treesitter` needs a Go port of the scanner. It carries hand-written Go
  scanners for other grammars (`Scan(payload, lexer, validSymbols)`), and
  `ts2go` converts only `parser.c`. This scanner is stateless and uses only
  `lookahead`, `advance`, `mark_end`, `eof` and `result_symbol`; input and
  output golden cases for the port are kept here. The port and its V9
  evidence belong to `go-treesitter`.

## Validation / enforcement

- Attribution runs compare the same generated parser with a no-op and the
  active scanner, and the previous and the new grammar.
- Incremental and fresh parses agree across edits that create or remove a
  recovery run; repaired text parses as the valid tree; a cancelled parse
  resumes and resets correctly; two parsers are independent.
- Scanner unit cases cover `LF`, `CR LF`, a lone `CR`, end of input, a NUL
  byte, UTF-8 text and string literals containing `'`.
- `scripts/check_generated.py` requires this ADR for `src/scanner.c` and an
  `externals` list in `grammar.js`.

## Revisit conditions

- A stock runtime release bounds recovery paths, releases stack nodes
  iteratively and makes the sibling scan linear.
- A consumer cannot load a grammar with an external scanner.
