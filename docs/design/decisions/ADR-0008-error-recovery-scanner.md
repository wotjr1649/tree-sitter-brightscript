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
   - a **recovery run**: malformed text up to the end of the physical line,
     stopping before a line break (`LF` or `CR LF`), before a `'` comment
     outside a string literal, before a keyword that closes or continues a
     block (`END…`, `NEXT`, `ELSE…`, `CATCH`) or a `:` before one, and, on a
     last line without a line break, before its last unit (a word or one
     character) when the run holds 16 units or more; never empty;
   - a **recovery line break**: a line break, or that last unit, which the
     grammar accepts where a line of statements ends and after the header
     of a loop, function, TRY, CATCH or directive, not after an IF header
     (a single-line IF with an error would become a block IF) and not inside
     brackets.
   It returns nothing, so that recovery proceeds token by token as without
   the scanner, for a malformed rest of fewer than 16 units before a line
   that begins like a statement or at the end of input: a cheap run there
   lets a recovery version skip the line break and take the next line into
   the malformed statement, and at the end of input the unit that ends the
   line would lose its node. Only the last unit of a long last line without
   a line break is therefore outside every `ERROR` node, as a hidden line
   end.
   A long malformed line then becomes one `ERROR` node that keeps the native
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
5. The scanner keeps one state byte: set on a run that stopped before the
   last unit of the input, so that when recovery moves back to a line end
   and the runtime lexes that unit again in a normal state, the scanner
   returns it as the recovery line break there too (a valid parse has no
   run, so the byte is never set in one). `create` allocates the byte with
   the runtime's `ts_calloc`; `serialize` writes it only when set. The
   scanner does not call `get_column` (in runtime 0.27.0 it re-reads the
   line from its start, which made a line with many block keywords after an
   error quadratic; Session 05-7 review B2-01), does not recurse, and each
   successful scan advances at least one character; a scan is bounded by one
   line plus the blank lines and first character after it.
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
- **A run for every malformed rest of a line** (the first implementation,
  `cc664de`) — rejected after independent review (Session 05-7, A-01 and
  B-01): a recovery version skipped whole valid lines as cheap runs, so one
  stray token could hide the following blocks and subs, and on a last line
  without a line break the runtime's repair versions re-read the line once
  per repair (quadratic time).
- **Hidden raw token forms** — rejected after a trial: the generator turns a
  hidden single-string rule into a nonterminal, which changes valid trees.
- **A Rust, Wasm or separate-process parser** — out of scope.

## Consequences

- Recovery trees change: a long malformed line is one `ERROR` node instead
  of several local ones. Recovery trees are not contractual
  ([grammar-contract.md](../../specs/grammar-contract.md) §6), but native
  `ERROR`/`MISSING` nodes, source coverage, the lines after an error and the
  repair to a valid state are checked. On the single-line mutants of the
  three repository samples, the candidate hides rows that the 0.1.0 parser
  (`47d4047`) keeps about as often as the reverse, and far less often by
  five rows or more (the qualification report has the counts).
- When the parse stack holds more unclosed constructs than the runtime's
  recovery summary reaches (16 entries), recovery cannot return to a
  statement boundary; the following lines are absorbed, as without a scanner.
- `go-treesitter` needs a Go port of the scanner. It carries hand-written Go
  scanners for other grammars (`Scan(payload, lexer, validSymbols)`), and
  `ts2go` converts only `parser.c`. This scanner uses `lookahead`, `advance`,
  `mark_end`, `eof` and `result_symbol` and serializes one byte; input and output golden cases for the port are kept in
  `test/recovery/`. The port and its V9 evidence belong to `go-treesitter`.

## Validation / enforcement

- Attribution runs compare the same generated parser with a no-op and the
  active scanner, and the previous and the new grammar.
- Incremental and fresh parses agree across edits that create or remove a
  recovery run; repaired text parses as the valid tree; a cancelled parse
  resumes and resets correctly; two parsers are independent.
- Scanner unit cases cover `LF`, `CR LF`, a lone `CR`, end of input with and
  without blanks or a final word, a NUL byte, UTF-8 text, string literals
  containing `'` and a `'` comment; with the lines-after-an-error cases they
  are the golden trees of `test/recovery/`, compared by
  `scripts/check_robustness.py`, which also requires every declaration of
  those cases to stay outside every `ERROR` node.
- `scripts/check_generated.py` requires this ADR for `src/scanner.c` and an
  `externals` list in `grammar.js`.

## Revisit conditions

- A stock runtime release bounds recovery paths, releases stack nodes
  iteratively and makes the sibling scan linear.
- A consumer cannot load a grammar with an external scanner.
