# Grammar design

The implementation structure of `grammar.js`: tokens, rule families,
precedence, statement boundaries, the conditional-compilation spike and the
implementation order. Designed in Session 02 and implemented as designed in
Session 03 (grammar version 0.1.0); §3, §4 and §11 record what the
implementation established. Requirements and
their statuses are in [language-conformance.md](language-conformance.md);
acceptance policy in [grammar-contract.md](grammar-contract.md); node and field
names in [tree-schema.md](tree-schema.md) (planned public schema). Where this
document and the registry disagree, the registry wins and this document is
corrected.

Rule names written `_name` are hidden; other names are planned public nodes.
Token spellings are described, not written as grammar code.

## 1. Fixed constraints

| Constraint | Rule | Source |
|---|---|---|
| External scanner | Forbidden. No `externals`, no `src/scanner.c`. | [ADR-0005](../design/decisions/ADR-0005-external-scanner-policy.md) |
| Generator | Exact stable release, `--abi 15`, selected by the adoption procedure. | [ADR-0002](../design/decisions/ADR-0002-generator-pin-and-generated-artifacts.md) |
| DSL features | Only features present in every eligible stable release (0.26.0 or later, ADR-0002 adoption procedure): `word`, `supertypes`, `extras`, `inline`, `prec*`, `alias`, `field`, `token`, `token.immediate`. `eof()` (0.27 only) and `reserved` word sets are not used by the primary design. | Tree-sitter docs @ `v0.26.13`, `v0.27.0` (Level 3) |
| Conflicts | `conflicts` starts empty. An entry is added only under §14. | this document |
| Superset | One grammar, no version modes; `since` is metadata. | [ADR-0003](../design/decisions/ADR-0003-current-language-superset-grammar.md) |
| Conditions | Never evaluated. | [ADR-0004](../design/decisions/ADR-0004-conditional-compilation-representation.md) |

No requirement in the registry depends on lexer state carried between tokens.
Every construct below is expressible with context-aware lexing, keyword
extraction and LR(1) grammar rules; the only uncertain case (literal-`false`
bodies) is gated by the §11 spike, whose failure path adds no scanner.

## 2. Line model

Newlines are **tokens**, never extras. Tree-sitter reduces the regex class
`\s` to `[ \t\n\r]` (Level 3, "Using Extras"), so the whitespace extra is the
explicit class `[ \t]`.

| Form | Planned behaviour | Requirement | Fixture |
|---|---|---|---|
| LF | `_newline` token | BS-LEX-005, 006 | every multi-line fixture |
| CRLF | `_newline` token `\r?\n`; identical trees | BS-LEX-006 | `BS-LEX-006: CRLF line endings` (bytes) |
| Bare CR | not whitespace, not a terminator: yields `ERROR` | BS-LEX-007 (unresolved) | V10 seed only |
| EOF without final newline | last item needs no terminator (`source_file` below) | BS-LEX-008 | every corpus fixture (the runner strips one final newline) |
| EOF with final newline | same tree | BS-LEX-008 | `BS-LEX-008: final line with a line terminator` (blank line before the divider) |
| `:` | `_terminator` = `_newline` or `:` in file and block lists | BS-LEX-010, 011 | `BS-LEX-010: …` |
| Newline in `(`…`)` of calls | no rule | BS-EXP-024 (unresolved) | — |
| Newline in parameter lists | allowed after a `,` only; after `(` or before `)` no rule | BS-FUNC-006; BS-FUNC-007 (unresolved) | `BS-FUNC-006: parameter list continued after a comma` |
| Newline in grouping `(`…`)` or index `[`…`]` | no rule | BS-EXP-023 (unresolved) | — |
| Newline in array literals | after `[`, as element separator (with or without comma), before `]`; trailing comma tolerated | BS-ARRAY-002, 003 | `BS-ARRAY-002: …`, `BS-ARRAY-003: …` |
| Newline in AA literals | after `{`, as entry separator (with or without comma), before `}`; trailing comma tolerated | BS-AA-003, 004 | `BS-AA-003: …`, `BS-AA-004: …` |
| Newline after a binary operator | no rule | BS-EXP-023 (unresolved) | — |
| Comment termination | `comment` stops before `\r` or `\n`; the newline is a separate `_newline` | BS-LEX-012 | `BS-LEX-012: comment after code on the same line` |
| REM termination | same as `'` | BS-LEX-013, 014 | `BS-LEX-014: bare REM line` |
| Label and colon | `label_statement` = identifier `:`; the next token must be a terminator | BS-LEX-027, 028 | `BS-LEX-027: label line` |
| Directive lines | a directive is a statement; `#error` text runs to the line end; a directive sharing its line with a statement (before or after `:`) is not contractual | BS-COND-008 | `BS-COND-008: indented directives with comments` |

Statement lists:

```text
source_file := (statement _terminator | _terminator)* statement?
block       := _terminator (statement _terminator | _terminator)*
_terminator := _newline | ':'
```

`block` always begins with the terminator that ends its header, so a block
exists even when the body is empty, its range starts at that terminator, and a
header may end with `:` (BS-STMT-035). Exception: a single-line IF branch is
`_inline_block` aliased to `block`; it has no terminator and spans its first to
its last statement. The TRY body uses `_try_body`, a hidden rule with the shape
of `block` and its own line rule, aliased to `block` (§4, §10). The final optional `statement` in
`source_file` gives EOF termination without `eof()`.

Byte-sensitive fixtures — inputs containing a CR byte or a byte-order mark —
live under `test/corpus/bytes/`; the commit that adds the first of them also
adds `test/corpus/bytes/** -text` to `.gitattributes`. Final-newline variants
need no byte fixture: an LF corpus file expresses them with a blank line
before the divider. The Tree-sitter test runner keeps interior line endings
byte for byte and strips one final `\n` and a preceding `\r` from each input
(Level 3, `crates/cli/src/test.rs` @ `v0.27.0` and `v0.26.13`); at `v0.26.0`
the `\r` is stripped only on Windows. So that every eligible release sees the
same input, the line just before the divider of a byte fixture always ends
with LF alone.

## 3. Token model

