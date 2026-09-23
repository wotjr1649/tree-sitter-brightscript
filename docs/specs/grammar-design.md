# Grammar design

The planned implementation structure of `grammar.js`: tokens, rule families,
precedence, statement boundaries, the conditional-compilation spike and the
implementation order. **Nothing here is implemented yet.** Requirements and
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
| Newline in `(`…`)` of calls | allowed after `(`, after `,`, before `)` | BS-EXP-024 | `BS-EXP-024: call arguments across lines` |
| Newline in parameter lists | allowed after `(`, after `,`, before `)` | BS-FUNC-006, 007 | `BS-FUNC-006: …`, `BS-FUNC-007: …` |
| Newline in grouping `(`…`)` or index `[`…`]` | no rule | BS-EXP-023 (unresolved) | — |
| Newline in array literals | after `[`, as element separator (with or without comma), before `]` | BS-ARRAY-002, 003 | `BS-ARRAY-002: …` |
| Newline in AA literals | after `{`, as entry separator (with or without comma), before `}` | BS-AA-003, 004 | `BS-AA-003: …` |
| Newline after a binary operator | no rule | BS-EXP-023 (unresolved) | — |
| Comment termination | `comment` stops before `\r` or `\n`; the newline is a separate `_newline` | BS-LEX-012 | `BS-LEX-012: comment after code on the same line` |
| REM termination | same as `'` | BS-LEX-013, 014 | `BS-LEX-013: …` |
| Label and colon | `label_statement` = identifier `:`; the next token must be a terminator | BS-LEX-027, 028 | `BS-LEX-027: label line` |
| Directive lines | a directive is a statement; `#error` text runs to the line end | BS-COND-008 | `BS-COND-008: indented directives with comments` |

Statement lists:

```text
source_file := (statement _terminator | _terminator)* statement?
block       := _terminator (statement _terminator | _terminator)*
_terminator := _newline | ':'
```

`block` always begins with the terminator that ends its header, so a block
exists even when the body is empty, and a header may end with `:` (BS-STMT-035).
The final optional `statement` in `source_file` gives EOF termination without
`eof()`.

Byte-sensitive fixtures (CRLF, BOM, trailing whitespace, final newline
variants) live under `test/corpus/bytes/`. The commit that adds the first of
them also adds `test/corpus/bytes/** -text` to `.gitattributes`. The Tree-sitter
test runner keeps interior line endings byte for byte and strips exactly one
final `\n` and a preceding `\r` from each input (Level 3,
`crates/cli/src/test.rs` @ `v0.27.0` and `v0.26.13`).

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
| `source_literal` | `kw('line_num')` aliased | public | `expression` | BS-LIT-019 |
| punctuation | `( ) [ ] { } , ; : . @ ? =` | anonymous | per rule | — |
| optional chaining | `?.` `?@` `?[` `?(` as single tokens | anonymous | postfix rules | BS-LEX-029, 030 |
| operators | `^ * / \ + - <> < > <= >= << >>`; words `kw('mod') kw('and') kw('or') kw('not')` | anonymous | `binary_expression`, `unary_expression` | BS-EXP-011–019 |
| assignment operators | `= += -= *= /= \= <<= >>=` | anonymous | `assignment_statement` | BS-STMT-001, 002 |
| update operators | `++ --` | anonymous | `update_statement` | BS-STMT-003, 004 |
| directive words | `#` immediately followed by `const`, `if`, `else`, `end` or `error` in any case, one token each, aliased to `#const`, `#if`, `#else`, `#end`, `#error` | anonymous | directive rules | BS-COND-001–005, 008 |
| `error_message` | `[^\r\n]+` with lexical precedence 1 (wins over `comment` for the same text); valid only after `#error` | public | `error_directive` | BS-COND-004 |

Details:

