# Language conformance registry

The single place where BrightScript language requirements are defined and
traced. Grammar rules, fixtures and release claims refer to the IDs below.

Status: **registry populated (Session 02 specification freeze); nothing is
implemented.** Every requirement was promoted from the local research
inventory in `_ref/normative/roku-docs/notes/` after re-checking it against the
Level 1 snapshot, following [source-policy.md](../provenance/source-policy.md).
The `Grammar` column names planned rule families (`planned: …`) defined in
`docs/specs/grammar-design.md`; fixture inputs are catalogued in
`docs/validation/workload-matrix.md`. No requirement is `covered` yet.

## Traceability chain

Evidence (Level 1/2; Level 4 only for `tolerated`) → requirement (`BS-*`) →
grammar rule → positive fixture → negative or recovery fixture (where the
acceptance policy allows one) → status.

## Requirement IDs

Format: `BS-<AREA>-<NNN>`, three digits, allocated in order within an area,
never reused. A withdrawn requirement keeps its ID with status `retired` and a
reason.

| Area | Covers |
|---|---|
| `LEX` | case, whitespace, line structure, `:` separators, comments, identifiers, type designators, reserved words, labels, operator tokens |
| `LIT` | boolean, `invalid`, numeric, string and source literals |
| `TYPE` | type names in `AS` clauses |
| `EXP` | expressions, operators, precedence, calls, member/index/optional access |
| `STMT` | statements other than function declarations and error handling |
| `FUNC` | `FUNCTION`/`SUB` declarations, parameters, anonymous functions |
| `ARRAY` | array literals, `DIM`, multidimensional indexing |
| `AA` | associative-array literals and keys |
| `ERR` | `TRY`/`CATCH`/`THROW` |
| `COND` | conditional compilation (`#const`, `#if`, `#else if`, `#else`, `#end if`, `#error`) |

Roku OS availability is a field (`since`), not an area. Local research labels
from `_ref` (`LEX-01`, `AMB-20`, …) are never used as IDs; they appear only in
the Notes column and the reconciliation tables as pointers into the research.

## Record fields

| Field | Content |
|---|---|
| ID | `BS-<AREA>-<NNN>` |
| Requirement | Paraphrased, testable statement |
| Evidence | Level 1 page + section + snapshot ID; Level 2 record if any; Level 4 references if used |
| Since | Roku OS version, `baseline` (no version stated) or `unknown` |
| Status | see below |
| Grammar | rule name(s); `planned: …` until the rule exists, `none` when no rule is added |
| Positive fixtures | corpus test names |
| Negative / recovery fixtures | corpus test names, or `n/a` with reason |
| Coverage | `none`, `partial`, `covered` |
| Known limitations | `KL-NNN` IDs from [validation.md](../validation/validation.md), if any |
| Notes | ambiguities, disagreements between sources, known incompatibilities |

## Status vocabulary

| Status | Meaning | Grammar obligation |
|---|---|---|
| `documented` | Level 1 states the form | Must parse without `ERROR`/`MISSING` |
| `provisional` | Needs Level 2 evidence; the grammar makes a disclosed choice | Behaviour may change when evidence arrives |
| `tolerated` | Undocumented; accepted on Level 4 or Level 2 evidence | Must not change trees of documented forms |
| `unresolved` | No decision and no evidence either way | No contractual behaviour |
| `invalid` | Level 1 or Level 2 states the form is invalid or unsupported | Negative fixture expects an error |
| `out-of-scope` | Semantic or runtime rule | Recorded so it is not turned into grammar |
| `retired` | Withdrawn requirement | None |

A requirement is `covered` when its grammar rule exists and its required
fixtures pass at the gates in [validation.md](../validation/validation.md).

Implementation rules per status (frozen for the first implementation):

- `documented` and `provisional`: the rule is implemented exactly as stated and
  every listed positive fixture passes. A `provisional` row is implemented, not
  deferred; it states the chosen behaviour.
- `invalid`: every listed negative fixture yields `ERROR` or `MISSING`.
- `unresolved`: no rule is added for the form and no corpus fixture asserts its
  tree. Whatever the grammar built for documented forms produces is
  non-contractual. Such inputs may appear only as robustness seeds (V10).
- `out-of-scope`: no rule. Rows marked "(guard)" have a positive fixture that
  shows the grammar does **not** enforce the semantic rule.

## Fixture naming

Corpus test names start with the requirement ID they exercise, for example
`BS-STMT-012: FOR with and without STEP`. A fixture may cite several IDs.

## Registry

Evidence cites Level 1 snapshot `roku-docs-2026-09-23`
([upstream-sources.md](../provenance/upstream-sources.md)) unless stated
otherwise. Page keys (routes under `https://developer.roku.com/dev/docs/`):

| Key | Page | Route |
|---|---|---|
| LR | BrightScript language reference | `brightscript-language-reference` |
| SS | Statement summary | `statement-summary` |
| PS | Program statements | `program-statements` |
| EVT | Expressions, variables, and types | `expressions-variables-types` |
| RW | Reserved words | `reserved-words` |
| CC | Conditional compilation | `conditional-compilation` |
| EH | Error handling in BrightScript | `error-handling` |
| RN | Release notes | `release-notes` |
| CA | Component architecture | `component-architecture` |
| RF | Runtime functions | `runtime-functions` |

Coverage is `none` for every row until the first implementation; the column is
kept so that the record format stays uniform. `—` means no known limitation.

### LEX