| Token | Planned shape | Named? | Owner rule | Requirements |
|---|---|---|---|---|
| whitespace (extra) | `[ \t]` | — | `extras` | BS-LEX-002, 003 |
| `_newline` | `\r?\n` | hidden | `_terminator`, literal and list rules | BS-LEX-005, 006 |
| `comment` (extra) | `'` then `[^\r\n]*`; or `rem` in any case, then either nothing or one space/tab and `[^\r\n]*` | public | `extras` | BS-LEX-012–014 |
| `identifier` (`word`) | `[A-Za-z_][A-Za-z0-9_]*` then one optional `[$%!#&]` | public | everywhere a name is expected | BS-LEX-015–020 |
| keywords | `kw(w)`: a character-class regex matching `w` in any letter case (`/[eE][nN][dD]/`), aliased to the lower-case anonymous name `w` | anonymous | per rule | BS-LEX-001, 021, 025 |
| `number` | decimal: (`\d+(\.\d+)?` or `\.\d+`), optional exponent `[eEdD][+-]?\d+`, optional suffix `[%!#&]`; hex: `&[hH][0-9A-Fa-f]+` with optional `&` | public | `expression` | BS-LIT-003–014 |
| `string` | `"` then any run of (`[^"\r\n]` or `""`) then `"` | public | `expression`, AA keys, `library_statement` | BS-LIT-015–018 |
| `source_literal` | a pattern matching `line_num` in any letter case | public | `expression` | BS-LIT-019 |
| punctuation | `( ) [ ] { } , ; : . @ ? =` | anonymous | per rule | — |
| optional chaining | `?.` `?@` `?[` `?(` as single tokens | anonymous | postfix rules | BS-LEX-029, 030 |
| operators | `^ * / \ + - <> < > <= >= << >>`; words `kw('mod') kw('and') kw('or') kw('not')` | anonymous | `binary_expression`, `unary_expression` | BS-EXP-011–019 |
| assignment operators | `= += -= *= /= \= <<= >>=` | anonymous | `assignment_statement` | BS-STMT-001, 002 |
| update operators | `++ --` | anonymous | `update_statement` | BS-STMT-003, 004 |
| block terminators | `end`, a run of `[ \t]`, then `if`, `for`, `while`, `sub`, `function` or `try`, in any case, each **one token**, aliased to the anonymous names `end if`, `end for`, `end while`, `end sub`, `end function`, `end try` | anonymous | block rules | BS-STMT-010, 012, 015, 016, 022, 036, BS-FUNC-001, 002, BS-ERR-001 |
| directive words | `#` immediately followed by `const`, `if`, `else`, `end` or `error` in any case, one token each, aliased to `#const`, `#if`, `#else`, `#end`, `#error`; no word boundary (§11) | anonymous | directive rules | BS-COND-001–005, 008 |
| `error_message` | `[^ \t\r\n][^\r\n]*` with lexical precedence 1 (wins over `comment` for the same text); valid only after `#error` | public | `error_directive` | BS-COND-004 |

Details:

- Keyword boundaries. Every `kw()` token matches only strings that
  `identifier` also matches. An equal-length match goes to the token with the
  higher lexical precedence, then to a string over a pattern, then to the
  earlier token (Level 3, `prefer_token` in
  `crates/generate/src/build_tables/token_conflicts.rs` @ `v0.27.0`). `kw()`
  tokens are patterns, so `identifier` is the last rule in `grammar.js` and
  every keyword wins its tie; a longer identifier still wins by length
  (`iffy`, `endpoint`). The generator moves a keyword into its keyword table
  (keyword extraction: the lexer matches the `word` token first and then looks
  the word up) only when substituting the word token would not change the
  keyword's conflicts with other tokens (`identify_keywords` in
  `crates/generate/src/build_tables.rs` @ `v0.27.0`). `comment` overlaps
  `identifier` on `rem`, so keywords that are valid in a state where
  `identifier` is not (for example `then`, `else`, `to`, `in`, `as`, `mod`,
  `and`, `or`, `catch` and the type names) are not extracted and are
  recognised by context-aware lexing in the main lexer. Valid input gets the
  same tree either way. Invalid input can differ: where such a keyword is valid
  and `identifier` is not, a word that merely begins with it is split, without
  `ERROR` (`x = a modx` lexes as `a mod x`, `x = a android` as `a and roid`,
  `for i = 1 tox` as `to x`, `if a then b() elsex = 1` as `else x = 1`, and in
  a block IF `else iffy = 1` as `else if fy = 1`). By the same rule a
  single-line `elseif` lexes as `else` `if`, giving the tree of `else if`
  (single-line ELSE IF has no requirement row). No requirement depends on such
  input (grammar-contract non-goals: not every invalid program is rejected).
- The two-word block terminators are single tokens. After a line terminator
  inside a block, both an END statement (`end`) and the block's own terminator
  are valid; with `end` and `if` as two tokens one token of lookahead could not
  choose between them. As one token (`end if`) the lookahead decides, and the
  longest match prefers `end if` over `end`. The token contains whitespace, so
  it is not a keyword-extraction candidate. The other multi-word keywords
  (`else if`, `for each`, `exit for`, `exit while`, `continue for`,
  `continue while`, `#else if`, `#end if`) stay separate tokens: one token of
  lookahead after their first word decides (`else`, `#else` and `#end` never
  start a statement, and after `exit`, `for` or `continue` the next word
  selects the form). In both cases any run of spaces or tabs may separate the
  words and a newline may not (BS-STMT-022).
- A digit run followed by `.` and a letter is `number` then `.`: the fraction
  requires a digit after the point, so `5.tostr()` is member access
  (BS-LIT-014), and `5.` is not a number (BS-LIT-013, unresolved).
- The designator is part of `identifier`, not a separate node. `&` never
  starts an identifier, so `&hFF` is always a `number`.
- `?` alone is the PRINT alias. After an operand, `?.`, `?@`, `?[`, `?(` are
  preferred by longest match (`IF x?("Hello")` is an optional call,
  BS-LEX-032). At the start of a statement the optional-chaining tokens are not
  valid, so context-aware lexing yields `?`: `?.1` and `?("x")` print
  (BS-LEX-031), and `?[1]` prints an array (BS-LEX-035).