- Keyword boundaries come from keyword extraction: the lexer first matches the
  `word` token and only then checks the keyword table, so `iffy` or `endpoint`
  is one identifier (Level 3, "Keyword Extraction"; `crates/generate/src/build_tables.rs`
  @ `v0.27.0`). Multi-word keywords (`end if`, `else if`, `for each`,
  `exit while`, `#else if`, `#end if`) are **separate** keyword tokens, so any
  spaces or tabs may separate them and a newline may not (BS-STMT-022).
- A digit run followed by `.` and a letter is `number` then `.`: the fraction
  requires a digit after the point, so `5.tostr()` is member access
  (BS-LIT-014), and `5.` is not a number (BS-LIT-013, unresolved).
- The designator is part of `identifier`, not a separate node. `&` never
  starts an identifier, so `&hFF` is always a `number`.
- `?` alone is the PRINT alias. After an operand, `?.`, `?@`, `?[`, `?(` are
  preferred by longest match (`IF x?("Hello")` is an optional call,
  BS-LEX-032). At the start of a statement the optional-chaining tokens are not
  valid, so context-aware lexing yields `?` and `?.1`, `?("x")`, `?[1]` print
  (BS-LEX-031).
- `REM` versus `identifier`: for `remark`, `rem1`, `rem_x` the identifier is
  longer and wins. For `rem x` the comment is longer and wins. For exactly `rem`
  followed by a line end or EOF both match three characters: the comment must
  win (fixtures `BS-LEX-013: bare REM line`, `BS-LEX-014: …`). The comment token
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
- `#error` text: `error_message` consumes the rest of the line, including
  apostrophes (BS-COND-004).

## 4. Reserved words

Strategy: `word: $ => $.identifier`, every keyword through `kw()`, and **no
`reserved` word sets**. The runtime returns a keyword only where it has a parse
action in the current state (or is a reserved word there); otherwise the word
stays an `identifier` (Level 3, `lib/src/parser.c` @ `v0.27.0`,
`ts_parser__lex`). This makes every keyword contextual.

| Category | Words | Treatment | Requirements |
|---|---|---|---|
| A. Reserved grammar keywords | And Dim Each Else ElseIf End EndFunction EndIf EndSub EndWhile Exit ExitWhile False For Function Goto If Invalid LINE_NUM Next Not Or Print Return Step Stop Sub Then To True While (31) + Rem | `kw()` tokens; `Rem` is recognised by the `comment` token | BS-LEX-021, 013 |
| B. Reserved callable names | Box CreateObject Eval GetGlobalAA GetLastRunCompileError GetLastRunRunTimeError ObjFun Pos Run Tab Type (11) | ordinary `identifier`; calls are `call_expression` | BS-LEX-022, 023 |
| C. Reserved, no documented form | Let (1) | ordinary `identifier`; no LET rule | BS-STMT-034 |
| D. Syntax words not on the list | As Catch Continue EndTry In Library Mod Throw Try; type names Integer Float Double Boolean String Object Dynamic Void | `kw()` tokens, contextual | BS-LEX-025, BS-ERR-005, BS-TYPE-001 |

Categories A–C cover all 44 official reserved words.

Where a keyword and an identifier are both valid, the keyword wins. The
positions that matter are statement starts (`if for while try throw return
exit continue print dim goto end stop function sub library`, `catch` inside a
TRY body, `next` inside a FOR body, `else`/`elseif`/`end` inside IF bodies) and
operator positions after an operand (`and or mod`). Member names after
`.`/`?.`, AA keys, parameter names, loop variables and the operand of GOTO are
positions where no keyword is valid, so keyword words are identifiers there
(BS-LEX-024).

Required checks that keywords do not consume identifiers: the fixtures of
BS-LEX-001, 021, 024, 025, 026, BS-ERR-005 and BS-LIT-014.