| ID | Requirement | Evidence | Since | Status | Grammar | Positive fixtures | Negative / recovery fixtures | Coverage | KL | Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| BS-LEX-001 | Keywords, reserved words, identifiers and directive words match regardless of letter case; string contents keep their case. | SS (body); EVT §Identifiers; CC §Criteria | baseline | documented | planned: `kw()` keyword tokens, `identifier` | `BS-LEX-001: keywords in upper, lower and mixed case`<br>`BS-LEX-001: identifier spellings differing only in case` | n/a — no invalid form | none | — | LEX-01 |
| BS-LEX-002 | Space characters separate tokens; indentation and repeated spaces are insignificant. | SS, PS examples | baseline | documented | planned: extras (whitespace) | `BS-LEX-002: indentation and repeated spaces` | n/a | none | — | LEX-02 |
| BS-LEX-003 | Horizontal tab is whitespace equivalent to a space. No other character (form feed, vertical tab, U+00A0, other Unicode spaces) is whitespace. | L1 does not list whitespace characters | unknown | provisional | planned: extras (whitespace) | `BS-LEX-003: tab indentation and tabs between tokens` | n/a | none | — | LEX-02, AMB-32. Level 2 could widen the set; widening is compatible. |
| BS-LEX-004 | Adjacent tokens need no whitespace where the boundary is unambiguous (`print"error"`, `x=5:print 25`, `function():return m.xml@title:end function`, `tab(5)"tabbed 5"`). A keyword directly followed by identifier characters is one word (BS-LEX-026). | PS §DIM, §PRINT item list; CA §Attribute operator | baseline | documented | planned: lexer (no rule) | `BS-LEX-004: keyword directly followed by a string`<br>`BS-LEX-004: compact one-line anonymous function` | n/a | none | — | LEX-02, AMB-32 |
| BS-LEX-005 | The language is line oriented: a statement ends at the end of its line unless another follows after `:`. There is no line-continuation character. | SS (body); PS §IF expression THEN statements | baseline | documented | planned: `_newline`, `_terminator` | `BS-LEX-005: one statement per line` | n/a — continuation is BS-EXP-023 | none | — | LEX-03, LEX-05, LINE-01 |
| BS-LEX-006 | LF and CRLF both terminate a line; one file may mix them; trees are identical apart from byte offsets. | L1 does not name terminator bytes | unknown | provisional | planned: `_newline` | `BS-LEX-006: CRLF line endings`<br>`BS-LEX-006: mixed LF and CRLF line endings` | n/a | none | — | LEX-03, AMB-07. Byte fixtures (validation fixture rules). |
| BS-LEX-007 | A bare CR (not followed by LF) as a line terminator. | none | unknown | unresolved | none — bare CR is neither whitespace nor terminator | n/a — unresolved | n/a | none | — | LEX-03, AMB-07 |
| BS-LEX-008 | End of file terminates the last line: a final statement, comment or block terminator needs no line terminator; an empty file and a file of only blank lines and comments parse without error. | L1 silent | unknown | provisional | planned: `source_file` | `BS-LEX-008: final line without a line terminator`<br>`BS-LEX-008: final line with a line terminator`<br>`BS-LEX-008: empty file`<br>`BS-LEX-008: only comments and blank lines` | n/a | none | — | LINE-04, AMB-07 |
| BS-LEX-009 | Blank lines may appear before, between and after statements, inside block bodies and before block terminators. | multi-line examples on SS, PS, EVT, CC | baseline | documented | planned: `source_file`, `block` | `BS-LEX-009: blank lines around and inside blocks` | n/a | none | — | LINE-03 |
| BS-LEX-010 | `:` separates statements on one line in every statement list: file level, block bodies and single-line IF branches. | SS (body, example); PS §PRINT item list, §DIM | baseline | documented | planned: `_terminator` | `BS-LEX-010: colon-separated statements`<br>`BS-LEX-010: colon-separated statements in a block body` | n/a | none | — | LEX-04, LINE-02 |
| BS-LEX-011 | In file-level and block statement lists any run of `:` and line terminators separates statements; leading, repeated and trailing colons produce no node. | L1 silent | unknown | provisional | planned: `_terminator` | `BS-LEX-011: repeated, leading and trailing colons` | n/a | none | — | AMB-08. Single-line IF branches: BS-STMT-009. |
| BS-LEX-012 | `'` starts a comment that runs to the end of the line; it may stand alone or follow code; inside a string it is text. | EVT §Comments › In BrightScript; PS §REM | baseline | documented | planned: `comment` (extra) | `BS-LEX-012: apostrophe comment lines`<br>`BS-LEX-012: comment after code on the same line`<br>`BS-LEX-012: apostrophe inside a string` | n/a | none | — | LEX-06 |
| BS-LEX-013 | `REM` in any letter case starts a comment that runs to the end of the line, including a line that holds only `REM`. | PS §REM; SS; EVT §Comments | baseline | documented | planned: `comment` (extra) | `BS-LEX-013: REM comments in mixed case`<br>`BS-LEX-013: bare REM line` | n/a | none | — | LEX-06, STM-13 |
| BS-LEX-014 | `REM` starts a comment only as a whole word followed by space, tab, line end or file end, at line start, after code and after `:`. `remark`, `rem1`, `rem_x` are identifiers. `rem` directly followed by another character (`rem:`, `rem(`) has no contractual behaviour. After `.` the same rule applies, so `obj.rem` at line end is a comment. | L1 silent on the boundary | unknown | provisional | planned: `comment` token shape | `BS-LEX-014: identifiers beginning with rem`<br>`BS-LEX-014: REM after code and after a colon` | n/a | none | — | AMB-12 |
| BS-LEX-015 | Identifier: an ASCII letter or `_`, then ASCII letters, digits or `_`, any length. | EVT §Identifiers | baseline | documented | planned: `identifier` (word token) | `BS-LEX-015: identifier forms` | n/a | none | — | LEX-07 |
| BS-LEX-016 | Non-ASCII letters in identifiers. | EVT §Identifiers ("a – z") | unknown | unresolved | none | n/a — unresolved | n/a | none | — | LEX-07, AMB-09 |
| BS-LEX-017 | A variable name may end with one designator `$`, `%`, `!` or `#`. The designator is part of the identifier token, so `a`, `a$` and `a%` are different identifiers. | EVT §Identifiers, §Type declaration characters | baseline | documented | planned: `identifier` | `BS-LEX-017: variables with type designators` | n/a | none | — | LEX-08, TYP-03 |
| BS-LEX-018 | The `&` designator (LongInteger) on variable names (`A&`, `ID&`). | EVT §Type declaration characters, §Types | 7.0 | documented | planned: `identifier` | `BS-LEX-018: LongInteger designator on a variable` | n/a | none | — | LEX-08, VER-10 |
| BS-LEX-019 | Function names do not take type designators. Compile-time rule; the shared identifier token accepts a designator on a function name. | EVT §Identifiers | baseline | out-of-scope | none | n/a | n/a | none | — | FUN-04 |
| BS-LEX-020 | Designators on parameters, loop variables, CATCH variables, member names, AA identifier keys, labels and GOTO targets. | none | unknown | unresolved | none added — the shared identifier token accepts them | n/a — unresolved | n/a | none | — | AMB-09 |
| BS-LEX-021 | Reserved words that are grammar keywords (`And Dim Each Else ElseIf End EndFunction EndIf EndSub EndWhile Exit ExitWhile False For Function Goto If Invalid LINE_NUM Next Not Or Print Rem Return Step Stop Sub Then To True While`) are recognised as keywords in any letter case wherever the grammar expects them. | RW; PS; EVT | baseline | documented | planned: `kw()`, `word: identifier` | `BS-LEX-021: reserved keywords in statement positions` | n/a | none | — | LEX-09, AMB-01 |
| BS-LEX-022 | Reserved callable names (`Box CreateObject Eval GetGlobalAA GetLastRunCompileError GetLastRunRunTimeError ObjFun Pos Run Tab Type`) use ordinary call syntax and parse as a `call_expression` on an `identifier`, including `Tab`/`Pos` in PRINT lists. | RW; RF; PS §PRINT item list | baseline | documented | planned: `identifier`, `call_expression` | `BS-LEX-022: reserved built-in function calls` | n/a | none | — | FUN-07, AMB-01, AMB-24 |
| BS-LEX-023 | A reserved word used as a variable, function, parameter or label name is a compile error. The grammar rejects such a use only where the word is a grammar keyword in that position (statement-initial `end = 1`); `step = 1` or `box = 1` are not rejected. | RW | baseline | out-of-scope | none — keyword extraction only | n/a | n/a | none | — | AMB-01, AMB-24 |
| BS-LEX-024 | Keyword words are accepted as member names after `.`/`?.` and as identifier keys in associative-array literals (`{ function: "main()" }`, `list.next()`), except `rem` (BS-LEX-014). | EH §Invalid throws (`function` used as a key in source code); conflicts with EVT §Identifiers prose | unknown | provisional | planned: `identifier` through contextual keyword extraction | `BS-LEX-024: keywords as member names`<br>`BS-LEX-024: keywords as associative-array keys` | n/a | none | — | AMB-01, LIT-12, EXP-03. Tightening later would reject the L1 example. |
| BS-LEX-025 | Words that act as syntax but are not on the reserved list (`As Catch Continue In Library Mod Throw Try`, the `AS` type names, `EndTry`) are keywords only where the grammar expects them and identifiers elsewhere (`mod = 3`, `x = in + as`). Statement-initial `try`, `throw`, `continue`, `library`, and statement-initial `catch` inside a TRY body, always start their statements. | RW (absence); PS §TRY / CATCH, §THROW; EVT §Operators; CA §Script libraries | unknown | provisional | planned: `kw()` with contextual keyword extraction | `BS-LEX-025: non-reserved keyword words as identifiers` | n/a | none | — | LEX-10, AMB-02; candidate "`mod` as a variable name" (Level 4 claim, not used as evidence). Known incompatibility: pre-9.4 and pre-11.5 code using `try`, `catch`, `throw`, `continue` as statement-initial names. |
| BS-LEX-026 | Keyword recognition respects word boundaries: an identifier that begins with a keyword (`iffy`, `endpoint`, `format`, `printer`, `nextItem`, `stepSize`, `notify`, `order`, `android`, `returnValue`, `falsey`) is one identifier. | EVT §Identifiers | baseline | documented | planned: `word: identifier` | `BS-LEX-026: identifiers beginning with keywords` | n/a | none | — | LEX-07 |
| BS-LEX-027 | A label is an identifier followed by `:` on a line by itself; it is the target of GOTO. | PS §GOTO label; CA §Scope | baseline | documented | planned: `label_statement` | `BS-LEX-027: label line` | n/a | none | — | LEX-11 |
| BS-LEX-028 | A label line may end with a comment. Code after a label on the same line has no contractual behaviour. | L1 silent | unknown | provisional | planned: `label_statement` | `BS-LEX-028: label followed by a comment` | n/a | none | — | AMB-08 |
| BS-LEX-029 | Optional-chaining operators `?.`, `?@`, `?[`, `?(` are indivisible tokens; whitespace may precede them (`a = b ?. c`, `x = s ?[ 5 ]`). | EVT §Optional chaining operators › Notes | 11.0 | documented | planned: tokens `?.` `?@` `?[` `?(` | `BS-LEX-029: optional-chaining tokens after whitespace` | n/a | none | — | LEX-12, AMB-16 |
| BS-LEX-030 | `?` separated from `.` by whitespace (`a = b ? . c`) is not an optional-chaining operator. | EVT §Optional chaining operators › Notes ("Do not write") | 11.0 | invalid | planned: tokenization | n/a | `BS-LEX-030: split optional-chaining token` | none | — | AMB-16 |
| BS-LEX-031 | At the start of a statement `?` is PRINT, also when directly followed by `(`, `.`+digit or `[` (`?("Hello")`, `?.1`, `?[1]`). | EVT §Optional chaining operators › Support details; SS | baseline | documented | planned: `print_statement` | `BS-LEX-031: question-mark PRINT alias forms` | n/a | none | — | LEX-13, AMB-16 |
| BS-LEX-032 | `IF x?("Hello")` at the end of its line begins a block IF whose condition is an optional call; it does not print. | EVT §Optional chaining operators › Support details | unknown | documented | planned: `if_statement`, `call_expression` | `BS-LEX-032: IF with an optional call starts a block IF` | n/a | none | — | VER-20, AMB-16. Known incompatibility: older firmware printed. |
| BS-LEX-033 | Source text is UTF-8; a leading UTF-8 byte-order mark is ignored; non-ASCII characters are ordinary content in comments and strings. | CA §BrightScript XML support (encoding stated for XML only); Tree-sitter `lib/src/lexer.c` @ `v0.27.0` skips a leading BOM (Level 3) | unknown | provisional | planned: `string`, `comment` | `BS-LEX-033: UTF-8 text in comments and strings`<br>`BS-LEX-033: leading byte-order mark` | n/a | none | — | LINE-06, AMB-11 |
| BS-LEX-034 | Other encodings (UTF-16, Latin-1), invalid UTF-8 and NUL bytes. | none | unknown | unresolved | none | n/a — unresolved | n/a | none | — | LINE-06 |

### LIT

| ID | Requirement | Evidence | Since | Status | Grammar | Positive fixtures | Negative / recovery fixtures | Coverage | KL | Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| BS-LIT-001 | `true` and `false` in any letter case. | EVT §Literals (constants) | baseline | documented | planned: `true`, `false` | `BS-LIT-001: boolean literals` | n/a | none | — | LIT-01 |
| BS-LIT-002 | `invalid` in any letter case. | EVT §Literals, §Types | baseline | documented | planned: `invalid` | `BS-LIT-002: invalid literal` | n/a | none | — | LIT-02 |
| BS-LIT-003 | Decimal integer literal: one or more digits. | EVT §Numeric literals | baseline | documented | planned: `number` | `BS-LIT-003: decimal integers` | n/a | none | — | LIT-03 |
| BS-LIT-004 | There is no signed literal; `-5` is unary negation applied to `5`. | EVT §Negation operator, §Numeric literals | baseline | documented | planned: `unary_expression` | `BS-LIT-004: negative number is unary negation` | n/a | none | — | LIT-03, AMB-10 |
| BS-LIT-005 | Hex integer: `&H` or `&h` followed by hex digits (`&HFF`, `&hFF`, `&h28`). | EVT §Numeric literals; EH; RF | baseline | documented | planned: `number` | `BS-LIT-005: hex integers with either prefix case` | n/a | none | — | LIT-04 |
| BS-LIT-006 | Lowercase hex digits (`&hff`, `&hFe`). | L1 examples use uppercase digits only | unknown | provisional | planned: `number` | `BS-LIT-006: lowercase hex digits` | n/a | none | — | LIT-04, AMB-10 |
| BS-LIT-007 | Float forms: decimal point (`2.01`), `E` exponent with optional sign (`1.23456E+30`), `!` suffix (`2!`, `125!`). | EVT §Numeric literals, §Type declaration characters | baseline | documented | planned: `number` | `BS-LIT-007: float literal forms` | n/a | none | — | LIT-05, LIT-08 |
| BS-LIT-008 | Lowercase `e`, unsigned exponent (`1e1000000`) and leading-dot fraction (`.1`). | EH §Miscellaneous examples; EVT §Optional chaining operators › Support details (`?.1`) | baseline | documented | planned: `number` | `BS-LIT-008: lowercase unsigned exponent and leading-dot fraction` | n/a | none | — | LIT-05, AMB-10 |
| BS-LIT-009 | Double forms: `D` exponent (`1.23456789D-12`), `#` suffix (`2.3#`, `125#`). | EVT §Numeric literals, §Type declaration characters | baseline | documented | planned: `number` | `BS-LIT-009: double literal forms` | n/a | none | — | LIT-06 |
| BS-LIT-010 | Lowercase `d` exponent (`1.5d-3`). | L1 examples use uppercase only | unknown | provisional | planned: `number` | `BS-LIT-010: lowercase d exponent` | n/a | none | — | AMB-10 |
| BS-LIT-011 | LongInteger literal: `&` suffix on decimal (`9876543210&`) and hex (`&hFEDCBA9876543210&`) integers. | EVT §Numeric literals, §Types; RN §Roku OS 7.0 | 7.0 | documented | planned: `number` | `BS-LIT-011: LongInteger literals` | n/a | none | — | LIT-07, VER-10 |
| BS-LIT-012 | `%` suffix on integer literals (`125%`, `100%`). | EVT §Type declaration characters; CA §Use of wrapper functions on intrinsic types | baseline | documented | planned: `number` | `BS-LIT-012: integer suffix on a literal` | n/a | none | — | LIT-08 |
| BS-LIT-013 | Other numeric forms: trailing dot (`5.`), suffixes other than `&` on hex (`&hFF%`), `&h` without digits, `5.e3`. | none | unknown | unresolved | none beyond the planned `number` token shape | n/a — unresolved | n/a | none | — | AMB-10 |
| BS-LIT-014 | After digits, `.` followed by a letter is member access, not a fraction: `5.tostr()`, `100%.tostr()`, `"5".toint()`, `"01234567".left(3)`. | CA §Use of wrapper functions on intrinsic types | baseline | documented | planned: `number` token shape, `member_expression` | `BS-LIT-014: method call on a numeric literal`<br>`BS-LIT-014: method call on a string literal` | n/a | none | — | LIT-09 |
| BS-LIT-015 | String literal: text between double quotes on one line. | EVT §String literals | baseline | documented | planned: `string` | `BS-LIT-015: string literals` | `BS-LIT-015: unterminated string at end of line` (recovery) | none | — | LIT-10 |
| BS-LIT-016 | `""` inside a string is one quotation mark; `""""` is a one-character string. | EVT §String literals; RN §Roku OS 6.2 | 6.2 | documented | planned: `string` | `BS-LIT-016: doubled quotation marks` | n/a | none | — | LIT-10, VER-08 |
| BS-LIT-017 | No other escape mechanism: backslash and every character except `"` and line terminators are literal string content. | EVT §String literals (only `""` documented) | unknown | provisional | planned: `string` | `BS-LIT-017: backslash and non-ASCII text in strings` | n/a | none | — | LIT-10, AMB-11 |
| BS-LIT-018 | Strings spanning lines. | none | unknown | unresolved | none — a line terminator ends string scanning | n/a — unresolved | n/a | none | — | AMB-11 |
| BS-LIT-019 | `LINE_NUM` source literal (reserved word). | EVT §Source literals; RW; RF §Run | baseline | documented | planned: `source_literal` | `BS-LIT-019: LINE_NUM source literal` | n/a | none | — | LEX-14 |
| BS-LIT-020 | A function name used as a value (`fivevar = five`) is an ordinary identifier expression. | EVT §Function literals, §Function call operator | baseline | documented | planned: `identifier` | `BS-LIT-020: function name used as a value` | n/a | none | — | LIT-13 |

