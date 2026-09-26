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
   rule, is valid, which happens only in the error state's lex mode, and at
   the line end or the end of input after a long run of the same stack
   version (Decision 3), which exists only after an error. The runtime also
   tries the error state's lex mode when a normal state finds no token (a
   lone `CR`, for example); a token returned there is accepted only where the
   grammar accepts it, so the scanner never returns a line end for a lone
   `CR`.
3. It then returns one of two tokens:
   - a **recovery run**: malformed text of one line, stopping before a line
     break (`LF`, `CR LF` or a lone `CR`), before a `'` comment outside a
     string literal, before a keyword that closes or continues a block
     (`END…`, `NEXT`, `ELSE…`, `CATCH`) or a `:` or `#` before one, or at the
     end of input; never empty. A run of 16 units or more is *long*;
   - a **recovery line end**: the line break (`LF` or `CR LF`) of a line
     whose long run did not stop before a block keyword, or at the end of
     input an empty token, once per stack version (in recovery after a long
     run or not; in a normal state after a long run). The grammar accepts it
     where a line of statements ends and after the header of a loop,
     function, TRY, CATCH or directive, not after an IF header (a single-line
     IF with an error would become a block IF) and not inside brackets.
   At any other line break it returns nothing, so the runtime lexes the
   ordinary line break and recovery may resume after an IF header or inside
   a multi-line bracket literal, as without the scanner; when a long run
   stops before a block keyword, recovery can resume at the keyword on the
   same line, so that line's break is ordinary too. It also returns nothing,
   so that recovery proceeds token by token as without the scanner, for a
   malformed rest of fewer than 16 units that is followed by a line that
   begins like a statement (a cheap run there lets a recovery version skip
   the line break and take the next line into the malformed statement), that
   begins with a closing bracket (recovery can then return into the literal
   it closes) or that ends the input, unless a long run precedes it on its
   line; a rest that stops before a block keyword is a run however short.
   When recovery returns to an earlier state at the line end of a long run,
   the runtime lexes that line end again in a normal state; the scanner
   returns it as a recovery line end there too. A long malformed line then
   becomes one `ERROR` node that keeps the native children of the tokens
   parsed before the error, and parsing resumes at the next line when a
   statement boundary is within reach of recovery.
4. Tokens that can stay unreduced on the parse stack in long runs without a
   named node between them (the openers `(` and `[`, the prefix operators
   `-`, `+` and `not`, and `try`) get named raw forms that appear only inside
   `ERROR` nodes; every valid tree still shows them under their anonymous
   names. A hidden rule that starts with a second never-produced external
   token lists the raw forms, so that the generator keeps their names, and is
   placed so that no public node lists them as children. The raw names are
   public, documented in tree-schema.md as error-only.
5. The scanner keeps one state byte, flags of the last token it returned in
   a stack version: a long run on the current line (kept by the shorter runs
   after it, cleared by the recovery line end of the line); a long run on
   the current line that stopped before a block keyword (it matters only at
   the end of input); and the empty line end at the end of input was
   returned. A valid parse has no scanner token, so the byte is never set in
   one. In runtime 0.27.0 a token that changes the state cannot be skipped
   once recovery to an earlier state has succeeded (`ts_parser__recover`),
   and an empty token is kept during recovery only if it changes the state
   (`ts_parser__lex`). The recovery line end of a long run changes the state,
   where recovery is meant to leave the line; the line break after a short
   run is the ordinary one and leaves the state alone; the empty line end at
   the end of input sets its flag, so that the runtime keeps it and it is
   returned at most once per stack version.
   `create` allocates the byte with `ts_calloc` of `tree_sitter/alloc.h` (the
   C library's `calloc` unless the build defines
   `TREE_SITTER_REUSE_ALLOCATOR`); without it the scanner returns no token.
   `serialize` writes the byte only when set. The scanner does not call
   `get_column` (in runtime 0.27.0 it re-reads the line from its start,
   which made a line with many block keywords after an error quadratic;
   Session 05-7 review B2-01), does not recurse, and each successful scan
   except the empty line end advances at least one character; a scan reads
   at most the rest of its line and, at the end of a line, the blank lines
   and first character after it.
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
- **A recovery line break at every line break during recovery** (`b501847`)
  — rejected after independent review (Session 05-7, A2-04): after an error
  in an IF header or in a bracket, the recovery line break was valid neither
  there nor anywhere within reach of recovery, so the rest of the file became
  one `ERROR` node. Now only the line end of a line with a long run is a
  recovery line end.