Fallback, used only if one of those fixtures fails **because of** keyword
lexing in the pinned generator (for example issue #5925), after confirming the
fixture matches this document:

- add `reserved: { global: [category A keyword tokens], property: [] }`;
- wrap the identifier in member-name and AA-key positions with
  `reserved('property', …)`;
- keep category D contextual.

The fallback rejects more invalid programs (`step = 1`) and changes no tree of
a documented or provisional form. Record its adoption in this section.

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
level. A prefix operator binds its operand at its own level: `2^-2` is
`2^(-2)`; `-2^2` is `-(2^2)`; `a = not b` is `a = (not b)`.

Postfix operand kinds (BS-EXP-025):

| Postfix form | Accepted left operand |
|---|---|
| call, index | `identifier`, `parenthesized_expression`, `call_expression`, `member_expression`, `index_expression`, `attribute_expression` |
| member, attribute | the same, plus `number`, `string`, `array_literal`, `associative_array_literal` for member access |

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
_stmt_member := _stmt_chain '.' identifier            (alias member_expression)
_stmt_index  := _stmt_chain '[' expression (',' expression)* ']'   (alias index_expression)
_stmt_call   := _stmt_chain argument_list              (alias call_expression; '(' only)
call statement      := _stmt_call
_assignment_target  := identifier | _stmt_member | _stmt_index
```

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
| Single-line branch extent | `_inline_block` = `_inline_statement ( ':'+ _inline_statement )*`, right-precedence so `:` and `ELSE` continue the innermost single-line IF; ends at the enclosing `_terminator` that is a newline, or at EOF | BS-STMT-007, 009 |
| `_inline_statement` | assignment, update, call, PRINT, RETURN, EXIT, CONTINUE, GOTO, END, STOP, THROW, DIM, single-line IF | BS-STMT-009 |
| ELSE association | single-line: nearest unmatched single-line IF; block: `ELSE` after a block body belongs to the open block IF | BS-STMT-009, 010 |
| Block IF clauses | `ELSE IF`/`ELSEIF` + condition + optional THEN + `block`; `ELSE` + `block` | BS-STMT-010, 011 |
| Labels | `label_statement` only in `source_file`/`block` lists, never in single-line branches | BS-LEX-027, 028 |
| Comments at line end | extras; they never end a statement, the following `_newline` does | BS-LEX-012 |
| PRINT items | `print_statement` = (`print` or `?`) then any sequence of `expression`, `,`, `;`; the list has `LIST` precedence so every operator or postfix continuation extends the current item | BS-STMT-024–026 |
| Directive lines | directives are statements; their bodies are `block`s | BS-COND-002–008 |
| END vs END X | `end` followed by `if`/`for`/`while`/`sub`/`function`/`try` closes a block; `end` followed by a terminator is `end_statement` (one-token lookahead) | BS-STMT-029, 036 |
| NEXT | valid only as the terminator of the innermost open FOR/FOR EACH; elsewhere `next` is an identifier, so `NEXT` inside a WHILE body is an error | BS-STMT-013, 017 |

## 7. Top level

`source_file` accepts any statement list (§2): function and sub declarations,
LIBRARY, directives, ordinary statements, labels and comments, in any order,
including an empty file (BS-STMT-033, BS-LEX-008). Whether the Roku compiler
accepts statements outside functions is unresolved at Level 2; the grammar
accepts them (fragment tolerance) and makes no claim either way.

## 8. Functions and subs

```text
function_declaration := kw(function) name:identifier parameters:parameter_list
                        [kw(as) return_type:type] body:block (end function | endfunction)
                      | kw(sub) name:identifier parameters:parameter_list
                        body:block (end sub | endsub)
anonymous_function   := the same two forms without the name
parameter_list       := '(' _newline* [parameter (',' _newline* parameter)* _newline*] ')'
parameter            := name:identifier ['=' default:expression] [kw(as) type:type]
type                 := one of kw(integer float double boolean string object dynamic function void)
```

- FUNCTION and SUB share `function_declaration` and `anonymous_function`; the
  keyword is an anonymous child (tree-schema spelling table).
- A terminator matches its opener (BS-STMT-036): `function … end sub` is an
  error.
- SUB takes no `AS` clause (BS-FUNC-004, unresolved).
- Calls: `call_expression` = operand + `argument_list`;
  `argument_list` = (`(` or `?(`) `_newline*` [expression (`,` `_newline*`
  expression)* `_newline*`] `)`. Statement-level calls use `(` only (§6).
  Calls without parentheses have no rule.
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
  `_sep` gives the trailing comma (BS-ARRAY-003, BS-AA-004); two commas in a
  row are an error.
- `a[1,2,3]` is one `index_expression` with three `index` fields; `a[1][2][3]`
  is three nested ones (BS-ARRAY-007). No normalisation.
- AA keys that are keyword words are identifiers by contextual lexing
  (BS-LEX-024). Duplicate keys and key case are semantic (BS-AA-005).
- Newlines inside index brackets and DIM brackets have no rule.

## 10. TRY, CATCH, THROW

```text
try_statement   := kw(try) body:block handler:catch_clause (end try | endtry)
catch_clause    := kw(catch) variable:identifier body:block
throw_statement := kw(throw) value:expression
```

- Since 9.4 (BS-ERR-001–005). CATCH is required; a TRY without CATCH is an
  error (BS-ERR-006 has no rule). The variable is a single `identifier`, so the
  five illegal forms of BS-ERR-003 fail at the token after `catch`.
- `catch` ends the TRY body only as a statement-initial keyword inside that
  body; elsewhere it is an identifier (BS-ERR-005).
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
error_directive   := '#error' message:error_message?
_cc_condition     := identifier | true | false
```

Every branch body is an ordinary `block` of statements, so directives may wrap
statements or declarations and may nest (BS-COND-002–006). Conditions are
never evaluated. Because `#end` and `#else` are one-token directive words
followed by keyword tokens, `#endif`/`#elseif` happen to lex as `#end if` and
`#else if`; that acceptance is non-contractual (BS-COND-009).

### Literal-false spike (ADR-0004)

Run after the baseline passes its fixtures, before WP-18 (§15). Scope: the
body of an `#if false` or `#else if false` branch. The `#else` branch of a
literal `true` condition is **not** attempted (the ADR permits it; this
project does not need it for any documented form).

Planned PASS design:

```text
if_directive      += '#if' condition:false consequence:inactive_text …
else_if_directive += '#else' kw(if) condition:false consequence:inactive_text
_cc_condition     := identifier | true            (literal false moves to the forms above)
inactive_text     := _newline (_inactive_line | _newline | _inactive_if)*
_inactive_line    := token(prec(-1, [^ \t\r\n#'] [^\r\n]* | '#' [^\r\n]*))
_inactive_if      := '#if' _inactive_line? _newline (_inactive_line | _newline | _inactive_if)*
                     ('#else' _inactive_line? _newline (…)*)* '#end' kw(if)
```

`#if`, `#else` and `#end` carry lexical precedence 1 so they win over
`_inactive_line` at a line start; `comment` (precedence 0) wins over
`_inactive_line` (precedence −1), so `'` and `REM` lines inside the region stay
`comment` nodes; every other line of the region is hidden `_inactive_line`
text.

Spike inputs (added to `test/corpus/conditional-compilation.txt`; names start
with `BS-COND-007:`):

| ID | Input | Expected |
|---|---|---|
| S1 | documented prose block-comment example (independently worded) followed by a function | `if_directive` with `condition: (false)` `consequence: (inactive_text)`, then `function_declaration`; no `ERROR` |
| S2 | `#if false` around a complete function declaration | `inactive_text`; no declaration node inside |
| S3 | `#IF FALSE`, `#If False` | same as S1 |
| S4 | `#if falsey` around `x = 1` | ordinary `block` with `assignment_statement` |
| S5 | `#if false ' note` around prose | `inactive_text`, header comment is a `comment` |
| S6 | `#if false` prose `#else` `x = 1` `#end if` | `inactive_text`, then `else_directive` with a code `block` |
| S7 | `#if false` prose `#else if DEBUG` `x = 1` `#end if` | `inactive_text`, then `else_if_directive` with code |
| S8 | nested `#if DEBUG … #else … #end if` inside a false region, code after the region | balanced; code after the outer `#end if` is ordinary statements |
| S9 | `#const x = true` and `#error oops` lines inside a false region | part of `inactive_text`; no `const_directive`/`error_directive` |
| S10 | unbalanced quote and apostrophe prose inside a false region | `inactive_text`; comment lines only where the line starts with `'` or `REM ` |
| S11 | `#if DEBUG` … `#else if false` prose `#end if` | `else_if_directive` with `inactive_text` |
| R1 | a malformed line (`x = = 1`) before a valid false region and a valid function | `ERROR` confined to the first line; region and function unchanged |
| R2 | the same malformed line after the region | region unchanged |
| R3 | a false region without `#end if` at EOF | tree has `ERROR` or `MISSING`; no crash |
| E1–E6 | incremental edits (workload matrix W10): edit prose inside; insert a line before and after the region; delete and re-insert `#end if`; change `false` to `true` and back; insert `#else` inside | incremental tree equals the fresh parse (V5) |

Acceptance criteria (ADR-0004 decision 3), all required:

| ADR criterion | Evidence |
|---|---|
| C1 case-insensitive recognition, no mis-tokenising of `falsey`, with and without a trailing comment | S3, S4, S5 |
| C2 `#else if`, `#else`, `#end if` recognised inside the body | S1, S6, S7, S11 |
| C3 nested conditional blocks balanced by the parser | S8 |
| C4 recovery does not swallow text outside the region | R1, R2 (R3: no crash, error present) |
| C5 incremental equality inside, around and across the region | E1–E6 |

Additional gate: no `conflicts` entry and no external scanner introduced by
the spike; every baseline COND fixture still passes.

Attempt budget: the PASS design above plus at most two scanner-free variants
(for example `_inactive_line` at precedence 0 with directive words at 1; or
comment lines absorbed into `_inactive_line`). The first variant meeting all
criteria is adopted. If none does, the result is FAIL. No further question is
asked in either case.

| Outcome | Grammar | Schema | Fixtures | Records |
|---|---|---|---|---|
| PASS | PASS design kept | `inactive_text` becomes a public node | S1–S11, R1–R3 positive or `:error` as listed; `BS-COND-007: block comment with prose` positive | ADR-0004 status "literal-false opaque bodies adopted" with V5 evidence; KL-001 set to retired (unused) in validation.md |
| FAIL | spike rules removed; baseline kept (`false` is an ordinary `_cc_condition`) | no `inactive_text` | `BS-COND-007: block comment with prose` asserts `:error` and cites KL-001; `BS-COND-007: commented-out function` stays positive (its body is code) | ADR-0004 status "spike failed; baseline retained" with the failing criteria; KL-001 set to active; registry BS-COND-007 KL column keeps KL-001 |

## 12. Rule families

| Family | Purpose | Requirements | Public nodes (fields) | Conflicts / risks | Fixture files | Depends on |
|---|---|---|---|---|---|---|
| Line and file | statement lists, EOF, blank lines | BS-LEX-005–011, BS-STMT-033, 035 | `source_file`, `block` | block start terminator | `lexical.txt`, `bytes/*` | — |
| Comments | `'` and REM | BS-LEX-012–014 | `comment` | REM tie (§3) | `lexical.txt` | line |
| Identifiers and keywords | word token, `kw()` | BS-LEX-001, 015–026, BS-ERR-005 | `identifier` | keyword contextuality (§4) | `lexical.txt` | line |
| Literals | numbers, strings, booleans, `invalid`, `LINE_NUM` | BS-LIT-* | `number`, `string`, `true`, `false`, `invalid`, `source_literal` | fraction vs member dot | `literals.txt` | identifiers |
| Types | `AS` names | BS-TYPE-001 | `type` | type words contextual | `functions.txt` | keywords |
| Postfix expressions | call, member, index, attribute, optional forms | BS-EXP-003–010, 021, 025, BS-ARRAY-007, BS-LIT-014 | `call_expression` (function, arguments), `argument_list`, `member_expression` (object, property), `index_expression` (object, index), `attribute_expression` (object, attribute) | `?` tokenisation; optional variants aliased to one node | `expressions.txt` | literals |
| Operators | unary, binary, grouping | BS-EXP-001, 002, 011–020 | `unary_expression` (operator, operand), `binary_expression` (left, operator, right), `parenthesized_expression` | precedence only | `precedence.txt` | postfix |
| Collections | array and AA literals, DIM | BS-ARRAY-*, BS-AA-* | `array_literal`, `associative_array_literal`, `associative_array_entry` (key, value), `dim_statement` (name, dimension) | trailing `_sep` | `collections.txt` | operators, line |
| Simple statements | assignment, update, call, PRINT, RETURN, EXIT, CONTINUE, GOTO, labels, END, STOP, LIBRARY | BS-STMT-001–006, 018, 019, 023–034, BS-LEX-027, 028, 031 | `assignment_statement` (left, operator, right), `update_statement` (operand, operator), `print_statement`, `return_statement` (value), `exit_statement`, `continue_statement`, `goto_statement` (label), `label_statement` (name), `end_statement`, `stop_statement`, `library_statement` (path) | statement chains (§6); PRINT juxtaposition | `statements.txt` | collections |
| IF | single-line and block | BS-STMT-007–011, BS-LEX-032 | `if_statement` (condition, consequence, alternative), `else_if_clause` (condition, consequence), `else_clause` (body) | inline `:`/ELSE continuation (right precedence) | `if.txt` | simple statements |
| Loops | FOR, FOR EACH, WHILE | BS-STMT-012–022, 036 | `for_statement` (counter, start, end, step, body), `for_each_statement` (item, collection, body), `while_statement` (condition, body) | END vs END X; NEXT | `loops.txt` | IF |
| Functions | declarations, anonymous functions, parameters | BS-FUNC-*, BS-TYPE-001 | `function_declaration` (name, parameters, return_type, body), `anonymous_function` (parameters, return_type, body), `parameter_list`, `parameter` (name, default, type), `type` | matching terminators | `functions.txt` | loops |
| Error handling | TRY, CATCH, THROW | BS-ERR-* | `try_statement` (body, handler), `catch_clause` (variable, body), `throw_statement` (value) | contextual `catch` | `error-handling.txt` | functions |
| Conditional compilation | directives, spike | BS-COND-* | `const_directive` (name, value), `if_directive` (condition, consequence, alternative), `else_if_directive` (condition, consequence), `else_directive` (body), `error_directive` (message), `error_message`, `inactive_text` (PASS only) | spike (§11) | `conditional-compilation.txt` | all statements |

## 13. External scanner audit

| Candidate | Why a scanner might seem needed | Scanner-free design |
|---|---|---|
| Significant newlines | line-oriented language | newline token outside extras (§2) |
| Newlines inside literals and lists | context-dependent significance | explicit `_newline*` positions (§2, §9) |
| `REM` comments | keyword-shaped comment start | token tie rules with ordered fallbacks (§3) |
| `?` PRINT vs optional chaining | same first character | indivisible tokens + context-aware lexing (§3) |
| Single-line vs block IF | decided by the next token | LR(1) factoring (§6) |
| Literal-false bodies | opaque text | spike with prec −1 line token (§11); failure → KL-001, not a scanner |

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
| anonymous function vs declaration | LR(1): identifier vs `(` after `function`/`sub` |
| END vs END X, ELSE vs ELSE IF, FOR vs FOR EACH, `#else` vs `#else if` | LR(1) one-token lookahead |
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

| WP | Content | Requirements | Files | Focused tests | Exit criteria | Depends on | If the design assumption fails |
|---|---|---|---|---|---|---|---|
| 0 | Toolchain and bootstrap: adoption procedure, `package.json` (private, exact devDependency, scripts `generate` = `tree-sitter generate --abi 15`, `test` = `tree-sitter test`), lockfile, `tree-sitter.json` (name `brightscript`, scope `source.brs`, file type `brs`, version `0.1.0`, license MIT, all bindings disabled), minimal `grammar.js` (`source_file` of comments and terminators), V0 drift and registry checks as scripts | — | `package.json`, lockfile, `tree-sitter.json`, `grammar.js`, `src/*`, `scripts/*` | generate twice, drift 0 | pinned identity recorded | — | ADR-0002 fallback order |
| 1 | Line model, comments, bytes corpus | BS-LEX-002–014, 033 | + `test/corpus/lexical.txt`, `test/corpus/bytes/*`, `.gitattributes` | lexical and bytes fixtures | REM fixtures pass | 0 | §3 REM fallbacks 2, 3 |
| 2 | Identifiers, `kw()`, word token | BS-LEX-001, 015–026 | `lexical.txt` | keyword-boundary fixtures | BS-LEX-024–026 pass | 1 | §4 fallback |
| 3 | Literals | BS-LIT-* | `literals.txt` | literal fixtures | all LIT fixtures | 2 | adjust token regex only |
| 4 | Types | BS-TYPE-001 | `functions.txt` (types part) | type fixtures | pass | 2 | — |
| 5 | Postfix expressions and `?` tokens | BS-EXP-001, 003–010, 021, 025, BS-LEX-029–031, BS-ARRAY-007 | `expressions.txt` | expression fixtures | pass, no conflicts | 3 | lexical precedence on `?` tokens only if a fixture proves it |
| 6 | Operators and precedence | BS-EXP-002, 011–020 | `precedence.txt` | every §5 case | pass | 5 | none: precedence is fixed by §5 |
| 7 | Statement chains, assignment, update, call statements | BS-STMT-001–006, BS-EXP-008–010 | `statements.txt` | statement and negative fixtures | pass | 6 | §14 policy |
| 8 | Collections | BS-ARRAY-001–006, BS-AA-* | `collections.txt` | collection fixtures | pass | 7 | — |
| 9 | Blocks, labels, simple statements | BS-STMT-018, 019, 023–035, BS-LEX-027, 028 | `statements.txt` | statement fixtures | pass | 8 | — |
| 10 | IF | BS-STMT-007–011, BS-LEX-032 | `if.txt` | IF fixtures | pass | 9 | §14 policy |
| 11 | Loops, terminator matching | BS-STMT-012–022, 036 | `loops.txt` | loop fixtures, KR-005 | pass | 10 | — |
| 12 | Functions | BS-FUNC-* | `functions.txt` | function fixtures | pass | 11 | — |
| 13 | TRY/CATCH/THROW | BS-ERR-* | `error-handling.txt` | ERR fixtures | pass | 12 | — |
| 14 | Conditional-compilation baseline | BS-COND-001–006, 008 | `conditional-compilation.txt` | COND fixtures | pass | 13 | — |
| 15 | Literal-false spike | BS-COND-007 | same | S1–S11, R1–R3, E1–E6 | PASS or FAIL recorded (§11) | 14 | §11 FAIL path |
| 16 | Official-example, recovery and remaining corpus | all | `official-examples.txt`, `recovery.txt` | full `tree-sitter test` | every registry fixture exists and passes | 15 | fix grammar; never weaken fixtures |
| 17 | Schema reconciliation | tree-schema | `docs/specs/tree-schema.md` | `node-types.json` review | planned vs actual reconciled, catalogue filled | 16 | record deviations and bump rules |
| 18 | `highlights.scm` | query | `queries/highlights.scm`, `test/highlight/*` | `tree-sitter test` highlight assertions, `tree-sitter query` compile | pass | 17 | — |
| 19–23 | V3 coverage update, V5, V6, V10, provenance | registry, validation | registry Coverage column, `docs/reports/` | workload matrix sets | release-candidate gate evidence | 18 | failure policy of the implementation session |

Downstream parity (V9) and review follow in the implementation session plan;
they change no grammar design.