- `REM` versus `identifier`: for `remark`, `rem1`, `rem_x` the identifier is
  longer and wins. For `rem x` the comment is longer and wins. For exactly `rem`
  followed by a line end or EOF both match three characters: the comment must
  win (fixtures `BS-LEX-014: bare REM line` and the other BS-LEX-014 fixtures). The comment token
  must **not** carry lexical precedence: a higher-precedence completed token
  stops the lexer from continuing into lower-precedence tokens
  (`prefer_transition`, `token_conflicts.rs` @ `v0.27.0`), which would turn
  `remark` into a comment. Mechanism, applied in order until both fixtures
  pass:
  1. Rely on the equal-length tie rule: equal precedence, both patterns, the
     earlier token wins. Declare `comment` (and list it in `extras`) before
     `identifier` in `grammar.js`.
  2. Make the comment a non-terminal extra: `'` form as one token, REM form as
     `kw('rem')` followed by an optional `token.immediate` rest-of-line; keyword
     extraction then returns `rem` wherever the extra is valid.
  3. Exclude exactly `rem` (any case) from the identifier pattern by
     construction (an alternation that matches every identifier except that
     word).

  Adopted: mechanism 1. Every BS-LEX-013 and BS-LEX-014 fixture passes with it
  from WP7 on; mechanisms 2 and 3 were not needed.
- `#error` text: `error_message` consumes the rest of the line, including
  apostrophes (BS-COND-004).

## 4. Reserved words

Strategy: `word: $ => $.identifier`, every keyword through `kw()`, and **no
`reserved` word sets**. The runtime returns an extracted keyword only where it
has a parse action in the current state (or is a reserved word there);
otherwise the word stays an `identifier` (Level 3, `lib/src/parser.c` @
`v0.27.0`, `ts_parser__lex`). A keyword the generator does not extract (§3)
is lexed only in states where it is valid (context-aware lexing). Either way
every keyword is contextual.

| Category | Words | Treatment | Requirements |
|---|---|---|---|
| A. Reserved grammar keywords | And Dim Each Else ElseIf End EndFunction EndIf EndSub EndWhile Exit ExitWhile False For Function Goto If Invalid LINE_NUM Next Not Or Print Return Step Stop Sub Then To True While (31) + Rem | `kw()` tokens, except the literals `True`, `False`, `Invalid` and `LINE_NUM`, which are named nodes matched by case-insensitive patterns (§3); `Rem` is recognised by the `comment` token | BS-LEX-021, 013 |
| B. Reserved callable names | Box CreateObject Eval GetGlobalAA GetLastRunCompileError GetLastRunRunTimeError ObjFun Pos Run Tab Type (11) | ordinary `identifier`; calls are `call_expression` | BS-LEX-022, 023 |
| C. Reserved, no documented form | Let (1) | ordinary `identifier`; no LET rule | BS-STMT-034 |
| D. Syntax words not on the list | As Catch Continue EndTry In Library Mod Throw Try; type names Integer Float Double Boolean String Object Dynamic Void | `kw()` tokens, contextual | BS-LEX-025, BS-ERR-005, BS-TYPE-001 |

Categories A–C cover all 44 official reserved words.

Where only a name is valid (the CATCH variable, a `#const` name, a FOR
counter, a parameter), the literal words `true`, `false`, `invalid` and
`LINE_NUM` are not valid tokens, so context-aware lexing yields an
`identifier` (`catch true`); where a name or a boolean is valid (a `#const`
value, a directive condition), `invalid` and `LINE_NUM` do (`#const x =
invalid`, `#if invalid`). Using a reserved word as a name is a compile-time
rule (BS-LEX-023), not grammar.

Where a keyword and an identifier are both valid, the keyword wins. The
positions that matter are statement starts (`if for while try throw return
exit continue print dim goto end stop function sub library`, `catch` inside a
TRY body, `next` inside a FOR body, `else`/`elseif` inside IF bodies) and
operator positions after an operand (`and or mod`). Member names after
`.`/`?.`, AA keys, parameter names, loop variables and the operand of GOTO are
positions where no keyword is valid, so keyword words are identifiers there
(BS-LEX-024).

State merging. The generator merges parse states that share an item-set core
and ignores keyword/word-token conflicts when it does
(`crates/generate/src/build_tables/minimize_parse_table.rs` @ `v0.27.0`,
`merge_compatible_states`). A keyword that ends one kind of block can
therefore become valid at the statement starts of other blocks built from the
same rule. That is harmless for reserved words (`else`, `elseif`, `next`).
`catch` must stay an identifier outside TRY bodies (BS-ERR-005). The TRY body
is therefore a separate hidden rule, `_try_body := _terminator _try_line*`
with `_try_line := statement _terminator | _terminator`, aliased to `block`.
Because its repetition is over its own line rule, the generator does not share
a repeat helper between it and `block` (identical repeats are shared,
`crates/generate/src/prepare_grammar/expand_repeats.rs` @ `v0.27.0`), so the
states that can end a TRY body are not the states of other bodies. Where a
keyword still reaches a state with no action for it, the runtime retries the
word token (`lib/src/parser.c` @ `v0.27.0` and `v0.26.0`). The fixture
`BS-ERR-005: try and catch as identifiers` checks `catch` both as the first
statement of a body and after another statement. The block terminators are
single tokens (§3), so `end` is unaffected.

Required checks that keywords do not consume identifiers: the fixtures of
BS-LEX-001, 021, 024, 025, 026, BS-ERR-005 and BS-LIT-014.

Fallback, used only when one of those fixtures fails and its actual tree has
a keyword token where the fixture expects an `identifier` (or the reverse),
after confirming the fixture matches this document:

- add `reserved: { global: [...], property: [] }`, where `global` lists the 31
  `kw()` tokens of category A (not `Rem`);
- wrap the identifier in member-name and AA-key positions with
  `reserved('property', …)`;
- keep category D contextual.

The fallback rejects more invalid programs (`step = 1`) and changes no tree of
a documented or provisional form. Record its adoption in this section.

Not adopted: every fixture listed above passes with the primary strategy
(Session 03).

## 5. Expression precedence

Official order, highest first (EVT §Operators, cross-checked against prose,
examples and CA §Use of wrapper functions on intrinsic types). The numeric
constants are an internal mapping only.