- **A recovery line break after every run** (Session 05-7 trial R11) —
  rejected: the line break after a short run then changed the state, so the
  runtime dropped the version that skips it whenever recovery could leave
  the line (see Decision 5), and one stray token in a multi-line array or
  associative-array literal turned the literal's earlier lines into an
  `ERROR` node.
- **The last unit of the input as its line end, a 256-character look-ahead
  to the end of input after a block keyword, and a whole-line run after the
  line break of a long run** (`e093ac8`) — rejected after independent review
  (Session 05-7, A3-01 to A3-04): the flag of a long run stayed set when
  recovery lexed its line break again as an ordinary one, so the A2-04 fix
  failed for every later error in the file; a block keyword more than 256
  characters before the end of input left end-of-input recovery quadratic
  (10.7 s at 1 MiB); the whole-line run hid the rest of the file after a
  long malformed line in a nested literal; and short errors in a deeply open
  construct wrapped the whole file at the end of input.
- **A lone `CR` as a recovery line end** (`e093ac8`, `4ff5633`) — rejected
  after independent review (Session 05-7, A4-01): the runtime tries the
  error state's lex mode when a normal state finds no token, so the lone
  `CR` became a line end in parses without any other error (BS-LEX-007
  leaves a lone `CR` unresolved; the 0.1.0 parser reports an error).
- **Keeping the long-run flag after a run that stops before a block
  keyword** (`4ff5633`) — rejected (A4-02): when recovery resumed at `ELSE`
  on the same line, the line break after the ELSE header never reached the
  scanner, and a later error recovered as after a long run. Clearing the
  flag entirely there (trial R14b) made end-of-input recovery after
  `… NEXT` quadratic again, so the end of input keeps its own flag.
- **Recovering a short rest before a block keyword token by token** (trial
  R14b) — rejected: the block-keyword recovery guard grew by more than
  8 MiB.
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
  (`47d4047`) keeps in fewer mutants than the reverse, by one, five and
  twenty rows or more (the qualification report has the counts). A long run
  also covers the places inside its line where recovery without the scanner
  could have resumed, such as the statement after `THEN`.
- The empty line end at the end of input lets recovery leave constructs
  that the input leaves open. On 2,816 generated inputs that end inside open
  constructs (Session 05-7 review A4), the candidate keeps declarations that
  `e093ac8` loses in 200 and loses declarations that `e093ac8` keeps in 19;
  it loses none that `47d4047` keeps.
- A short malformed rest that begins with a closing bracket is recovered
  token by token, so an extra closer can end a literal early and its real
  closing lines become errors (1 to 5 more rows in 24 of 360 generated
  cases, as with `47d4047`). A short rest that stops before a block keyword
  is one run, so the next line can join the malformed statement
  (`x = ) + 1 : else` followed by `x = 1`).
- When the parse stack holds more unclosed constructs than the runtime's
  recovery summary reaches (16 entries), recovery cannot return to a
  statement boundary at the line end of a long run; it continues on the next
  lines token by token or at a closing bracket and can absorb lines that the
  parser without the scanner keeps.
- `go-treesitter` needs a Go port of the scanner. It carries hand-written Go
  scanners for other grammars (`Scan(payload, lexer, validSymbols)`), and
  `ts2go` converts only `parser.c`. This scanner uses `lookahead`, `advance`,
  `mark_end`, `eof` and `result_symbol`, serializes one byte and returns an
  empty token at the end of input, which the port's runtime must keep as the
  stock runtime does (the state changes); input and output golden cases for
  the port are kept in `test/recovery/`. The port and its V9 evidence belong to `go-treesitter`.

## Validation / enforcement

- Attribution runs compare the same generated parser with a no-op and the
  active scanner, and the previous and the new grammar.
- Incremental and fresh parses agree across edits that create or remove a
  recovery run; repaired text parses as the valid tree; a cancelled parse
  resumes and resets correctly; two parsers are independent.
- Scanner unit cases cover `LF`, `CR LF`, a lone `CR` in a run, between
  lines and between valid statements, end of input with and without blanks, a final word, a final block
  keyword, a final comment or a block keyword far from the end, a NUL byte,
  UTF-8 text, string literals
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