### TYPE

| ID | Requirement | Evidence | Since | Status | Grammar | Positive fixtures | Negative / recovery fixtures | Coverage | KL | Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| BS-TYPE-001 | `AS` type names in any letter case: `Integer Float Double Boolean String Object Dynamic Function`, plus `Void` for return types. One `type` rule serves parameters and return types. | PS §FUNCTION(…) AS type; RN §Roku OS 3.0, §Roku OS 4.1 ("typed values in function parameters and returns") | 3.0 | documented | planned: `type` | `BS-TYPE-001: parameter and return type names` | n/a | none | — | TYP-01, VER-01. `void` on a parameter is accepted by the shared rule (non-contractual). |
| BS-TYPE-002 | `LongInteger`, `Interface` and `Invalid` as `AS` type names. | EVT §Types lists the types, not their use in `AS` | unknown | unresolved | none | n/a — unresolved | n/a | none | — | TYP-02, AMB-26 |
| BS-TYPE-003 | Dynamic typing, declared-type conversion, promotion, rounding, autoboxing and `type()` results. | EVT §Types, §Type conversion (promotion), §Effects of type conversions on accuracy; CA | baseline | out-of-scope | none | n/a | n/a | none | — | TYP-04 |

### EXP

| ID | Requirement | Evidence | Since | Status | Grammar | Positive fixtures | Negative / recovery fixtures | Coverage | KL | Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| BS-EXP-001 | Primary expressions: identifiers, literals, `LINE_NUM`, parenthesized expressions, array and associative-array literals, anonymous functions. | EVT §Literals (constants), §Function call operator; PS §Anonymous functions | baseline | documented | planned: `expression` supertype | `BS-EXP-001: primary expressions` | n/a | none | — | EXP-01 |
| BS-EXP-002 | Parentheses group an expression and override precedence. | EVT §Operators | baseline | documented | planned: `parenthesized_expression` | `BS-EXP-002: parentheses override precedence` | `BS-EXP-002: unclosed parenthesis` (recovery) | none | — | EXP-01 |
| BS-EXP-003 | Call: an expression followed by `(`, zero or more comma-separated arguments and `)` (`five()`, `fivevar()`, `array[1]()`, `obj.add()`). | EVT §Function call operator | baseline | documented | planned: `call_expression`, `argument_list` | `BS-EXP-003: call forms` | n/a | none | — | EXP-02 |
| BS-EXP-004 | Dot member access: chained, applied to call results and parenthesized expressions, interface-qualified (`i.ifInt.SetInt(5)`, `(1+2).tostr()`). | EVT §Dot operator; CA §Use of wrapper functions on intrinsic types | baseline | documented | planned: `member_expression` | `BS-EXP-004: member access chains` | n/a | none | — | EXP-03 |
| BS-EXP-005 | Index access `[expr]`, chained (`a[1][2]`) and applied to member and call results. | EVT §Array operator | baseline | documented | planned: `index_expression` | `BS-EXP-005: index access and chained indexing` | n/a | none | — | EXP-04 |
| BS-EXP-006 | XML attribute operator `@`: `element@name` (`rsp.photos@perpage`, `m.xml@title`). | CA §Attribute operator | baseline | documented | planned: `attribute_expression` | `BS-EXP-006: attribute operator` | n/a | none | — | EXP-05 |
| BS-EXP-007 | Optional chaining `?.`, `?@`, `?[`, `?(` in expressions, freely chained (`array?[3]?.foo?.bar?()`); each shares its node type with the non-optional form. | EVT §Optional chaining operators; RN §Roku OS 11.0 | 11.0 | documented | planned: `member_expression`, `attribute_expression`, `index_expression`, `call_expression` | `BS-EXP-007: optional chaining chain`<br>`BS-EXP-007: optional call and optional index with arguments` | n/a | none | — | EXP-06, VER-19 |
| BS-EXP-008 | An optional-chaining operator as the outermost accessor of an assignment target (`array?[12] = x`, `a?.b = 1`). | EVT §Optional chaining operators › Support details ("Not supported") | 11.0 | invalid | planned: `_assignment_target` excludes optional accessors | n/a | `BS-EXP-008: optional accessor as an assignment target` | none | — | EXP-06, ASN-01, AMB-16 |
| BS-EXP-009 | A standalone call statement whose outermost call is `?(` (`f?()`). | EVT §Optional chaining operators › Support details ("Not supported") | 11.0 | invalid | planned: call statements require `(` as the outermost call | n/a | `BS-EXP-009: standalone optional call statement` | none | — | EXP-06, STM-17 |
| BS-EXP-010 | Optional chaining inside subexpressions of call statements and assignment targets (`f(array?[12])`, `f(foo?.bar).member = 5`). | EVT §Optional chaining operators › Support details | 11.0 | documented | planned: `call_expression`, `assignment_statement` | `BS-EXP-010: optional chaining inside statement subexpressions` | n/a | none | — | EXP-06 |
| BS-EXP-011 | `^` exponentiation, right associative (`2^3^2` = `2^(3^2)`). | EVT §Operators, §Exponentiation operator | baseline | documented | planned: `binary_expression` (exponent level, right) | `BS-EXP-011: exponentiation is right associative` | n/a | none | — | EXP-07 |
| BS-EXP-012 | Unary `-` and `+` bind looser than postfix operators and `^`, tighter than multiplicative operators (`-5.tostr()` = `-(5.tostr())`, `-2^2` = `-(2^2)`, `-a*b` = `(-a)*b`). | EVT §Operators, §Negation operator; CA §Use of wrapper functions on intrinsic types | baseline | documented | planned: `unary_expression` (unary level) | `BS-EXP-012: unary minus against postfix and exponent`<br>`BS-EXP-012: unary operators against multiplication` | n/a | none | — | EXP-08 |
| BS-EXP-013 | `*`, `/` and `MOD` share one level, left associative. | EVT §Operators, §Multiplicative operators | baseline | documented | planned: `binary_expression` (multiplicative level) | `BS-EXP-013: multiplicative operators are left associative` | n/a | none | — | EXP-09, AMB-13 (`*` lost in the rendered table; prose and examples keep it) |
| BS-EXP-014 | `\` integer division, same level as `*`. | EVT §Multiplicative operators; RN §Roku OS 6.1 | 6.1 | documented | planned: `binary_expression` (multiplicative level) | `BS-EXP-014: integer division` | n/a | none | — | EXP-09, VER-06 |
| BS-EXP-015 | `+` and `-` (also string concatenation), left associative, below multiplicative. | EVT §Operators, §Additive operators | baseline | documented | planned: `binary_expression` (additive level) | `BS-EXP-015: additive operators against multiplicative` | n/a | none | — | EXP-10 |
| BS-EXP-016 | `<<` and `>>` below additive and above comparisons. | EVT §Operators, §Integer bitshift operators; RN §Roku OS 6.1 | 6.1 | documented | planned: `binary_expression` (shift level) | `BS-EXP-016: shifts between additive and comparison` | n/a | none | — | EXP-11, VER-07 |
| BS-EXP-017 | Comparisons `=`, `<>`, `<`, `>`, `<=`, `>=` share one level, left associative (`a < b < c` = `(a < b) < c`). | EVT §Operators, §Comparison operators | baseline | documented | planned: `binary_expression` (comparison level) | `BS-EXP-017: comparison operators and chains` | n/a | none | — | EXP-12, AMB-13 |
| BS-EXP-018 | `NOT` is a prefix operator below comparisons and above `AND` (`not a = b` = `not (a = b)`, `not a and b` = `(not a) and b`). | EVT §Operators, §Logical and bitwise operators | baseline | documented | planned: `unary_expression` (NOT level) | `BS-EXP-018: NOT below comparison and above AND` | n/a | none | — | EXP-13 |
| BS-EXP-019 | `AND` binds tighter than `OR`; both left associative (`a or b and c` = `a or (b and c)`). | EVT §Operators, §Logical and bitwise operators | baseline | documented | planned: `binary_expression` (AND and OR levels) | `BS-EXP-019: AND binds tighter than OR` | n/a | none | — | EXP-14 |
| BS-EXP-020 | Inside an expression `=` is comparison; assignment is a statement, never an expression (`if a=5 then …`, `x = a = b`). | EVT §= operator | baseline | documented | planned: `binary_expression`, `assignment_statement` | `BS-EXP-020: equals inside an expression is comparison` | n/a | none | — | EXP-16 |
| BS-EXP-021 | Call, `.`, `[]`, `@` and their optional forms form one postfix level applied left to right; `@` binds like `.` (`x@y.z` = `(x@y).z`, `a.b@c` = `(a.b)@c`). | EVT §Operators (the table lists postfix operators on separate rows and omits `@`) | unknown | provisional | planned: postfix level | `BS-EXP-021: mixed postfix chain`<br>`BS-EXP-021: attribute operator inside a member chain` | n/a | none | — | EXP-15, AMB-13 |
| BS-EXP-022 | Adjacent operands without an operator outside PRINT (`"a"b"c"`). | CA §Attribute operator (unexplained example) | unknown | unresolved | none | n/a — unresolved | n/a | none | — | EXP-17, AMB-28. The example is excluded from fixtures. |
| BS-EXP-023 | A line break after a binary operator, inside grouping parentheses or inside index brackets. | none | unknown | unresolved | none | n/a — unresolved | n/a | none | — | LEX-05, AMB-07 |
| BS-EXP-024 | Line breaks inside argument lists: after `(`, after a `,`, and before `)`. | L1 shows it for a parameter list only (BS-FUNC-006) | unknown | provisional | planned: `argument_list` | `BS-EXP-024: call arguments across lines` | n/a | none | — | LINE-05, AMB-07 |
| BS-EXP-025 | Calls and indexing apply to identifiers, parenthesized expressions and postfix expressions; member access also applies to numeric, string, array and associative-array literals. A call or index applied directly to a literal (`"a"(1)`, `5[0]`, `[1][0]`) has no contractual behaviour. | L1 examples show only these operand kinds | unknown | provisional | planned: `_postfix_operand` | `BS-EXP-025: postfix operand kinds` | n/a | none | — | EXP-02, EXP-03, LIT-09. Keeps PRINT item boundaries deterministic (BS-STMT-026). |
| BS-EXP-026 | Operator semantics: numeric promotion, concatenation, short-circuit evaluation, runtime errors, `?.` on interface names, the `TYPE?(` compile error. | EVT §Operators subsections; CA | baseline | out-of-scope | none | n/a | n/a | none | — | EXP-14, AMB-35 |

### STMT

| ID | Requirement | Evidence | Since | Status | Grammar | Positive fixtures | Negative / recovery fixtures | Coverage | KL | Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| BS-STMT-001 | Assignment `target = expression`. Targets: identifier (with designator), member access, index access with one or more indexes, including chains whose inner parts are calls (`f(x).y = 1`). | PS §variable = expression; EVT §Dot operator, §Array operator | baseline | documented | planned: `assignment_statement`, `_assignment_target` | `BS-STMT-001: assignment to variables, members and indexes` | `BS-STMT-001: assignment missing its value` (recovery) | none | — | ASN-01 |
| BS-STMT-002 | Compound assignment `+=`, `-=`, `*=`, `/=`, `\=`, `<<=`, `>>=` on the same targets. `^=`, `MOD=` and other spellings are not accepted (no rule). | EVT §Mathematical and bitshift assignment operators (examples); RN §Roku OS 7.1 (list) | 7.1 | documented | planned: `assignment_statement` | `BS-STMT-002: compound assignment operators` | n/a | none | — | ASN-02, VER-12, AMB-14 |
| BS-STMT-003 | `x++` and `x--` statements on a variable. | EVT §Increment and decrement operators; PS §CONTINUE FOR / CONTINUE WHILE; RN §Roku OS 7.1 | 7.1 | documented | planned: `update_statement` | `BS-STMT-003: increment and decrement statements` | n/a | none | — | ASN-03, VER-11 |
| BS-STMT-004 | `++`/`--` on member and index targets (`a.b++`, `a[0]--`). Prefix forms and use inside expressions have no contractual behaviour. | L1 silent | unknown | provisional | planned: `update_statement` over `_assignment_target` | `BS-STMT-004: increment and decrement on member and index targets` | n/a | none | — | ASN-03, AMB-15 |
| BS-STMT-005 | Call statement: a call expression whose outermost call uses `(` and whose chain starts with an identifier (`HandleButton(msg.GetInt())`, `cavemen.push("fred")`). | PS, EVT, CA examples | baseline | documented | planned: `call_expression` in `statement` | `BS-STMT-005: call statements` | n/a | none | — | STM-17 |
| BS-STMT-006 | Other bare expressions as statements (`x`, `a + b`, `a.b`) and call statements whose chain starts with something other than an identifier (`(f)()`, `"x".len()`). | none | unknown | unresolved | none | n/a — unresolved | n/a | none | — | STM-17, AMB-16 |
| BS-STMT-007 | Single-line IF: `IF condition [THEN] statements [ELSE statements]` on one line; THEN optional; each branch holds one or more statements separated by `:` and extends to the end of the line. | PS §IF expression THEN statements [ELSE statements]; SS (example) | baseline | documented | planned: `if_statement` (single-line form), `else_clause` | `BS-STMT-007: single-line IF with THEN`<br>`BS-STMT-007: single-line IF without THEN`<br>`BS-STMT-007: single-line IF with ELSE`<br>`BS-STMT-007: colon-separated statements in a single-line branch` | n/a | none | — | STM-01, AMB-04, AMB-05 |
| BS-STMT-008 | After the condition and optional THEN, a line end, comment or `:` selects the block form; any statement start selects the single-line form. | EVT §Optional chaining operators › Support details (comment case); L1 silent on `:` | unknown | provisional | planned: `if_statement` factoring | `BS-STMT-008: THEN followed by a comment starts a block IF`<br>`BS-STMT-008: THEN followed by a colon starts a block IF` | n/a | none | — | STM-02, AMB-04 |
| BS-STMT-009 | Single-line IF composition: ELSE belongs to the nearest single-line IF; a branch may hold a nested single-line IF; `ELSE IF` in single-line form is an ELSE branch holding a nested IF. Branch statements are assignment, update, call, PRINT, RETURN, EXIT, CONTINUE, GOTO, END, STOP, THROW, DIM and single-line IF. Repeated `:` between branch statements is accepted; a trailing `:` is not. | L1 silent | unknown | provisional | planned: `_inline_statement`, `if_statement` | `BS-STMT-009: nested single-line IF with ELSE`<br>`BS-STMT-009: single-line ELSE IF nests an IF` | n/a | none | — | AMB-05 |
| BS-STMT-010 | Block IF: `IF condition [THEN]`, line end, statements, any number of `ELSEIF`/`ELSE IF condition [THEN]` clauses, optional `ELSE`, closed by `END IF` or `ENDIF`. | PS §Block IF, ELSEIF, THEN, ENDIF | baseline | documented | planned: `if_statement`, `else_if_clause`, `else_clause` | `BS-STMT-010: block IF with ELSE IF and ELSE`<br>`BS-STMT-010: ELSEIF and ENDIF spellings`<br>`BS-STMT-010: block IF without THEN` | `BS-STMT-010: block IF missing END IF` (recovery) | none | — | STM-02, AMB-03 |
| BS-STMT-011 | In a block IF, `ELSE` and `ELSE IF … [THEN]` headers end at a line end, `:` or comment. Code directly after them on the same line has no contractual behaviour. | L1 silent | unknown | provisional | planned: `else_clause`, `else_if_clause` | `BS-STMT-011: ELSE and ELSE IF headers followed by comments and colons` | n/a | none | — | AMB-04, AMB-05 |
| BS-STMT-012 | Counted loop `FOR counter = start TO end [STEP increment]`, body, `END FOR`. | PS §FOR counter = exp TO exp [STEP exp] / END FOR | baseline | documented | planned: `for_statement` | `BS-STMT-012: FOR with and without STEP` | `BS-STMT-012: FOR missing END FOR` (recovery) | none | — | STM-03 |
| BS-STMT-013 | Bare `NEXT` terminates FOR and FOR EACH. | PS §FOR …, §FOR EACH item IN object | baseline | documented | planned: `for_statement`, `for_each_statement` | `BS-STMT-013: NEXT terminates FOR and FOR EACH` | n/a | none | — | STM-03, AMB-06, VER-26 |
| BS-STMT-014 | `NEXT counter` and `NEXT i, j`. | none | unknown | unresolved | none | n/a — unresolved | n/a | none | — | AMB-06 |
| BS-STMT-015 | `FOR EACH item IN expression`, body, `END FOR`. | PS §FOR EACH item IN object | baseline | documented | planned: `for_each_statement` | `BS-STMT-015: FOR EACH over an expression` | n/a | none | — | STM-04 |
| BS-STMT-016 | `WHILE condition`, body, `END WHILE`. | PS §WHILE expression / EXIT WHILE / END WHILE | baseline | documented | planned: `while_statement` | `BS-STMT-016: WHILE loop` | `BS-STMT-016: WHILE missing END WHILE` (recovery) | none | — | STM-05 |
| BS-STMT-017 | `NEXT` does not terminate a WHILE loop. | PS §WHILE ("cannot be terminated with NEXT") | baseline | invalid | planned: `while_statement` accepts only `END WHILE`/`ENDWHILE` | n/a | `BS-STMT-017: WHILE terminated by NEXT` | none | — | STM-05 |
| BS-STMT-018 | `EXIT FOR` and `EXIT WHILE`. | PS §FOR, §FOR EACH, §WHILE; SS | baseline | documented | planned: `exit_statement` | `BS-STMT-018: EXIT FOR and EXIT WHILE` | n/a | none | — | STM-03, STM-05, STM-18 |
| BS-STMT-019 | `CONTINUE FOR` and `CONTINUE WHILE`. | PS §CONTINUE FOR / CONTINUE WHILE; RN §Roku OS 11.5 | 11.5 | documented | planned: `continue_statement` | `BS-STMT-019: CONTINUE FOR and CONTINUE WHILE` | n/a | none | — | STM-06, VER-22 |
| BS-STMT-020 | Compact `ENDWHILE` and `EXITWHILE` (reserved words) are equivalent to `END WHILE` and `EXIT WHILE`. | RW (membership only) | unknown | provisional | planned: `kw('endwhile')`, `kw('exitwhile')` | `BS-STMT-020: ENDWHILE and EXITWHILE` | n/a | none | — | AMB-03 |
| BS-STMT-021 | `ENDFOR`, `EXITFOR`, `FOREACH`, bare `EXIT`, bare `CONTINUE`. | none — absent from RW and examples | unknown | unresolved | none | n/a — unresolved | n/a | none | — | STM-18, AMB-03 |
| BS-STMT-022 | The words of a multi-word keyword (`END IF`, `ELSE IF`, `FOR EACH`, `EXIT FOR`, `END FUNCTION`, …) may be separated by any run of spaces and tabs, never by a line break. | L1 silent | unknown | provisional | planned: separate keyword tokens | `BS-STMT-022: multi-word keywords with extra spacing` | n/a | none | — | AMB-03 |
| BS-STMT-023 | `RETURN [expression]`. | PS §RETURN [expression] | baseline | documented | planned: `return_statement` | `BS-STMT-023: RETURN with and without a value` | n/a | none | — | STM-07 |
| BS-STMT-024 | `PRINT` (or `?`) followed by items separated by `,` or `;`; a trailing `;` or `,` is allowed. | PS §PRINT item list; SS | baseline | documented | planned: `print_statement` | `BS-STMT-024: PRINT separators and trailing semicolon`<br>`BS-STMT-024: question-mark PRINT with separators` | n/a | none | — | STM-08 |
| BS-STMT-025 | PRINT items may be adjacent without a separator (`print "a " 5 "!!"`, `print tab(5)"x";tab(25)"y"`, `print tab(40) pos(0)`). | PS §PRINT item list | baseline | documented | planned: `print_statement` | `BS-STMT-025: adjacent PRINT items`<br>`BS-STMT-025: TAB and POS items` | n/a | none | — | STM-08, AMB-17 |
| BS-STMT-026 | PRINT item boundaries: an item extends as far as the expression grammar allows (`print a -1` is one item `a - 1`, `print a (1)` is a call, `print "a" (1)` is two items). `PRINT` with no items is accepted. | L1 silent | unknown | provisional | planned: `print_statement` precedence | `BS-STMT-026: ambiguous adjacent PRINT items`<br>`BS-STMT-026: PRINT with no items` | n/a | none | — | AMB-17 |
| BS-STMT-027 | `GOTO label`. | PS §GOTO label; SS | baseline | documented | planned: `goto_statement` | `BS-STMT-027: GOTO a label` | n/a | none | — | STM-10 |
| BS-STMT-028 | GOTO with a line number. | PS §GOTO label (prose mentions a line number, no form) | unknown | unresolved | none | n/a — unresolved | n/a | none | — | AMB-31 |
| BS-STMT-029 | `END` terminates execution. | PS §END; SS | baseline | documented | planned: `end_statement` | `BS-STMT-029: END statement` | n/a | none | — | STM-11, AMB-25 |
| BS-STMT-030 | `STOP`. | PS §STOP; SS | baseline | documented | planned: `stop_statement` | `BS-STMT-030: STOP statement` | n/a | none | — | STM-12 |
| BS-STMT-031 | `LIBRARY "path"` at the top of a file (`Library "v30/bslCore.brs"`). | CA §Script libraries; EH §Handling only some errors | baseline | documented | planned: `library_statement` | `BS-STMT-031: LIBRARY at the top of a file` | n/a | none | — | STM-16 |
| BS-STMT-032 | LIBRARY is accepted wherever a statement is accepted; placement rules are not grammar. | L1 silent on placement | unknown | provisional | planned: `library_statement` in `statement` | `BS-STMT-032: LIBRARY after a function declaration` | n/a | none | — | STM-16, AMB-19 |
| BS-STMT-033 | A file is a sequence of statements: declarations, LIBRARY, directives and ordinary statements are all accepted at file level. | CA §Scope (named functions are global); L1 silent on statements outside functions | unknown | provisional | planned: `source_file` | `BS-STMT-033: statements at file level` | n/a | none | — | FUN-06, AMB-27 |
| BS-STMT-034 | `LET` statement. | RW only | unknown | unresolved | none | n/a — unresolved | n/a | none | — | ASN-04, AMB-23 |
| BS-STMT-035 | Every block header (IF, ELSE IF, ELSE, FOR, FOR EACH, WHILE, TRY, CATCH, FUNCTION, SUB) ends at a line end, `:` or comment, so a body may be written on one line with colons. | FUNCTION bodies documented (BS-FUNC-010); L1 silent for the others | unknown | provisional | planned: `block` starts with `_terminator` | `BS-STMT-035: one-line loop and TRY bodies with colons` | n/a | none | — | AMB-08 |
| BS-STMT-036 | A block terminator closes only its own construct: `END IF`/`ENDIF` an IF, `END FOR`/`NEXT` a FOR or FOR EACH, `END WHILE`/`ENDWHILE` a WHILE, `END TRY`/`ENDTRY` a TRY, `END FUNCTION`/`ENDFUNCTION` a function, `END SUB`/`ENDSUB` a sub. | PS (each statement defines its terminator) | baseline | documented | planned: per-construct terminators | `BS-STMT-036: nested blocks close with their own terminators` | `BS-STMT-036: END IF closing a FOR body` (recovery) | none | — | KR-005 (`docs/validation/known-regressions.md`) |
| BS-STMT-037 | EXIT/CONTINUE inside a matching loop, GOTO target existence, label scope and reachability. | PS; CA §Scope | baseline | out-of-scope | none | `BS-STMT-037: EXIT FOR outside a loop is not rejected` (guard) | n/a | none | — | AMB-35 |
| BS-STMT-038 | Runtime meaning of statements: FOR bound evaluation, enumeration order, PRINT zones and number formatting, TAB/POS behaviour, END/STOP effects. | PS | baseline | out-of-scope | none | n/a | n/a | none | — | — |

### FUNC

| ID | Requirement | Evidence | Since | Status | Grammar | Positive fixtures | Negative / recovery fixtures | Coverage | KL | Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| BS-FUNC-001 | Named function: `FUNCTION name(parameters) [AS type]`, body, `END FUNCTION`. | PS §FUNCTION(…) AS type / END FUNCTION; SS | baseline | documented | planned: `function_declaration` | `BS-FUNC-001: function with typed parameters and return type`<br>`BS-FUNC-001: function without parameters` | `BS-FUNC-001: function missing END FUNCTION` (recovery) | none | — | FUN-01 |
| BS-FUNC-002 | Named sub: `SUB name(parameters)`, body, `END SUB`; same node type as a function. | PS §FUNCTION (last paragraph); RW | baseline | documented | planned: `function_declaration` | `BS-FUNC-002: sub declaration` | n/a | none | — | FUN-02 |
| BS-FUNC-003 | Compact `ENDFUNCTION` and `ENDSUB` (reserved words). | RW (membership only) | unknown | provisional | planned: `kw('endfunction')`, `kw('endsub')` | `BS-FUNC-003: ENDFUNCTION and ENDSUB` | n/a | none | — | AMB-03 |
| BS-FUNC-004 | An `AS` return type on SUB. | none | unknown | unresolved | none | n/a — unresolved | n/a | none | — | FUN-02, AMB-26 |
| BS-FUNC-005 | Parameters: zero or more, comma-separated, each `name [= default] [AS type]`; a default may reference earlier parameters (`b=a+5 as Integer`). | PS §FUNCTION(…) | baseline | documented | planned: `parameter_list`, `parameter` | `BS-FUNC-005: parameters with defaults and types` | n/a | none | — | FUN-03 |
| BS-FUNC-006 | A line break after a comma in a parameter list. | CA §Attribute operator (example function declaration) | baseline | documented | planned: `parameter_list` | `BS-FUNC-006: parameter list continued after a comma` | n/a | none | — | LEX-05, LINE-05 |
| BS-FUNC-007 | Line breaks after `(` and before `)` in a parameter list. | L1 silent | unknown | provisional | planned: `parameter_list` | `BS-FUNC-007: parameter list opened and closed on separate lines` | n/a | none | — | AMB-07 |
| BS-FUNC-008 | Once a parameter has a default value, every following parameter needs one. | PS §FUNCTION(…) | baseline | out-of-scope | none | `BS-FUNC-008: default-parameter order is not enforced` (guard) | n/a | none | — | FUN-03, AMB-35 |
| BS-FUNC-009 | Anonymous function `FUNCTION (parameters) [AS type]`, body, `END FUNCTION`, usable wherever an expression is. | PS §Anonymous functions, §FUNCTION(…) heading | baseline | documented | planned: `anonymous_function` | `BS-FUNC-009: anonymous function assigned to a variable`<br>`BS-FUNC-009: anonymous function as an associative-array value` | n/a | none | — | FUN-05 |
| BS-FUNC-010 | One-line bodies with `:` (`FUNCTION explode() : THROW "Kaboom!" : END FUNCTION`, `function():return m.xml@title:end function`). | EVT §Optional chaining operators › Notes; CA §Attribute operator, §Creating and using intrinsic objects | baseline | documented | planned: `block` | `BS-FUNC-010: one-line function bodies` | n/a | none | — | FUN-05, LEX-04 |
| BS-FUNC-011 | Anonymous `SUB (parameters)`, body, `END SUB`, same node type as an anonymous function. | PS §FUNCTION (Sub shortcut); anonymous form not shown | unknown | provisional | planned: `anonymous_function` | `BS-FUNC-011: anonymous sub` | n/a | none | — | AMB-22 |
| BS-FUNC-012 | Named declarations nested inside a body. | CA §Scope (named functions are global) | unknown | unresolved | none added — the shared statement list accepts them | n/a — unresolved | n/a | none | — | FUN-06, AMB-27 |
| BS-FUNC-013 | `m` is an ordinary identifier. | PS §FUNCTION; CA §"m" the BrightScript "this pointer" | baseline | documented | planned: `identifier` | `BS-FUNC-013: m used as an identifier` | n/a | none | — | FUN-08 |
| BS-FUNC-014 | Function semantics: scope, `m` binding, no closures, Void returns, unused-variable `_` tagging (11.0), stack depth (16.0), function-count limit (5.0). | PS; EVT §Types; CA §Scope; RN | baseline | out-of-scope | none | n/a | n/a | none | — | FUN-06, VER-02, VER-05, VER-21, VER-25 |

### ARRAY

| ID | Requirement | Evidence | Since | Status | Grammar | Positive fixtures | Negative / recovery fixtures | Coverage | KL | Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| BS-ARRAY-001 | Array literal: `[]`, or comma-separated elements (literals or expressions, nesting allowed) on one line. | EVT §Array literals | baseline | documented | planned: `array_literal` | `BS-ARRAY-001: empty, flat and nested array literals` | `BS-ARRAY-001: array literal missing its closing bracket` (recovery) | none | — | LIT-11 |
| BS-ARRAY-002 | Multi-line array literal: line breaks after `[`, between elements (with or without commas) and before `]`. | EVT §Array literals | baseline | documented | planned: `array_literal` | `BS-ARRAY-002: multi-line array without commas`<br>`BS-ARRAY-002: multi-line array with commas` | n/a | none | — | LIT-11, LINE-05 |
| BS-ARRAY-003 | A trailing comma before `]`, on the same line or before the closing line break, is accepted; empty elements (`[1,,2]`) are not. | L1 silent | unknown | provisional | planned: `array_literal` | `BS-ARRAY-003: trailing comma in array literals` | n/a | none | — | ARR-04, AMB-07 |
| BS-ARRAY-004 | `DIM name[d1, …, dk]` with expression dimensions. | PS §DIM (examples); SS; EVT §Array operator | baseline | documented | planned: `dim_statement` | `BS-ARRAY-004: DIM with one and several dimensions` | n/a | none | — | STM-09, ARR-01 |
| BS-ARRAY-005 | `DIM name(d1, …, dk)`, the parenthesis form of the PS heading, gives the same node. | PS §DIM (heading) | unknown | provisional | planned: `dim_statement` | `BS-ARRAY-005: DIM with parentheses` | n/a | none | — | AMB-18 |
| BS-ARRAY-006 | Several declarators in one DIM (`dim a[1], b[2]`). | none | unknown | unresolved | none | n/a — unresolved | n/a | none | — | AMB-18 |
| BS-ARRAY-007 | A comma-separated index list `a[1,2,3]` is one index access with three indexes; it is not rewritten to `a[1][2][3]` (their equivalence is semantic). | EVT §Array operator; PS §DIM | baseline | documented | planned: `index_expression` | `BS-ARRAY-007: multiple indexes in one access` | n/a | none | — | EXP-04, ARR-02 |
| BS-ARRAY-008 | Array semantics: sizing, growth, `roArray` creation, enumeration. | PS §DIM; EVT §Array operator | baseline | out-of-scope | none | n/a | n/a | none | — | ARR-01 |

### AA

| ID | Requirement | Evidence | Since | Status | Grammar | Positive fixtures | Negative / recovery fixtures | Coverage | KL | Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| BS-AA-001 | Associative-array literal: `{}` or `{ }`, or comma-separated `key: value` entries on one line; keys are identifiers; values are any expression including anonymous functions. | EVT §Associative array literals; PS §Anonymous functions | baseline | documented | planned: `associative_array_literal`, `associative_array_entry` | `BS-AA-001: empty and one-line associative arrays`<br>`BS-AA-001: anonymous functions as values` | `BS-AA-001: associative array missing its closing brace` (recovery) | none | — | LIT-12 |
| BS-AA-002 | String-literal keys (`{ "Jane Doe": 1001 }`). | EVT §Associative array literals; RN §Roku OS 7.0 | 7.0 | documented | planned: `associative_array_entry` | `BS-AA-002: string keys` | n/a | none | — | LIT-12, VER-09 |
| BS-AA-003 | Multi-line associative array: line breaks after `{`, between entries (with or without commas) and before `}`. | EVT §Associative array literals; PS §FUNCTION (`obj = { add: add … }`) | baseline | documented | planned: `associative_array_literal` | `BS-AA-003: multi-line associative array without commas`<br>`BS-AA-003: multi-line associative array with commas` | n/a | none | — | LIT-12, LINE-05 |
| BS-AA-004 | A trailing comma is accepted; empty entries (`{a:1,,b:2}`) are not. | L1 silent | unknown | provisional | planned: `associative_array_literal` | `BS-AA-004: trailing comma in associative arrays` | n/a | none | — | ARR-04, AMB-07 |
| BS-AA-005 | Duplicate keys, key case folding (identifier keys lower-cased; quoted keys case-preserving since Roku OS 8) and lookup semantics. | EVT §Dot operator; RN §Roku OS 8 | baseline | out-of-scope | none | `BS-AA-005: duplicate keys are not rejected` (guard) | n/a | none | — | ARR-03, VER-15 |

### ERR

| ID | Requirement | Evidence | Since | Status | Grammar | Positive fixtures | Negative / recovery fixtures | Coverage | KL | Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| BS-ERR-001 | `TRY`, body, `CATCH variable`, body, `END TRY` or `ENDTRY`; bodies may be empty. | PS §TRY / CATCH variable / END TRY; RN §Roku OS 9.4 | 9.4 | documented | planned: `try_statement`, `catch_clause` | `BS-ERR-001: TRY with CATCH`<br>`BS-ERR-001: empty TRY and CATCH bodies with ENDTRY` | `BS-ERR-001: TRY missing END TRY` (recovery) | none | — | ERR-01, ERR-04, VER-18 |
| BS-ERR-002 | TRY statements nest inside TRY and CATCH bodies. | PS §Nested TRY/CATCH statements | 9.4 | documented | planned: `try_statement` | `BS-ERR-002: nested TRY in TRY and CATCH bodies` | n/a | none | — | ERR-01 |
| BS-ERR-003 | A CATCH clause without a simple variable: no variable, an index, a member, a literal or an expression. | PS §TRY / CATCH variable / END TRY (listed as not legal) | 9.4 | invalid | planned: `catch_clause` | n/a | `BS-ERR-003: CATCH without a variable`<br>`BS-ERR-003: CATCH with an index`<br>`BS-ERR-003: CATCH with a member`<br>`BS-ERR-003: CATCH with a literal`<br>`BS-ERR-003: CATCH with an expression` | none | — | ERR-01 |
| BS-ERR-004 | `THROW expression` (string, associative-array literal, variable). | PS §THROW expression; EH §Throwing exceptions | 9.4 | documented | planned: `throw_statement` | `BS-ERR-004: THROW forms` | n/a | none | — | ERR-02 |
| BS-ERR-005 | `TRY` and `THROW` are keywords at statement start, `CATCH` at statement start inside a TRY body; elsewhere the three words are identifiers. | PS §TRY / CATCH ("not keywords … reserved identifiers"), §THROW ("is a keyword") | 9.4 | provisional | planned: contextual `kw('try')`, `kw('catch')`, `kw('throw')` | `BS-ERR-005: try, catch and throw as identifiers` | n/a | none | — | ERR-03, AMB-02. Known incompatibility: legacy code using them as statement-initial names. |
| BS-ERR-006 | TRY without CATCH. | PS schematic always shows CATCH | unknown | unresolved | none — the grammar requires CATCH | n/a — unresolved | n/a | none | — | AMB-33 |
| BS-ERR-007 | Exception object fields, re-throw, `ERR_USER`/`ERR_BAD_THROW`, uncatchable STOP, the minimum-OS declaration, and the rule that a GOTO label may not appear between TRY and CATCH. | PS §TRY / CATCH, §THROW; EH | 9.4 | out-of-scope | none | `BS-ERR-007: label inside a TRY body is not rejected` (guard) | n/a | none | — | ERR-05, ERR-06, AMB-35 |

### COND

| ID | Requirement | Evidence | Since | Status | Grammar | Positive fixtures | Negative / recovery fixtures | Coverage | KL | Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| BS-COND-001 | `#const name = value` where value is `true`, `false` or a constant name. | CC (introduction) | unknown | documented | planned: `const_directive` | `BS-COND-001: #const forms` | n/a | none | — | CC-01, CC-04, VER-27 |
| BS-COND-002 | `#if condition` … `#end if`, the condition a constant name, `true` or `false`. Conditions are never evaluated; every branch is parsed as BrightScript (baseline, ADR-0004). | CC §Uses, §Undefined constants | unknown | documented | planned: `if_directive` | `BS-COND-002: #if around statements`<br>`BS-COND-002: #if true and #if name bodies are code` | `BS-COND-002: #if missing #end if` (recovery) | none | — | CC-02, VER-27 |
| BS-COND-003 | `#else if condition` and `#else` branches. | CC §Uses | unknown | documented | planned: `else_if_directive`, `else_directive` | `BS-COND-003: #else if and #else branches` | n/a | none | — | CC-02 |
| BS-COND-004 | `#error message`; the message is free text to the end of the line. | CC §Uses | unknown | documented | planned: `error_directive`, `error_message` | `BS-COND-004: #error with free text` | n/a | none | — | CC-03 |
| BS-COND-005 | Directive words and constant names in any letter case. | CC §Criteria; SS | unknown | documented | planned: directive tokens | `BS-COND-005: directives in mixed case` | n/a | none | — | CC-04, LEX-01 |
| BS-COND-006 | Directives at file level (wrapping declarations) and inside bodies (wrapping statements); conditional blocks nest. | CC §Uses, §Block comments | unknown | documented | planned: `if_directive` in `statement` | `BS-COND-006: #if around function declarations`<br>`BS-COND-006: nested #if blocks` | n/a | none | — | CC-07, CC-08 |
| BS-COND-007 | Block-comment idiom: a literal-`false` branch whose content is not BrightScript. Represented per the ADR-0004 spike: PASS → `inactive_text`; FAIL → known limitation KL-001. | CC §Block comments; ADR-0004 | unknown | documented | planned: `if_directive` + `inactive_text` (spike-gated) | `BS-COND-007: block comment with prose`<br>`BS-COND-007: commented-out function` | spike fixtures (`docs/specs/grammar-design.md`) | none | KL-001 (only if the spike fails) | CC-07, AMB-20 |
| BS-COND-008 | A directive occupies its own line: it may be indented; `#const`, `#if`, `#else if`, `#else` and `#end if` may be followed by a comment; `#` is immediately followed by the directive word; the two words of `#else if`/`#end if` may be separated by spaces or tabs. | L1 silent | unknown | provisional | planned: directive tokens | `BS-COND-008: indented directives with comments` | n/a | none | — | CC-08, AMB-21 |
| BS-COND-009 | Compact `#elseif`/`#endif`, whitespace between `#` and the word, operators or parentheses in conditions (`#if not DEBUG`), expressions in `#const`. | none; `#if not` was observed only in a Level 4 test description | unknown | unresolved | none | n/a — unresolved | n/a | none | — | CC-02, AMB-21; candidate "`#if not NAME`" |
| BS-COND-010 | Directives inside expressions or literals, and statements split across branch boundaries. | ADR-0004 consequences | unknown | unresolved | none | n/a — unresolved | n/a | none | — | AMB-20 |
| BS-COND-011 | Condition evaluation, manifest `bs_const`, undefined constants evaluating to `false` (16.0; earlier a compile error), redefinition, `#error` failing compilation. | CC §Criteria, §Undefined constants, §Manifest constant; RN §Roku OS 16.0 | 16.0 | out-of-scope | none | n/a | n/a | none | — | CC-05, CC-06, VER-24 |

## Registry summary

| Area | Rows | documented | provisional | tolerated | unresolved | invalid | out-of-scope |
|---|---|---|---|---|---|---|---|
| LEX | 34 | 18 | 9 | 0 | 4 | 1 | 2 |
| LIT | 20 | 15 | 3 | 0 | 2 | 0 | 0 |
| TYPE | 3 | 1 | 0 | 0 | 1 | 0 | 1 |
| EXP | 26 | 18 | 3 | 0 | 2 | 2 | 1 |
| STMT | 38 | 20 | 10 | 0 | 5 | 1 | 2 |
| FUNC | 14 | 7 | 3 | 0 | 2 | 0 | 2 |
| ARRAY | 8 | 4 | 2 | 0 | 1 | 0 | 1 |
| AA | 5 | 3 | 1 | 0 | 0 | 0 | 1 |
| ERR | 7 | 3 | 1 | 0 | 1 | 1 | 1 |
| COND | 11 | 7 | 1 | 0 | 2 | 0 | 1 |
| **Total** | **166** | **96** | **33** | **0** | **20** | **5** | **12** |

No requirement is `tolerated`: no undocumented variant has Level 2 evidence or
Level 4 evidence of acceptance as plain BrightScript that was needed.

## Known incompatibilities

The grammar follows the current documentation (ADR-0003). Older meanings of
the same text:

| Text | Older meaning | Current parse | Requirement |
|---|---|---|---|
| `IF x?("Hello")` ending its line | single-line IF printing `Hello` | block IF with an optional call | BS-LEX-032 |
| statement-initial `try`, `catch`, `throw` used as names | identifiers (before Roku OS 9.4) | statement keywords; ERROR for assignment or call forms | BS-ERR-005 |
| statement-initial `continue` used as a name | identifier (before Roku OS 11.5) | statement keyword | BS-LEX-025 |

## Reconciliation

### Official sources → requirements

| Page | Sections inspected | Requirements derived | Sections excluded (reason) |
|---|---|---|---|
| LR | whole page | none | overview and authority statement only |
| SS | statement list; case note; colon note and examples | BS-LEX-001, 010; BS-STMT-007, 024 | — |
| PS | DIM; variable = expression; END; STOP; GOTO label; RETURN; FOR; FOR EACH; WHILE; CONTINUE; TRY / CATCH; Nested TRY/CATCH; THROW; REM; IF (single line); Block IF; PRINT item list (TAB, POS); FUNCTION; Anonymous functions | BS-LEX-005, 013, 027; BS-STMT-001, 003, 005, 007, 010, 012, 013, 015–019, 023–025, 027, 029, 030, 036; BS-FUNC-001, 002, 005, 009, 013; BS-ARRAY-004, 005, 007; BS-ERR-001–005; BS-TYPE-001 | exception-object and backtrace tables, Maximum stack depth, `m` binding paragraphs, print zones and number formatting (runtime; BS-ERR-007, BS-FUNC-014, BS-STMT-038) |
| EVT | Identifiers; Types; Comments › In BrightScript; Literals (string, numeric, source, function, array, associative array); Type declaration characters; Operators table; Function call, Dot, Array, Optional chaining (Notes, Support details), Exponentiation, Negation, Multiplicative, Additive, Increment and decrement, Mathematical and bitshift assignment, Integer bitshift, Comparison, Logical and bitwise, `=` operator | BS-LEX-001, 012, 015–018, 021, 026, 029–032; BS-LIT-001–012, 014–017, 019, 020; BS-EXP-001–021; BS-STMT-001–004; BS-ARRAY-001, 002, 007; BS-AA-001–003 | Comments › In XML (XML files); Dynamic vs. object types, Type conversion, Effects of type conversions (runtime; BS-TYPE-003); lookup case rules (BS-AA-005); short-circuit evaluation and operator results (BS-EXP-026) |
| RW | reserved-word list | BS-LEX-021–023; BS-STMT-020, 034; BS-FUNC-003 | — |
| CC | introduction; Criteria; Undefined constants; Defining a constant; Manifest constant; Uses; Block comments | BS-COND-001–009 | manifest syntax and evaluation rules (BS-COND-011) |
| EH | Catching and handling; Throwing exceptions; Invalid throws; Re-throwing; Handling only some errors; Miscellaneous examples | BS-ERR-001, 004; BS-LEX-024 (`function` as a key); BS-LIT-008 (`1e1000000`); BS-STMT-031 (LIBRARY) | exception object, error number, backtrace, custom fields (runtime; BS-ERR-007); console and crash-dump transcripts (not source) |
| RN | all 44 release sections | `since` values of BS-LEX-018, 029, 030; BS-LIT-011, 016; BS-TYPE-001; BS-EXP-007–010, 014, 016; BS-STMT-002, 003, 019; BS-AA-002; BS-ERR-001–005; BS-COND-011 | component, SceneGraph, media, DRM, tooling and platform entries (not language) |
| CA | Use of wrapper functions on intrinsic types; Dot operator; Attribute operator; Scope; Creating and using intrinsic objects; Script libraries | BS-LIT-014; BS-EXP-004, 006, 012, 021, 022; BS-LEX-004, 027; BS-FUNC-006, 009, 010; BS-STMT-031, 033 | component model, statements working with interfaces, garbage collection, events, threading, XML namespaces, bslCore function list (runtime or API) |
| RF | all function sections | BS-LEX-022; BS-LIT-019 | function behaviour, deprecations (API) |

### Research inventory → requirements

The research inventory (`_ref/normative/roku-docs/notes/syntax-inventory.md`,
102 items) was reconciled item by item. Disposition meanings: *promoted* — the
item's statement became its own requirement(s); *combined* — folded into
requirements derived mainly from other items; *duplicate* — repeats another
item; *provisional* / *unresolved* / *out-of-scope* — the item's only outcome
is a requirement with that status.

| Item | Disposition | Requirements |
|---|---|---|
| LEX-01 | promoted | BS-LEX-001 |
| LEX-02 | promoted | BS-LEX-002, 003, 004 |
| LEX-03 | promoted | BS-LEX-005, 006, 007 |
| LEX-04 | promoted | BS-LEX-010, 011 |
| LEX-05 | combined | BS-LEX-005, BS-EXP-023, 024, BS-FUNC-006, BS-ARRAY-002, BS-AA-003 |
| LEX-06 | promoted | BS-LEX-012, 013 |
| LEX-07 | promoted | BS-LEX-015, 016, 026 |
| LEX-08 | promoted | BS-LEX-017, 018, 019, 020 |
| LEX-09 | promoted | BS-LEX-021, 022, 023 |
| LEX-10 | promoted | BS-LEX-025 |
| LEX-11 | promoted | BS-LEX-027, 028 |
| LEX-12 | combined | BS-LEX-029, BS-EXP-006, 011–019, BS-STMT-002 |
| LEX-13 | promoted | BS-LEX-031, 032 |
| LEX-14 | promoted | BS-LIT-019 |
| LIT-01 | promoted | BS-LIT-001 |
| LIT-02 | promoted | BS-LIT-002 |
| LIT-03 | promoted | BS-LIT-003, 004 |
| LIT-04 | promoted | BS-LIT-005, 006 |
| LIT-05 | promoted | BS-LIT-007, 008 |
| LIT-06 | promoted | BS-LIT-009, 010 |
| LIT-07 | promoted | BS-LIT-011 |
| LIT-08 | promoted | BS-LIT-012 |
| LIT-09 | promoted | BS-LIT-014, BS-EXP-025 |
| LIT-10 | promoted | BS-LIT-015, 016, 017, 018 |
| LIT-11 | promoted | BS-ARRAY-001, 002 |
| LIT-12 | promoted | BS-AA-001–004 |
| LIT-13 | promoted | BS-LIT-020 |
| TYP-01 | promoted | BS-TYPE-001 |
| TYP-02 | unresolved | BS-TYPE-002 |
| TYP-03 | duplicate | of LEX-08 and LIT-08 |
| TYP-04 | out-of-scope | BS-TYPE-003 |
| EXP-01 | promoted | BS-EXP-001, 002 |
| EXP-02 | promoted | BS-EXP-003 |
| EXP-03 | promoted | BS-EXP-004 |
| EXP-04 | promoted | BS-EXP-005, BS-ARRAY-007 |
| EXP-05 | promoted | BS-EXP-006 |
| EXP-06 | promoted | BS-EXP-007–010 |
| EXP-07 | promoted | BS-EXP-011 |
| EXP-08 | promoted | BS-EXP-012 |
| EXP-09 | promoted | BS-EXP-013, 014 |
| EXP-10 | promoted | BS-EXP-015 |
| EXP-11 | promoted | BS-EXP-016 |
| EXP-12 | promoted | BS-EXP-017 |
| EXP-13 | promoted | BS-EXP-018 |
| EXP-14 | promoted | BS-EXP-019, 026 |
| EXP-15 | promoted | BS-EXP-021 |
| EXP-16 | promoted | BS-EXP-020 |
| EXP-17 | unresolved | BS-EXP-022 |
| ASN-01 | promoted | BS-STMT-001, BS-EXP-008 |
| ASN-02 | promoted | BS-STMT-002 |
| ASN-03 | promoted | BS-STMT-003, 004 |
| ASN-04 | unresolved | BS-STMT-034 |
| STM-01 | promoted | BS-STMT-007, 008, 009 |
| STM-02 | promoted | BS-STMT-010, 011 |
| STM-03 | promoted | BS-STMT-012, 013 |
| STM-04 | promoted | BS-STMT-015 |
| STM-05 | promoted | BS-STMT-016, 017 |
| STM-06 | promoted | BS-STMT-019 |
| STM-07 | promoted | BS-STMT-023 |
| STM-08 | promoted | BS-STMT-024, 025, 026 |
| STM-09 | promoted | BS-ARRAY-004, 005 |
| STM-10 | promoted | BS-STMT-027 |
| STM-11 | promoted | BS-STMT-029 |
| STM-12 | promoted | BS-STMT-030 |
| STM-13 | duplicate | of LEX-06 |
| STM-14 | duplicate | of ERR-01 |
| STM-15 | duplicate | of ERR-02 |
| STM-16 | promoted | BS-STMT-031, 032 |
| STM-17 | promoted | BS-STMT-005, 006 |
| STM-18 | promoted | BS-STMT-018, 021 |
| FUN-01 | promoted | BS-FUNC-001 |
| FUN-02 | promoted | BS-FUNC-002, 004 |
| FUN-03 | promoted | BS-FUNC-005, 008 |
| FUN-04 | combined | BS-LEX-019, 020 |
| FUN-05 | promoted | BS-FUNC-009, 010, 011 |
| FUN-06 | combined | BS-STMT-033, BS-FUNC-012 |
| FUN-07 | combined | BS-LEX-022 |
| FUN-08 | promoted | BS-FUNC-013 |
| ARR-01 | duplicate | of STM-09, LIT-11, LIT-12 |
| ARR-02 | duplicate | of EXP-03, EXP-04, EXP-06 |
| ARR-03 | out-of-scope | BS-AA-005 (key syntax is LIT-12) |
| ARR-04 | provisional | BS-ARRAY-003, BS-AA-004 |
| ERR-01 | promoted | BS-ERR-001, 003, 006 |
| ERR-02 | promoted | BS-ERR-004 |
| ERR-03 | provisional | BS-ERR-005 |
| ERR-04 | combined | `since` of BS-ERR-001–005 |
| ERR-05 | out-of-scope | BS-ERR-007 |
| ERR-06 | out-of-scope | BS-ERR-007 |
| CC-01 | promoted | BS-COND-001 |
| CC-02 | promoted | BS-COND-002, 003, 009 |
| CC-03 | promoted | BS-COND-004 |
| CC-04 | promoted | BS-COND-005 |
| CC-05 | out-of-scope | BS-COND-011 |
| CC-06 | out-of-scope | BS-COND-011 |
| CC-07 | promoted | BS-COND-007 |
| CC-08 | promoted | BS-COND-006, 008 |
| LINE-01 | combined | BS-LEX-005, 006 |
| LINE-02 | duplicate | of LEX-04 |
| LINE-03 | promoted | BS-LEX-009 |
| LINE-04 | provisional | BS-LEX-008 |
| LINE-05 | combined | BS-ARRAY-002, BS-AA-003, BS-FUNC-006, BS-EXP-024 |
| LINE-06 | provisional | BS-LEX-033, 034 |

| Disposition | Items |
|---|---|
| promoted | 74 |
| combined | 8 |
| duplicate | 7 |
| out-of-scope | 6 |
| provisional | 4 |
| unresolved | 3 |
| tolerated | 0 |
| rejected as an erroneous research interpretation | 0 |
| **Total** | **102** |

### Ambiguities → dispositions

Every entry of `_ref/normative/roku-docs/notes/ambiguities.md` and the two
candidates from Session 01 has one disposition. "L2 may revise" means a Level 2
record could change the chosen behaviour; the compatibility consequence is a
MINOR change before 1.0 when a public shape changes (tree-schema versioning).

| Entry | Requirements | Current evidence | Grammar impact | Disposition | Implementation behaviour | L2 may revise |
|---|---|---|---|---|---|---|
| AMB-01 | BS-LEX-021–024 | RW list; built-ins called in RF; `function` used as a key in EH | keyword recognition | PROVISIONAL-GRAMMAR-CHOICE | contextual keyword extraction; no `reserved` word sets; keywords allowed as member names and keys | yes |
| AMB-02 | BS-LEX-025, BS-ERR-005 | PS keyword notes; RW omissions | keyword recognition | PROVISIONAL-GRAMMAR-CHOICE | non-reserved syntax words are contextual | yes |
| AMB-03 | BS-STMT-010, 020, 021, 022; BS-FUNC-003; BS-ERR-001 | RW compact words; PS `ENDIF`, `ELSEIF`, `ENDTRY` | terminator tokens | PROVISIONAL-GRAMMAR-CHOICE | documented and reserved compact words accepted; `ENDFOR`/`EXITFOR`/`FOREACH` not; multi-word forms are separate tokens | yes |
| AMB-04 | BS-STMT-007, 008, 011 | PS optional THEN; EVT comment case | IF form selection | PROVISIONAL-GRAMMAR-CHOICE | token after condition decides the form | yes |
| AMB-05 | BS-STMT-009 | SS colon example | single-line IF shape | PROVISIONAL-GRAMMAR-CHOICE | nearest-IF ELSE; defined inline statement set | yes |
| AMB-06 | BS-STMT-013, 014 | PS bare NEXT | terminator | RESOLVED-DOCUMENTED | bare NEXT accepted; `NEXT var` has no rule (unresolved) | yes (`NEXT var` only) |
| AMB-07 | BS-LEX-005–008, BS-EXP-023, 024, BS-FUNC-006, 007, BS-ARRAY-002, 003, BS-AA-003, 004 | multi-line literals; one parameter-list example | line model | PROVISIONAL-GRAMMAR-CHOICE | newlines are tokens; allowed only where listed | yes |
| AMB-08 | BS-LEX-010, 011, 027, 028; BS-STMT-035 | label definition; colon separator | label and separator shape | PROVISIONAL-GRAMMAR-CHOICE | labels end their line; runs of separators allowed | yes |
| AMB-09 | BS-LEX-015–020 | identifier rules; designator table | identifier token | PROVISIONAL-GRAMMAR-CHOICE | designator is part of the identifier token everywhere | yes |
| AMB-10 | BS-LIT-004–014 | numeric examples | number token | PROVISIONAL-GRAMMAR-CHOICE | planned `number` token shape | yes |
| AMB-11 | BS-LIT-015–018, BS-LEX-033, 034 | only `""` documented | string token, encoding | PROVISIONAL-GRAMMAR-CHOICE | no escapes other than `""`; UTF-8 | yes |
| AMB-12 | BS-LEX-013, 014 | REM prose | comment token | PROVISIONAL-GRAMMAR-CHOICE | whole-word REM followed by space, tab or line end | yes |
| AMB-13 | BS-EXP-011–021 | precedence table and prose | precedence | PROVISIONAL-GRAMMAR-CHOICE | official order; postfix level includes `@` | yes (`@`, postfix only) |
| AMB-14 | BS-STMT-002 | RN 7.1 list, EVT examples | compound operators | RESOLVED-DOCUMENTED | exactly seven operators | no |
| AMB-15 | BS-STMT-003, 004 | postfix statement examples | update statement | PROVISIONAL-GRAMMAR-CHOICE | postfix statement on assignment targets | yes |
| AMB-16 | BS-LEX-029–032, BS-EXP-007–010 | EVT notes and support details | `?` tokenization | RESOLVED-DOCUMENTED | indivisible tokens + context-aware lexing | yes (edge spellings) |
| AMB-17 | BS-STMT-024–026 | PRINT prose and examples | PRINT list | PROVISIONAL-GRAMMAR-CHOICE | maximal-munch items, empty PRINT | yes |
| AMB-18 | BS-ARRAY-004–006 | heading vs examples | DIM | PROVISIONAL-GRAMMAR-CHOICE | brackets and parentheses; one declarator | yes |
| AMB-19 | BS-STMT-031, 032 | one top-of-file example | top-level shape | PROVISIONAL-GRAMMAR-CHOICE | LIBRARY is an ordinary statement | yes |
| AMB-20 | BS-COND-007 | block-comment idiom | CC body shape | PROVISIONAL-GRAMMAR-CHOICE (spike-gated) | ADR-0004 spike decides; FAIL ⇒ KNOWN-LIMITATION KL-001 | no (design decision) |
| AMB-21 | BS-COND-001–005, 008, 009 | documented spellings only | directive tokens | PROVISIONAL-GRAMMAR-CHOICE | documented spellings; conditions are names or booleans | yes |
| AMB-22 | BS-FUNC-011 | Sub shortcut prose | anonymous sub | PROVISIONAL-GRAMMAR-CHOICE | accepted, same node as anonymous function | yes |
| AMB-23 | BS-STMT-034 | RW only | none | FUTURE-L2 | no rule | yes |
| AMB-24 | BS-LEX-022, 023 | RW only | none | OUT-OF-SCOPE | `ObjFun` is an ordinary identifier | yes (reservation only) |
| AMB-25 | BS-STMT-029 | PS END | END vs END X | RESOLVED-DOCUMENTED | one-token lookahead after `end` | no |
| AMB-26 | BS-TYPE-001, 002, BS-FUNC-004 | FUNCTION type list | type names | FUTURE-L2 | documented names only | yes |
| AMB-27 | BS-STMT-033, BS-FUNC-012 | snippets only | root contents | PROVISIONAL-GRAMMAR-CHOICE | file = statement list | yes |
| AMB-28 | BS-EXP-022 | one unexplained example | none | FUTURE-L2 | no rule | yes |
| AMB-29 | — | official blocks mix source and output | fixture derivation only | OUT-OF-SCOPE | examples reviewed before use (grammar-contract §3.7) | no |
| AMB-30 | all `since` fields | versioned syntax | none | OUT-OF-SCOPE | settled by ADR-0003 (superset, no modes) | no |
| AMB-31 | BS-STMT-028 | prose mention only | none | FUTURE-L2 | no rule | yes |
| AMB-32 | BS-LEX-003, 004, 026 | adjacency examples | whitespace | PROVISIONAL-GRAMMAR-CHOICE | space and tab only; word boundaries | yes |
| AMB-33 | BS-ERR-001, 003, 006, BS-STMT-035 | CATCH rules | CATCH shape | PROVISIONAL-GRAMMAR-CHOICE | variable required; header may end with `:` | yes |
| AMB-34 | — | BrighterScript-only features | must not affect grammar | OUT-OF-SCOPE | never accepted | no |
| AMB-35 | BS-TYPE-003, BS-EXP-026, BS-STMT-037, BS-FUNC-008, 014, BS-AA-005, BS-ERR-007, BS-COND-011 | semantic rules | none | OUT-OF-SCOPE | not grammar; guard fixtures where listed | no |
| `#if not NAME` | BS-COND-009 | Level 4 test description only; L1 shows names and booleans | none | FUTURE-L2 (joined to AMB-21) | no rule; insufficient evidence to promote | yes |
| `mod` as a variable | BS-LEX-025 | Level 4 claim; L1 reserved list omits `Mod` | keyword recognition | PROVISIONAL-GRAMMAR-CHOICE (joined to AMB-02) | contextual: identifier where the operator is not expected; adopted from the L1 list, not the L4 claim | yes |

| Disposition | AMB entries | Session 01 candidates |
|---|---|---|
| RESOLVED-DOCUMENTED | 4 | 0 |
| PROVISIONAL-GRAMMAR-CHOICE | 22 | 1 |
| TOLERATED | 0 | 0 |
| OUT-OF-SCOPE | 5 | 0 |
| KNOWN-LIMITATION | 0 (KL-001 contingent under AMB-20) | 0 |
| FUTURE-L2 | 4 | 1 |
| **Total** | **35** | **2** |

### Versioned changes → `since`

From `_ref/normative/roku-docs/notes/versioned-language-changes.md`; every
version below was re-checked against the release-notes snapshot.

| Research label | Roku OS | Change | Kind | Requirements / disposition |
|---|---|---|---|---|
| VER-01 | 3.0 | typed parameters and returns | syntax | BS-TYPE-001 `since` 3.0 |
| VER-02 | 3.0 | stricter runtime checks | runtime | BS-FUNC-014 |
| VER-03 | 3.0 | `GetGlobalAA()` | API | none; name covered by BS-LEX-022 |
| VER-04 | 3.0 | `Type(x, version)` | API | none |
| VER-05 | 5.0 | function-count limit | resource | BS-FUNC-014 |
| VER-06 | 6.1 | `\` | syntax | BS-EXP-014 |
| VER-07 | 6.1 | `<<`, `>>` | syntax | BS-EXP-016 |
| VER-08 | 6.2 | `""` in strings | syntax | BS-LIT-016 |
| VER-09 | 7.0 | string AA keys | syntax | BS-AA-002 |
| VER-10 | 7.0 | LongInteger, `&` designator and suffix | syntax | BS-LEX-018, BS-LIT-011 |
| VER-11 | 7.1 | `++`, `--` | syntax | BS-STMT-003 |
| VER-12 | 7.1 | compound assignment | syntax | BS-STMT-002 |
| VER-13 | 7.1 | PRINT of enumerables | runtime | BS-STMT-038 |
| VER-14 | 7.5 | debugger thread behaviour | runtime | none (tooling) |
| VER-15 | 8 | case-preserving quoted keys | runtime | BS-AA-005 |
| VER-16 | 9 | `eval()` restricted | compile-time semantic | none (API) |
| VER-17 | 9.3 | `eval()` compile error by default | compile-time semantic | none (API) |
| VER-18 | 9.4 | TRY/CATCH/THROW | syntax | BS-ERR-001–005 |
| VER-19 | 11.0 | optional chaining | syntax | BS-LEX-029, 030, BS-EXP-007–010 |
| VER-20 | not stated | `IF x?(` meaning change | syntax | BS-LEX-032 `since` unknown |
| VER-21 | 11.0 | `_` unused-variable tagging | compile-time semantic | BS-FUNC-014 |
| VER-22 | 11.5 | CONTINUE FOR/WHILE | syntax | BS-STMT-019 |
| VER-23 | 14.5 | `rsg_version=1.1` ignored | compile-time semantic | none (API) |
| VER-24 | 16.0 | undefined CC constants are `false` | compile-time semantic | BS-COND-011 |
| VER-25 | 16.0 | stack depth 8192 | resource | BS-FUNC-014 |
| VER-26 | not stated | `NEXT` legacy terminator | syntax (spelling) | BS-STMT-013 `since` baseline |
| VER-27 | not stated | conditional compilation introduced | syntax | BS-COND-001–008 `since` unknown |
| VER-28 | not stated | `Eval` deprecated | API | none |
| VER-29 | not stated | `Run` deprecated | API | none; name covered by BS-LEX-022 |

Syntax-relevant entries: 14 (VER-01, 06–12, 18–20, 22, 26, 27), all mapped. No
semantic change is implemented as a parser mode.

The research summary and the snapshot agree for every entry; no correction was
needed.