| Level | Constant | Operators | Kind | Assoc. | Requirements |
|---|---|---|---|---|---|
| 1 | `POSTFIX` = 10 | call `(…)` `?(…)`; member `.` `?.`; index `[…]` `?[…]`; attribute `@` `?@` | postfix | left (chain) | BS-EXP-003–007, 021 |
| 2 | `EXPONENT` = 9 | `^` | binary | right | BS-EXP-011 |
| 3 | `UNARY` = 8 | `-` `+` | prefix | — | BS-EXP-012 |
| 4 | `MULTIPLICATIVE` = 7 | `*` `/` `MOD` `\` | binary | left | BS-EXP-013, 014 |
| 5 | `ADDITIVE` = 6 | `+` `-` | binary | left | BS-EXP-015 |
| 6 | `SHIFT` = 5 | `<<` `>>` | binary | left | BS-EXP-016 |
| 7 | `COMPARE` = 4 | `=` `<>` `<` `>` `<=` `>=` | binary | left | BS-EXP-017, 020 |
| 8 | `NOT` = 3 | `NOT` | prefix | — | BS-EXP-018 |
| 9 | `AND` = 2 | `AND` | binary | left | BS-EXP-019 |
| 10 | `OR` = 1 | `OR` | binary | left | BS-EXP-019 |
| — | `LIST` = -1 | PRINT item list, single-line IF | (list) | right | BS-STMT-009, 026 |

The table lists `()`, `.`, `[]` and optional chaining on separate rows; they
are all postfix operators that apply left to right, so one level is used
(BS-EXP-021, provisional). `@` is absent from the table and gets the postfix
level. A prefix operator binds its operand at its own level: `-2^2` is
`-(2^2)`; as the right operand of a tighter operator, `2^-2` is `2^(-2)` and
`a < not b` is `a < (not b)` (BS-EXP-027, provisional).

Postfix operand kinds. `_postfix_operand` is `identifier`,
`parenthesized_expression`, `call_expression`, `member_expression`,
`index_expression` or `attribute_expression` (including their optional
variants). It is a hidden rule that is not inlined and carries `POSTFIX`
precedence. When it was inlined, error recovery on a run of unclosed calls or
indexes opened with a token that cannot start their content (`x = f(*f(*…`)
left a deep stack whose end-of-input acceptance took quadratic time and memory
(1.27 GiB at 6 KB; Session 05-1 re-audit finding R-A-01); not inlined, the same
input is linear. The precedence settles the reduce/reduce conflict between an
operand of a postfix form and a PRINT item (`print a [1]`, §14) the way the
inlined rule did; `src/node-types.json` and every valid tree are unchanged.

| Postfix form | Accepted left operand |
|---|---|
| call, index, attribute | `_postfix_operand` |
| member | `_postfix_operand`, `number`, `string` (BS-LIT-014) |

Other operand kinds (calls or indexes on literals, access on array and AA
literals) have no rule (BS-EXP-025, unresolved).

Precedence cases (each is a fixture expectation, see the workload matrix):

| Input | Grouping |
|---|---|
| `-5.tostr()` | `-(5.tostr())` |
| `a.b ^ 2` | `(a.b) ^ 2` |
| `2^3^2` | `2^(3^2)` |
| `-2^2`, `2^-2` | `-(2^2)`, `2^(-2)` |
| `-a * b`, `a * -b` | `(-a) * b`, `a * (-b)` |
| `a / b mod c \ d * e` | `(((a / b) mod c) \ d) * e` |
| `a + b * c`, `a - b - c` | `a + (b * c)`, `(a - b) - c` |
| `a << b + c` | `a << (b + c)` |
| `a < b << c` | `a < (b << c)` |
| `a < b < c`, `a = b <> c` | `(a < b) < c`, `(a = b) <> c` |
| `not a = b` | `not (a = b)` |
| `not a and b` | `(not a) and b` |
| `a or b and c`, `a or b or c` | `a or (b and c)`, `(a or b) or c` |
| `not not a` | `not (not a)` |
| `a = c and not (b > 40)` | `(a = c) and (not (b > 40))` |
| `not a <> b and c or d` | `((not (a <> b)) and c) or d` |
| statement `x = a = b` | assignment of `(a = b)` |
| `a?.b.c?[0]?(1)` | `(((a?.b).c)?[0])?(1)` |
| `x@y.z`, `a.b@c` | `(x@y).z`, `(a.b)@c` |
| `"a" + b + "c"` | `("a" + b) + "c"` |

## 6. Statement structure and boundaries

`statement` (supertype) = `assignment_statement`, `update_statement`,
`call_expression` (statement form), `if_statement`, `for_statement`,
`for_each_statement`, `while_statement`, `exit_statement`,
`continue_statement`, `return_statement`, `print_statement`, `dim_statement`,
`goto_statement`, `label_statement`, `end_statement`, `stop_statement`,
`library_statement`, `throw_statement`, `try_statement`,
`function_declaration`, `const_directive`, `if_directive`, `error_directive`.

One statement set serves the file and every block (BS-STMT-033); nested named
declarations and LIBRARY inside bodies are therefore accepted without being
contractual (BS-FUNC-012, BS-STMT-032).

Statement-level chains. Call statements, assignment targets and update targets
use hidden chain rules whose head is an `identifier` and that contain no
optional-chaining operator and no attribute access:

```text
_stmt_chain  := identifier | _stmt_member | _stmt_index | _stmt_call
_stmt_member := object:_stmt_chain '.' property:identifier                  alias member_expression
_stmt_index  := object:_stmt_chain '[' index:expression (',' index:expression)* ']'   alias index_expression
_stmt_call   := function:_stmt_chain arguments:argument_list                alias call_expression ('(' only)
call statement      := _stmt_call
_assignment_target  := identifier | _stmt_member | _stmt_index
```

The field names are those of the expression forms, so the aliased nodes carry
exactly the planned fields. Likewise `_inline_block` (single-line branches) and
`_try_body` are aliased to `block`.

Arguments and indexes inside the chain are full expressions, so
`f(foo?.bar).member = 5` is accepted (BS-EXP-010) while `array?[12] = x`,
`a?.b = 1` and `f?()` are not (BS-EXP-008, 009). Because no statement starts
with `(`, a literal, `?` + operand, `-` or `[`, a statement start never
overlaps with a token that could continue an expression.

Boundary rules:

| Situation | Rule | Requirement |
|---|---|---|
| Newline- and colon-delimited statements | `source_file` and `block` lists (§2) | BS-LEX-005, 010, 011 |
| Single-line vs block IF | after `IF condition [THEN]`: `_terminator` or comment → block form (the block begins with that terminator); a statement start → single-line form | BS-STMT-007, 008 |
| Single-line branch extent | `_inline_block` = `_inline_statement ( ':'+ _inline_statement )*`, right-precedence so `:` and `ELSE` continue the innermost single-line IF; ends at the enclosing `_terminator` that is a newline, or at EOF; a trailing `:` has no rule | BS-STMT-007, 009 |
| `_inline_statement` | assignment, call, PRINT, RETURN, EXIT, CONTINUE, STOP (documented); update, GOTO, END, THROW, DIM, and a nested single-line IF only — the single-line alternative as a hidden rule aliased to `if_statement` (provisional) | BS-STMT-007, 009 |
| ELSE association | single-line: nearest unmatched single-line IF; block: `ELSE` after a block body belongs to the open block IF | BS-STMT-009, 010 |
| Block IF clauses | `ELSE IF`/`ELSEIF` + condition + optional THEN + `block`; `ELSE` + `block` | BS-STMT-010, 011 |
| Labels | `label_statement` only in `source_file`/`block` lists, never in single-line branches | BS-LEX-027, 028 |
| Comments | extras; they never end a statement, the following `_newline` does; placement in the tree follows the tree-schema comment rule | BS-LEX-012 |
| PRINT items | `print_statement` = (`print` or `?`) then any sequence of `expression`, `,`, `;`; the list has `LIST` precedence so every operator or postfix continuation extends the current item | BS-STMT-024–026, 040 |
| Directive lines | directives are statements, placed wherever statements are; their bodies are `block`s | BS-COND-002–008, 012 |
| END vs END X | the two-word terminators are single tokens (§3); `end` alone is `end_statement` | BS-STMT-029, 036 |
| NEXT | a terminator only of the innermost open FOR/FOR EACH; inside a WHILE body it closes nothing, so the WHILE is an error whether `next` lexes there as a keyword or an identifier | BS-STMT-013, 017 |

## 7. Top level

`source_file` accepts any statement list (§2): function and sub declarations,
LIBRARY, directives, ordinary statements, labels and comments, in any order,
including an empty file (BS-STMT-033, BS-LEX-008). Whether the Roku compiler
accepts statements outside functions is unresolved at Level 2; the grammar
accepts them (fragment tolerance) and makes no claim either way.

## 8. Functions and subs

```text
function_declaration := kw(function) name:identifier parameters:parameter_list
                        [kw(as) return_type:type] body:block ('end function' | endfunction)
                      | kw(sub) name:identifier parameters:parameter_list
                        body:block ('end sub' | endsub)
anonymous_function   := the same two forms without the name (the SUB form is tolerated, BS-FUNC-011)
parameter_list       := '(' [parameter (',' _newline* parameter)*] ')'
parameter            := name:identifier ['=' default:expression] [kw(as) type:type]
type                 := one of kw(integer float double boolean string object dynamic function void)
```

- FUNCTION and SUB share `function_declaration` and `anonymous_function`; the
  keyword is an anonymous child (tree-schema spelling table).
- A terminator matches its opener (BS-STMT-036): `function … end sub` is an
  error.
- SUB takes no `AS` clause (BS-FUNC-004, unresolved).
- Calls: `call_expression` = `_postfix_operand` + `argument_list`;
  `argument_list` = (`(` or `?(`) [expression (`,` expression)*] `)`, with no
  line break inside (BS-EXP-024, unresolved). Statement-level calls use `(`
  only (§6). Calls without parentheses have no rule.
- Semantic restrictions stay out of the grammar: default-parameter order
  (BS-FUNC-008), function-name designators (BS-LEX-019), `m` binding
  (BS-FUNC-013/014).

## 9. Arrays, DIM and associative arrays

```text
array_literal             := '[' _newline* [expression (_sep expression)* _sep?] ']'
associative_array_literal := '{' _newline* [entry (_sep entry)* _sep?] '}'
_sep                      := ',' _newline* | _newline+
associative_array_entry   := key:(identifier | string) ':' value:expression
dim_statement             := kw(dim) name:identifier
                             ('[' dimension:expression (',' dimension:expression)* ']'
                             | '(' dimension:expression (',' dimension:expression)* ')')
index_expression          := object ('[' | '?[') index:expression (',' index:expression)* ']'
```

- `_sep` covers comma-separated, newline-separated and mixed forms; a trailing
  `_sep` gives the tolerated trailing comma (BS-ARRAY-003, BS-AA-004); two
  commas in a row have no rule, and neither have a comma that starts a line
  (comma-first) or a line break between an entry's `:` and its value
  (BS-ARRAY-009, BS-AA-006, unresolved).
- `a[1,2,3]` is one `index_expression` with three `index` fields; `a[1][2][3]`
  is three nested ones (BS-ARRAY-007). No normalisation.
- AA keys that are keyword words are identifiers by contextual lexing
  (BS-LEX-024). Duplicate keys and key case are semantic (BS-AA-005).
- Newlines inside index brackets and DIM brackets have no rule.

## 10. TRY, CATCH, THROW

```text
try_statement   := kw(try) body:_try_body handler:catch_clause ('end try' | endtry)
_try_body       := _terminator _try_line*          (aliased to block, §4)
_try_line       := statement _terminator | _terminator
catch_clause    := kw(catch) variable:identifier body:block
throw_statement := kw(throw) value:expression
```

- Since 9.4 (BS-ERR-001–005). CATCH is required; a TRY without CATCH is an
  error (BS-ERR-006 has no rule). The variable is a single `identifier`, so the
  five illegal forms of BS-ERR-003 fail at the token after `catch`.
- `catch` ends the TRY body only as a statement-initial keyword directly
  inside that body; elsewhere, including nested bodies, it is an identifier
  (BS-ERR-005). `throw` is a keyword at statement start; elsewhere it is not
  contractual.
- A label between TRY and CATCH is a compile-time rule, not grammar
  (BS-ERR-007, guard fixture).

## 11. Conditional compilation

### Baseline (always implemented first)

```text
const_directive   := '#const' name:identifier '=' value:(identifier | true | false)
if_directive      := '#if' condition:_cc_condition consequence:block
                     alternative:else_if_directive* alternative:else_directive? '#end' kw(if)
else_if_directive := '#else' kw(if) condition:_cc_condition consequence:block
else_directive    := '#else' body:block
error_directive   := '#error' message:error_message?      (no message: BS-COND-015)
_cc_condition     := identifier | true | false
```

Every branch body is an ordinary `block` of statements, so directives may wrap
statements or declarations (BS-COND-002–006) and, being statements
themselves, may appear inside bodies and nest (BS-COND-012). Conditions are
never evaluated. Because `#end` and `#else` are one-token directive words
followed by keyword tokens, `#endif`/`#elseif` happen to lex as `#end if` and
`#else if`; that acceptance is non-contractual (BS-COND-009). Directive words
have no word boundary outside a literal-false region: a longer word that
begins with one is split, without `ERROR` (`#iffy` lexes as `#if fy`,
`#constant = true` as `#const ant = true`, `#errors here` as `#error` with the
message `s here`), like the keyword boundaries of §3; no requirement depends
on such input.

### Literal-false spike (ADR-0004)

Run in WP15 (§15), after the baseline passes its fixtures. Scope: the body of
an `#if false` or `#else if false` branch. The `#else` branch of a literal
`true` condition is not attempted (the ADR permits it; no documented form
needs it).

Design V1, tried first:

```text
if_directive      += '#if' condition:false consequence:inactive_text …
else_if_directive += '#else' kw(if) condition:false consequence:inactive_text
_cc_condition     := identifier | true            (literal false moves to the forms above)
inactive_text     := _newline (_inactive_line | _newline | _inactive_if)*
_inactive_line    := token(prec(0, [^ \t\r\n#][^\r\n]* | '#'[^\r\n]*)), declared after comment
_inactive_if      := '#if' _inactive_line? _newline (_inactive_line | _newline | _inactive_if)*
                     ('#else' _inactive_line? _newline (_inactive_line | _newline | _inactive_if)*)*
                     '#end' kw(if)
'#if', '#else', '#end': lexical precedence 1
```

Under V1 a region line that starts with `'`, or with `REM` followed by a
space, tab or line end, matches `comment` and `_inactive_line` with equal
length and precedence; `comment` is declared first and wins, so the line is a
`comment` node. Every other line — including prose that merely begins with
`rem` (`Remember …`, `REMARK: …`) — is longer as `_inactive_line` and stays
hidden text. A lower precedence for `_inactive_line` is not used: the lexer
would stop at a completed higher-precedence `comment` (`prefer_transition`)
and split `Remember` after `Rem`.

Directive-like lines (adopted after the Session 03 review, which found that
`#ifdef FOO` inside a region lexed as `#if` and opened a nested block, so the
region swallowed the rest of the file). The `#` alternative of
`_inactive_line` is split in two:

```text
_inactive_line := token(choice(
    prec(0, [^ \t\r\n#][^\r\n]*),
    prec(0, '#' then a rest that does not begin with if, else or end, in any case),
    prec(2, '#' then if, else or end run on into a longer word, except the words
            elseif and endif, then [^\r\n]*)))
```

A region line that starts with the whole word `#if`, `#else` or `#end`
(`#elseif`, `#endif` included) is a directive exactly as before: no
`_inactive_line` alternative matches those words as a prefix, so the lexer
cannot continue past a completed directive word into the lower-precedence
text alternative. A longer word (`#ifdef`, `#iffy`, `#elsewhere`,
`#endregion`, `#endnote:`) matches the precedence-2 alternative, which beats
the completed directive word, and the line is hidden text. Without lookahead
the exclusion of `elseif`/`endif` cannot tell a word that ends early at the
line end, so a line consisting of exactly `#endi` or `#elsei` still lexes as
the directive word. Fixture:
`BS-COND-007: directive-like words inside a false region`.

The word boundary is `[A-Za-z0-9_]`: a region line whose first word is exactly
`#if`, `#else` or `#end`, followed by any other character or by the line end,
is a directive, as the design requires (S6–S9), with these consequences for
text that is not a directive (the review's probes; no requirement states
otherwise):

- `#if` alone, or followed by a character such as `-`, `.`, `(`, `:`, `'`,
  `$` or a non-ASCII letter (`#if-then-else notes`), opens a nested block that
  needs its own `#end if`; without one the region runs to the end of the file.
- `#else` in the same position (`#else:`, `#else what`, `#elsei`) closes the
  region and the following lines are parsed as code, with or without `ERROR`.
- `#end` in the same position (`#end.`, `#end region`, `#endi`) yields an
  `ERROR` that can also cover neighbouring region text before or after it
  (and the `#end` of the closing line); the block still ends at the next
  `#end if`, and nothing after it is affected.

These inputs are W13 seeds (robustness only).

Design V2, tried only if V1 fails a criterion: as V1, but `_inactive_line` has
lexical precedence 1 and `#if`, `#else`, `#end` precedence 2, so every region
line, including `'` and REM lines, is hidden text and `inactive_text` has no
`comment` children.

No other design is tried. A design is adopted when it meets C1–C5 and the
PASS expectation, for that design, of the fifteen spike fixtures in the
literal-false table of the workload-matrix catalogue (the two registry
fixtures and S3–S12, R1–R3; the table's later rows postdate the spike). Each design first gets the §15 allowance of three
attempts for implementation defects; V1 is judged first, then V2; if neither
qualifies, the result is FAIL. No question is asked. V1's tie
analysis above assumes `comment` is a single token (REM mechanism 1 or 3,
§3); if mechanism 2 was adopted, V1 is still tried first and judged only by
the criteria and expectations.

Inputs: the two BS-COND-007 registry fixtures and the spike fixtures
`BS-COND-007: spike S3` … `S12` and `R1` … `R3`, with their exact inputs and
their PASS (V1 and V2) and FAIL expectations in the workload-matrix catalogue;
incremental scripts E1–E6 are in workload W10.

Acceptance criteria (ADR-0004 decision 3), all required:

| ADR criterion | Evidence |
|---|---|
| C1 case-insensitive recognition, no mis-tokenising of `falsey`, with and without a trailing comment | S3, S4, S5, S12 |
| C2 `#else if`, `#else`, `#end if` recognised inside the body | `block comment with prose`, S6, S7, S11 |
| C3 nested conditional blocks balanced by the parser | S8 |
| C4 recovery does not swallow text outside the region | R1, R2 (R3: error present, no crash) |
| C5 incremental equality inside, around and across the region | E1–E6 |

C4 check (`scripts/check_spike.py`): parse R1 and R2 with `tree-sitter parse
--cst` and parse their repaired versions (the malformed line replaced by
`x = 1`). C4 holds when the repaired version has no error, every `ERROR` or
`MISSING` node (a named `MISSING` node prints as a zero-width node with the
has-error mark) lies within the malformed line, and every node that ends before
that line or starts after it has the same kind, start and end row and column,
and has-error mark in both parses (so an error hidden elsewhere also fails).
At the spike the check compared only the nodes after the line; the Session 03
review widened it. C5 check: for each script, the final tree of `tree-sitter parse
--edits` equals a fresh parse of the final text (same S-expression and
ranges); every script ends on error-free text.

Additional gate: no `conflicts` entry and no external scanner introduced by
the spike; every baseline COND fixture still passes.

| Outcome | Grammar | Schema | Fixtures | Records |
|---|---|---|---|---|
| PASS (taken) | the adopted design (V1 or V2) | `inactive_text` becomes public | every spike fixture takes its PASS expectation for the adopted design; E1–E6 stay in W10 | ADR-0004 status "literal-false opaque bodies adopted (V1 or V2)" with the C1–C5 evidence; KL-001 set to retired (unused) in validation.md |
| FAIL | spike rules removed; baseline kept (`false` is an ordinary `_cc_condition`) | no `inactive_text` | every spike fixture takes its FAIL expectation: inputs with non-BrightScript text assert `:error` and are listed as KL-001 demonstrating fixtures; code-only inputs stay positive; R1–R3 stay recovery fixtures; E1–E6 are recorded with the spike evidence and not added to W10 | ADR-0004 status "spike failed; baseline retained" with the failing criteria; KL-001 set to active, listing its fixtures |

Result (Session 03, WP15): PASS with design V1 at its first attempt; the
evidence is in [ADR-0004](../design/decisions/ADR-0004-conditional-compilation-representation.md#spike-result).
`false` is no longer a `_cc_condition`: after `#if` or `#else if` it selects
the `inactive_text` form.

## 12. Rule families

| Family | Purpose | Requirements | Public nodes (fields) | Conflicts / risks | Main fixture file (the catalogue decides per fixture) | Depends on |
|---|---|---|---|---|---|---|
| Line and file | statement lists, EOF, blank lines | BS-LEX-005–011, BS-STMT-033, 035 | `source_file`, `block` | block start terminator | `lexical.txt`, `bytes/*` | — |
| Comments | `'` and REM | BS-LEX-012–014 | `comment` | REM tie (§3) | `lexical.txt` | line |
| Identifiers and keywords | word token, `kw()` | BS-LEX-001, 015–026, BS-ERR-005 | `identifier` | keyword contextuality (§4) | `lexical.txt` | line |
| Literals | numbers, strings, booleans, `invalid`, `LINE_NUM` | BS-LIT-* | `number`, `string`, `true`, `false`, `invalid`, `source_literal` | fraction vs member dot | `literals.txt` | identifiers |
| Types | `AS` names | BS-TYPE-001 | `type` | type words contextual | `functions.txt` | keywords |
| Postfix expressions | call, member, index, attribute, optional forms | BS-EXP-003–010, 021, BS-ARRAY-007, BS-LIT-014, BS-LEX-029–031, 035 | `call_expression` (function, arguments), `argument_list`, `member_expression` (object, property), `index_expression` (object, index), `attribute_expression` (object, attribute) | `?` tokenisation; optional variants aliased to one node | `expressions.txt` | literals |
| Operators | unary, binary, grouping | BS-EXP-001, 002, 011–020, 027 | `unary_expression` (operator, operand), `binary_expression` (left, operator, right), `parenthesized_expression` | precedence only | `precedence.txt` | postfix |
| Collections | array and AA literals, DIM | BS-ARRAY-*, BS-AA-* | `array_literal`, `associative_array_literal`, `associative_array_entry` (key, value), `dim_statement` (name, dimension) | trailing `_sep` | `collections.txt` | operators, line |
| Simple statements | assignment, update, call, PRINT, RETURN, EXIT, CONTINUE, GOTO, labels, END, STOP, LIBRARY | BS-STMT-001–006, 018, 019, 023–034, 039, BS-LEX-027, 028 | `assignment_statement` (left, operator, right), `update_statement` (operand, operator), `print_statement`, `return_statement` (value), `exit_statement`, `continue_statement`, `goto_statement` (label), `label_statement` (name), `end_statement`, `stop_statement`, `library_statement` (path) | statement chains (§6); PRINT juxtaposition | `statements.txt` | collections |
| IF | single-line and block | BS-STMT-007–011, BS-LEX-032 | `if_statement` (condition, consequence, alternative), `else_if_clause` (condition, consequence), `else_clause` (body) | inline `:`/ELSE continuation (right precedence) | `if.txt` | simple statements |
| Loops | FOR, FOR EACH, WHILE | BS-STMT-012–022, 036 | `for_statement` (counter, start, end, step, body), `for_each_statement` (item, collection, body), `while_statement` (condition, body) | single-token terminators; NEXT | `loops.txt` | IF |
| Functions | declarations, anonymous functions, parameters | BS-FUNC-*, BS-TYPE-001 | `function_declaration` (name, parameters, return_type, body), `anonymous_function` (parameters, return_type, body), `parameter_list`, `parameter` (name, default, type), `type` | matching terminators | `functions.txt` | loops |
| Error handling | TRY, CATCH, THROW | BS-ERR-* | `try_statement` (body, handler), `catch_clause` (variable, body), `throw_statement` (value) | contextual `catch` via `_try_body` | `error-handling.txt` | functions |
| Conditional compilation | directives, spike | BS-COND-* | `const_directive` (name, value), `if_directive` (condition, consequence, alternative), `else_if_directive` (condition, consequence), `else_directive` (body), `error_directive` (message), `error_message`, `inactive_text` (PASS only) | spike (§11) | `conditional-compilation.txt` | all statements |

## 13. External scanner audit

| Candidate | Why a scanner might seem needed | Scanner-free design |
|---|---|---|
| Significant newlines | line-oriented language | newline token outside extras (§2) |
| Newlines inside literals and lists | context-dependent significance | explicit `_newline*` positions (§2, §9) |
| `REM` comments | keyword-shaped comment start | token tie rules with ordered fallbacks (§3) |
| `?` PRINT vs optional chaining | same first character | indivisible tokens + context-aware lexing (§3) |
| Single-line vs block IF | decided by the next token | LR(1) factoring (§6) |
| Literal-false bodies | opaque text | spike with a line token (§11, V1/V2); failure → KL-001, not a scanner |

No requirement needs lexer state; ADR-0005 stays closed.

## 14. Conflict policy

Expected ambiguity points and the planned mechanism:

| Point | Mechanism |
|---|---|
| assignment `=` vs comparison `=` | grammar factoring: assignment only at statement level (§6) |
| call vs member/index access | one postfix level, left-recursive chains |
| statement-level chain vs expression chain | separate hidden chains aliased to the same nodes (§6) |
| single-line vs block IF | LR(1) on the token after the condition |
| `:`/ELSE in nested single-line IFs | right precedence on `_inline_block` and the single-line IF |
| label vs colon separator | factoring: a bare identifier is never a statement |
| `?` alias vs optional chaining | lexical distinction (§3) |
| PRINT item juxtaposition | `LIST` precedence below every operator |
| operand of a postfix form vs PRINT item (`print a [1]`) | `POSTFIX` precedence on `_postfix_operand` (§5) |
| anonymous function vs declaration | LR(1): identifier vs `(` after `function`/`sub` |
| END vs END X | single tokens for the two-word terminators (§3) |
| ELSE vs ELSE IF, FOR vs FOR EACH, `#else` vs `#else if` | LR(1) one-token lookahead |
| `catch` at statement starts of other blocks | separate `_try_body` rule (§4) |
| literal-false spike | factoring on the condition token |

Policy: `conflicts` starts empty. A declared conflict needs (1) the generator's
conflict report, (2) a minimised input, (3) evidence that factoring,
precedence or associativity cannot resolve it without changing a documented
tree, and (4) a row added to this section naming the conflict, the rules and
the fixture proving the dynamic choice.

## 15. Implementation order

Each work package ends with its focused tests passing and V0 clean. Files are
those expected to change; `grammar.js` and regenerated `src/*` change in every
grammar package and land in the same commit.

Focused tests of a package are the fixtures of its requirements whose inputs
use only constructs implemented so far; a fixture that needs a later construct
is run from the first package where it becomes runnable. A mechanism chosen
early (the REM tie, §3) is confirmed when its last fixture becomes runnable.

Failure policy: diagnose → minimise → decide whether the grammar, the
toolchain, the runtime or the fixture expectation is wrong (an expectation is
wrong only if it contradicts the registry, this document or tree-schema; then
the document and the fixture change in one commit) → fix → focused tests →
regression tests → continue. After three failures of one mechanism without new
evidence, take the next documented fallback (§3 REM, §4 reserved words, §11
V2, ADR-0002 next release); when none remains, record a `KL-NNN` with its
fixture. Fixtures are never deleted, weakened or skipped otherwise, and
`tree-sitter test --update` is never used to write positive expectations.

Schema reconciliation (WP17): the grammar is changed until it produces the
planned public schema; the schema changes only where the generator cannot
produce it, with the reason recorded in the same commit.

| WP | Content | Requirements | Files | Focused tests | Exit criteria | Depends on | If the design assumption fails |
|---|---|---|---|---|---|---|---|
| 0 | Toolchain and bootstrap: adoption procedure, `package.json` (private, exact devDependency, scripts `generate` = `tree-sitter generate --abi 15`, `test` = `tree-sitter test`), lockfile, `tree-sitter.json` (name `brightscript`, scope `source.brs`, file type `brs`, version `0.1.0`, license MIT, all bindings disabled), minimal `grammar.js` (`source_file` of comments and terminators), V0 drift and registry checks as scripts, the ADR-0002 smoke fixtures | — | `package.json`, lockfile, `tree-sitter.json`, `grammar.js`, `src/*`, `scripts/*`, `test/corpus/lexical.txt` and `test/corpus/bytes/*` (smoke fixtures only), `.gitattributes` | generate twice, drift 0 | pinned identity recorded | — | ADR-0002 fallback order |
| 1 | Line model, comments, bytes corpus | BS-LEX-002–014, 033 | + `test/corpus/lexical.txt`, `test/corpus/bytes/*`, `.gitattributes` | runnable lexical and bytes fixtures | REM mechanism chosen; runnable fixtures pass | 0 | §3 REM fallbacks 2, 3 |
| 2 | Identifiers, `kw()`, word token | BS-LEX-001, 015–026 | `lexical.txt` | keyword-boundary fixtures | BS-LEX-024–026 pass | 1 | §4 fallback |
| 3 | Literals | BS-LIT-* | `literals.txt` | literal fixtures | all LIT fixtures | 2 | adjust token regex only |
| 4 | Types | BS-TYPE-001 | `functions.txt` (types part) | type fixtures | pass | 2 | — |
| 5 | Postfix expressions and `?` tokens | BS-EXP-001, 003–010, 021, BS-LEX-029–031, 035, BS-ARRAY-007 | `expressions.txt` | expression fixtures | pass, no conflicts | 3 | lexical precedence on `?` tokens only if a fixture proves it |
| 6 | Operators and precedence | BS-EXP-002, 011–020, 027 | `precedence.txt` | every §5 case | pass | 5 | none: precedence is fixed by §5 |
| 7 | Statement chains, assignment, update, call statements | BS-STMT-001–006, BS-EXP-008–010 | `statements.txt` | statement and negative fixtures | pass | 6 | §14 policy |
| 8 | Collections | BS-ARRAY-001–006, BS-AA-* | `collections.txt` | collection fixtures | pass | 7 | — |
| 9 | Blocks, labels, simple statements | BS-STMT-018, 019, 023–035, 039, BS-LEX-027, 028 | `statements.txt` | statement fixtures | pass | 8 | — |
| 10 | IF | BS-STMT-007–011, BS-LEX-032 | `if.txt` | IF fixtures | pass | 9 | §14 policy |
| 11 | Loops, terminator matching | BS-STMT-012–022, 036 | `loops.txt` | loop fixtures, KR-005 | pass | 10 | — |
| 12 | Functions | BS-FUNC-* | `functions.txt` | function fixtures | pass | 11 | — |
| 13 | TRY/CATCH/THROW | BS-ERR-* | `error-handling.txt` | ERR fixtures | pass | 12 | — |
| 14 | Conditional-compilation baseline | BS-COND-001–006, 008, 012 | `conditional-compilation.txt` | COND fixtures | pass | 13 | — |
| 15 | Literal-false spike | BS-COND-007 | same | BS-COND-007 fixtures, E1–E6 | PASS or FAIL recorded (§11) | 14 | §11 V2, then FAIL path |
| 16 | Recovery and remaining corpus | all | `recovery.txt` and any file still incomplete | full `tree-sitter test` | every registry fixture exists and passes | 15 | failure policy above |
| 17 | Schema reconciliation | tree-schema | `docs/specs/tree-schema.md` | `node-types.json` review | planned vs actual reconciled, catalogue filled | 16 | schema reconciliation rule above |
| 18 | `highlights.scm` | query | `queries/highlights.scm`, `test/highlight/*` | `tree-sitter test` highlight assertions, `tree-sitter query` compile | pass | 17 | — |
| 19–23 | V3 coverage update, V5, V6, V10, provenance | registry, validation | registry Coverage column, `docs/reports/` | workload matrix sets | release-candidate gate evidence | 18 | failure policy above |

Downstream parity (V9) and review follow in the implementation session plan;
they change no grammar design.
