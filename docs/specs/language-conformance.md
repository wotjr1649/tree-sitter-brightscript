# Language conformance registry

The single place where BrightScript language requirements are defined and
traced. Grammar rules, fixtures and release claims refer to the IDs below.

Status: registry populated in Session 02 (specification freeze) and
implemented in Session 03 (grammar version 0.1.0): every `documented`,
`provisional`, `tolerated` and `invalid` requirement is `covered`. Session 05
closed the deferred findings S04-D1–D6 and S04-M8 of the 0.1.0 release audit
without a grammar change, adding BS-STMT-040, BS-ARRAY-009, BS-AA-006,
BS-COND-014 and BS-COND-015. Every
requirement was promoted from the local research inventory in
`_ref/normative/roku-docs/notes/` after re-checking it against the Level 1
snapshot, following [source-policy.md](../provenance/source-policy.md). The
`Grammar` column names the rules and tokens that implement the requirement
([grammar-design.md](grammar-design.md)); node names are in
[tree-schema.md](tree-schema.md); fixture inputs are catalogued in
[workload-matrix.md](../validation/workload-matrix.md).

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
| `out-of-scope` | Semantic, runtime or compile-time rule the grammar does not enforce ([grammar-contract.md](grammar-contract.md) "Non-goals") | Recorded so it is not turned into grammar |
| `retired` | Withdrawn requirement | None |

A requirement is `covered` when its grammar rule exists and its required
fixtures pass at the gates in [validation.md](../validation/validation.md).

Implementation rules per status (frozen for the first implementation):

- `documented` and `provisional`: the rule is implemented exactly as stated and
  every listed positive fixture passes. A `provisional` row is implemented, not
  deferred; it states the chosen behaviour.
- `tolerated`: implemented as stated with its positive fixture; marked
  non-normative; it must not change the tree of any documented form.
- `invalid`: every listed negative fixture yields `ERROR` or `MISSING`.
- `unresolved`: no rule is added for the form and no corpus fixture asserts its
  tree. Whatever the grammar built for documented forms produces is
  non-contractual. Such inputs may appear only as robustness seeds (V10).
- `out-of-scope`: no rule. Rows marked "(guard)" have a positive fixture that
  shows the grammar does **not** enforce the semantic rule.

How grammar-contract §3 is applied: `provisional` is used only for a choice
about text the grammar must handle anyway — token boundaries and character
sets, line terminators, precedence and association, the choice between forms,
where a documented construct may be placed, and what a reserved compact word
stands for. Accepting an extra construct, operand kind, punctuation or empty
form that no documented form needs is an undocumented variant: `tolerated`
when §3.3 evidence exists, otherwise `unresolved`. Every `tolerated` row cites
BrighterScript parsing the variant in plain BrightScript mode without any
error diagnostic (neither `warnIfNotBrighterScriptMode` nor another one).

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

Coverage: a `covered` row meets the definition above for grammar version
0.1.0 (Session 03): every listed fixture is present and passes in workload W01;
`unresolved` and `out-of-scope` rows keep `none`. `—` means no known
limitation.

### LEX

| ID | Requirement | Evidence | Since | Status | Grammar | Positive fixtures | Negative / recovery fixtures | Coverage | KL | Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| BS-LEX-001 | Keywords, reserved words, identifiers and directive words match regardless of letter case; string contents keep their case. | SS (body); EVT §Identifiers; CC §Criteria | baseline | documented | `kw()` keyword tokens, `identifier` | `BS-LEX-001: keywords in upper, lower and mixed case`<br>`BS-LEX-001: identifier spellings differing only in case` | n/a — no invalid form | covered | — | LEX-01 |
| BS-LEX-002 | Space characters separate tokens; indentation and repeated spaces are insignificant. | SS, PS examples | baseline | documented | extras (whitespace) | `BS-LEX-002: indentation and repeated spaces` | n/a | covered | — | LEX-02 |
| BS-LEX-003 | Horizontal tab is whitespace equivalent to a space. No other character (form feed, vertical tab, U+00A0, other Unicode spaces) is whitespace. | L1 does not list whitespace characters | unknown | provisional | extras (whitespace) | `BS-LEX-003: tab indentation and tabs between tokens` | n/a | covered | — | LEX-02, AMB-32. Level 2 could widen the set; widening is compatible. |
| BS-LEX-004 | Adjacent tokens need no whitespace where the boundary is unambiguous (`print"error"`, `x=5:print 25`, `function():return m.xml@title:end function`, `tab(5)"tabbed 5"`). A keyword directly followed by identifier characters is one word (BS-LEX-026). | PS §DIM, §PRINT item list; CA §Attribute operator | baseline | documented | lexer (no rule) | `BS-LEX-004: keyword directly followed by a string`<br>`BS-LEX-004: compact one-line anonymous function` | n/a | covered | — | LEX-02, AMB-32 |
| BS-LEX-005 | The language is line oriented: a statement ends at the end of its line unless another statement follows after `:`. | SS (body); PS §IF expression THEN statements | baseline | documented | `_newline`, `_terminator` | `BS-LEX-005: one statement per line` | n/a | covered | — | LEX-03, LEX-05, LINE-01. No continuation syntax is documented; continuation forms are BS-EXP-023 (unresolved). |
| BS-LEX-006 | LF and CRLF both terminate a line; one file may mix them; trees are identical apart from byte offsets. | L1 does not name terminator bytes | unknown | provisional | `_newline` | `BS-LEX-006: CRLF line endings`<br>`BS-LEX-006: mixed LF and CRLF line endings`<br>`BS-LEX-006: CRLF between comment lines` | n/a | covered | — | LEX-03, AMB-07. Byte fixtures (validation fixture rules). |
| BS-LEX-007 | A bare CR (not followed by LF) as a line terminator. | none | unknown | unresolved | none — bare CR is neither whitespace nor terminator | n/a — unresolved | n/a | none | — | LEX-03, AMB-07 |
| BS-LEX-008 | End of file terminates the last line: a final statement, comment or block terminator needs no line terminator; an empty file and a file of only blank lines and comments parse without error. | L1 silent | unknown | provisional | `source_file` | `BS-LEX-008: final line without a line terminator`<br>`BS-LEX-008: final line with a line terminator`<br>`BS-LEX-008: empty file`<br>`BS-LEX-008: only comments and blank lines`<br>`BS-LEX-008: only indented blank lines` | n/a | covered | — | LINE-04, AMB-07 |
| BS-LEX-009 | Blank lines may appear before, between and after statements, inside block bodies and before block terminators. | multi-line examples on SS, PS, EVT, CC | baseline | documented | `source_file`, `block` | `BS-LEX-009: blank lines around and inside blocks` | n/a | covered | — | LINE-03 |
| BS-LEX-010 | `:` separates statements on one line in every statement list: file level, block bodies and single-line IF branches. | SS (body, example); PS §PRINT item list, §DIM | baseline | documented | `_terminator` | `BS-LEX-010: colon-separated statements`<br>`BS-LEX-010: colon-separated statements in a block body` | n/a | covered | — | LEX-04, LINE-02 |
| BS-LEX-011 | Any run of `:` and line terminators separates statements in file-level and block statement lists (leading, repeated and trailing colons produce no node), and repeated `:` separates statements of a single-line IF branch. Non-normative. | Level 4: BrighterScript @ `01a359c6` `src/parser/Parser.ts` `body()`, `block()` and `consumeStatementSeparators()` accept runs of colons and newlines, including leading ones, and `inlineConditionalBranch()` accepts repeated colons, all without an error diagnostic; L1 silent | unknown | tolerated | `_terminator`, `_inline_block` | `BS-LEX-011: repeated, leading and trailing colons` | n/a | covered | — | AMB-08. Changes no documented tree. A trailing `:` in a single-line branch has no contractual behaviour (BS-STMT-009). |
| BS-LEX-012 | `'` starts a comment that runs to the end of the line; it may stand alone or follow code; inside a string it is text. | EVT §Comments › In BrightScript; PS §REM | baseline | documented | `comment` (extra) | `BS-LEX-012: apostrophe comment lines`<br>`BS-LEX-012: comment after code on the same line`<br>`BS-LEX-012: apostrophe inside a string` | n/a | covered | — | LEX-06 |
| BS-LEX-013 | `REM` in any letter case followed by text starts a comment that runs to the end of the line. | PS §REM; SS; EVT §Comments | baseline | documented | `comment` (extra) | `BS-LEX-013: REM comments in mixed case` | n/a | covered | — | LEX-06, STM-13 |
| BS-LEX-014 | `REM` starts a comment only as a whole word followed by space, tab, line end or file end, including a line that holds only `REM`, at line start, after code and after `:`. `remark`, `rem1`, `rem_x` are identifiers. `rem` directly followed by another character (`rem:`, `rem(`) and `rem` as a member name or AA key have no contractual behaviour. | L1 silent on the boundary | unknown | provisional | `comment` token shape | `BS-LEX-014: identifiers beginning with rem`<br>`BS-LEX-014: REM after code and after a colon`<br>`BS-LEX-014: bare REM line` | n/a | covered | — | AMB-12 |
| BS-LEX-015 | Identifier: an ASCII letter or `_`, then ASCII letters, digits or `_`, any length. | EVT §Identifiers | baseline | documented | `identifier` (word token) | `BS-LEX-015: identifier forms` | n/a | covered | — | LEX-07 |
| BS-LEX-016 | Non-ASCII letters in identifiers. | EVT §Identifiers ("a – z") | unknown | unresolved | none | n/a — unresolved | n/a | none | — | LEX-07, AMB-09 |
| BS-LEX-017 | A variable name may end with one designator `$`, `%`, `!` or `#`, including parameters, FOR and FOR EACH variables and CATCH variables. The designator is part of the identifier token, so `a`, `a$` and `a%` are different identifiers. | EVT §Identifiers ("If a variable"), §Type declaration characters; PS §FUNCTION (parameters), §FOR ("counter-variable"), §FOR EACH ("the variable item"), §TRY / CATCH ("a simple variable") | baseline | documented | `identifier` | `BS-LEX-017: variables with type designators`<br>`BS-LEX-017: designators on parameters and loop and catch variables` | n/a | covered | — | LEX-08, TYP-03. Parameters, loop variables and CATCH variables are variables in PS wording, so EVT's "If a variable" rule applies; no L1 example shows a designator there (the research notes FUN-04 and AMB-33 recorded that absence). |
| BS-LEX-018 | The `&` designator (LongInteger) on variable names (`A&`, `ID&`). | EVT §Type declaration characters, §Types | 7.0 | documented | `identifier` | `BS-LEX-018: LongInteger designator on a variable` | n/a | covered | — | LEX-08, VER-10 |
| BS-LEX-019 | Function names do not take type designators. Compile-time rule; the shared identifier token accepts a designator on a function name. | EVT §Identifiers | baseline | out-of-scope | none | n/a | n/a | none | — | FUN-04 |
| BS-LEX-020 | Designators on member names, AA identifier keys, labels and GOTO targets. | none | unknown | unresolved | none added — the shared identifier token accepts them | n/a — unresolved | n/a | none | — | AMB-09 |
| BS-LEX-021 | Reserved words that are grammar keywords (`And Dim Each Else ElseIf End EndFunction EndIf EndSub EndWhile Exit ExitWhile False For Function Goto If Invalid LINE_NUM Next Not Or Print Rem Return Step Stop Sub Then To True While`) are recognised as keywords in any letter case wherever the grammar expects them. | RW; PS; EVT | baseline | documented | `kw()`, `word: identifier` | `BS-LEX-021: reserved keywords in statement positions`<br>`BS-LEX-021: reserved keywords in mixed case` | n/a | covered | — | LEX-09, AMB-01. The fixtures also rest on BS-STMT-035 (tolerated: the one-line `While True : … : End While`) and on the provisional meaning of the compact words `ExitWhile`, `EndWhile`, `EndSub`, `EndFunction` (BS-STMT-020, BS-FUNC-003). |
| BS-LEX-022 | Reserved words documented as functions (`Box CreateObject Eval GetGlobalAA GetLastRunCompileError GetLastRunRunTimeError Pos Run Tab Type`) use ordinary call syntax and parse as a `call_expression` on an `identifier`, including `Tab`/`Pos` in PRINT lists. `ObjFun` is reserved but undocumented and is an ordinary identifier (BS-LEX-023). | RW; RF; PS §PRINT item list | baseline | documented | `identifier`, `call_expression` | `BS-LEX-022: reserved built-in function calls`<br>`BS-LEX-022: Eval, Run and GetLastRunRunTimeError calls` | n/a | covered | — | FUN-07, AMB-01, AMB-24 |
| BS-LEX-023 | A reserved word used as a variable, function, parameter or label name is a compile error. The grammar rejects such a use only where the word is a grammar keyword in that position (statement-initial `end = 1`); `step = 1` or `box = 1` are not rejected. | RW | baseline | out-of-scope | none — keyword extraction only | n/a | n/a | none | — | AMB-01, AMB-24. This includes the literal words `true`, `false`, `invalid` and `LINE_NUM` where the grammar expects a name and the word is not a valid token there (`catch true`, `#const true = false`, `#const x = invalid`, `#if invalid`, `for LINE_NUM = 1 to 2`, `sub f(true)`): they parse as an `identifier` without an error (grammar-design §4). |
| BS-LEX-024 | Keyword words are accepted as member names after `.`/`?.` and as identifier keys in associative-array literals (`e.backtrace[i].function`, `{ function: "main()" }`, `list.next()`), except `rem` (BS-LEX-014). | EH §The backtrace (`.function` as a member name) and §Invalid throws (`function` as a key) in source code; EVT §Identifiers and §Associative array literals prose ("Key names must be valid identifiers") point the other way | unknown | provisional | `identifier` through contextual keyword extraction | `BS-LEX-024: keywords as member names`<br>`BS-LEX-024: keywords as associative-array keys`<br>`BS-LEX-024: function as a member name after an index` | n/a | covered | — | AMB-01, LIT-12, EXP-03. Tightening later would reject the L1 examples. |
| BS-LEX-025 | Words that act as syntax but are not on the reserved list (`As Catch Continue In Library Mod Throw Try`, the `AS` type names, `EndTry`) are keywords only where the grammar expects them and identifiers elsewhere (`mod = 3`, `x = in + as`). In a file or block statement list, statement-initial `try`, `throw`, `continue`, `library`, and statement-initial `catch` directly inside a TRY body, always start their statements. | RW (absence); PS §TRY / CATCH, §THROW; EVT §Operators; CA §Script libraries | unknown | provisional | `kw()` with contextual keyword extraction | `BS-LEX-025: non-reserved keyword words as identifiers`<br>`BS-LEX-025: more non-reserved words as identifiers` | n/a | covered | — | LEX-10, AMB-02; candidate "`mod` as a variable name" (Level 4 claim, not used as evidence). Known incompatibility: pre-9.4 and pre-11.5 code using `try`, `catch`, `throw`, `continue` as statement-initial names. A single-line IF branch is not a statement list: `throw` and `continue` start their statements there too (BS-STMT-009, BS-STMT-007), while `try` and `library`, which have no single-line form, fall under the first sentence (`if a then try = 1` assigns to `try`). |
| BS-LEX-026 | Keyword recognition respects word boundaries: an identifier that begins with a keyword (`iffy`, `endpoint`, `format`, `printer`, `nextItem`, `stepSize`, `notify`, `order`, `android`, `returnValue`, `falsey`) is one identifier. | EVT §Identifiers | baseline | documented | `word: identifier` | `BS-LEX-026: identifiers beginning with keywords` | n/a | covered | — | LEX-07 |
| BS-LEX-027 | A label is an identifier followed by `:` on a line by itself; it is the target of GOTO. | PS §GOTO label; CA §Scope | baseline | documented | `label_statement` | `BS-LEX-027: label line` | n/a | covered | — | LEX-11 |
| BS-LEX-028 | A label line may end with a comment. Code before or after a label on the same line has no contractual behaviour. | L1 silent | unknown | provisional | `label_statement` | `BS-LEX-028: label followed by a comment` | n/a | covered | — | AMB-08 |
| BS-LEX-029 | Optional-chaining operators `?.`, `?@`, `?[`, `?(` are indivisible tokens; whitespace may precede them (`a = b ?. c`, `x = s ?[ 5 ]`). | EVT §Optional chaining operators › Notes | 11.0 | documented | tokens `?.` `?@` `?[` `?(` | `BS-LEX-029: optional-chaining tokens after whitespace` | n/a | covered | — | LEX-12, AMB-16 |
| BS-LEX-030 | `?` separated from `.` by whitespace (`a = b ? . c`) is not an optional-chaining operator. | EVT §Optional chaining operators › Notes ("Do not write") | 11.0 | invalid | tokenization | n/a | `BS-LEX-030: split optional-chaining token` | covered | — | AMB-16 |
| BS-LEX-031 | At the start of a statement `?` is PRINT, also when directly followed by `(` or by `.` and a digit (`?("Hello")`, `?.1`). | EVT §Optional chaining operators › Support details; SS | baseline | documented | `print_statement` | `BS-LEX-031: question-mark PRINT alias forms` | n/a | covered | — | LEX-13, AMB-16 |
| BS-LEX-032 | `IF x?("Hello")` at the end of its line begins a block IF whose condition is an optional call; it does not print. | EVT §Optional chaining operators › Support details | unknown | documented | `if_statement`, `call_expression` | `BS-LEX-032: IF with an optional call starts a block IF` | n/a | covered | — | VER-20, AMB-16. Known incompatibility: older firmware printed. |
| BS-LEX-033 | Source text is UTF-8; a leading UTF-8 byte-order mark is ignored; non-ASCII characters are ordinary content in comments and strings. | L1 states an encoding only for XML (CA §BrightScript XML support). The Tree-sitter runtime skips a leading BOM before the grammar sees the input (runtime behaviour, `lib/src/lexer.c` @ `v0.27.0`), which the fixture records | unknown | provisional | `string`, `comment` | `BS-LEX-033: UTF-8 text in comments and strings`<br>`BS-LEX-033: leading byte-order mark` | n/a | covered | — | LINE-06, AMB-11 |
| BS-LEX-034 | Other encodings (UTF-16, Latin-1), invalid UTF-8 and NUL bytes. | none | unknown | unresolved | none | n/a — unresolved | n/a | none | — | LINE-06 |
| BS-LEX-035 | At the start of a statement `?` directly followed by `[` is PRINT followed by an array literal (`?[1]`). | L1 shows only `?(` and `?.1` (EVT §Optional chaining operators › Support details) | unknown | provisional | `print_statement` (context-aware lexing) | `BS-LEX-035: question mark followed by a bracket at statement start` | n/a | covered | — | AMB-16 |

### LIT

| ID | Requirement | Evidence | Since | Status | Grammar | Positive fixtures | Negative / recovery fixtures | Coverage | KL | Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| BS-LIT-001 | `true` and `false` in any letter case. | EVT §Literals (constants) | baseline | documented | `true`, `false` | `BS-LIT-001: boolean literals` | n/a | covered | — | LIT-01 |
| BS-LIT-002 | `invalid` in any letter case. | EVT §Literals, §Types | baseline | documented | `invalid` | `BS-LIT-002: invalid literal` | n/a | covered | — | LIT-02 |
| BS-LIT-003 | Decimal integer literal: one or more digits. | EVT §Numeric literals | baseline | documented | `number` | `BS-LIT-003: decimal integers` | n/a | covered | — | LIT-03 |
| BS-LIT-004 | There is no signed literal; `-5` is unary negation applied to `5`. | EVT §Negation operator, §Numeric literals | baseline | documented | `unary_expression` | `BS-LIT-004: negative number is unary negation` | n/a | covered | — | LIT-03, AMB-10 |
| BS-LIT-005 | Hex integer: `&H` or `&h` followed by hex digits (`&HFF`, `&hFF`, `&h28`). | EVT §Numeric literals; EH; RF | baseline | documented | `number` | `BS-LIT-005: hex integers with either prefix case` | n/a | covered | — | LIT-04 |
| BS-LIT-006 | Lowercase hex digits (`&hff`, `&hFe`). | L1 examples use uppercase digits only | unknown | provisional | `number` | `BS-LIT-006: lowercase hex digits` | n/a | covered | — | LIT-04, AMB-10 |
| BS-LIT-007 | Float forms: decimal point (`2.01`), `E` exponent with optional sign (`1.23456E+30`), `!` suffix (`2!`, `125!`). | EVT §Numeric literals, §Type declaration characters | baseline | documented | `number` | `BS-LIT-007: float literal forms` | n/a | covered | — | LIT-05, LIT-08 |
| BS-LIT-008 | Lowercase `e`, unsigned exponent (`1e1000000`) and leading-dot fraction (`.1`). | EH §Miscellaneous examples; EVT §Optional chaining operators › Support details (`?.1`) | baseline | documented | `number` | `BS-LIT-008: lowercase unsigned exponent and leading-dot fraction` | n/a | covered | — | LIT-05, AMB-10 |
| BS-LIT-009 | Double forms: `D` exponent (`1.23456789D-12`), `#` suffix (`2.3#`, `125#`). | EVT §Numeric literals, §Type declaration characters | baseline | documented | `number` | `BS-LIT-009: double literal forms` | n/a | covered | — | LIT-06 |
| BS-LIT-010 | Lowercase `d` exponent (`1.5d-3`). | L1 examples use uppercase only | unknown | provisional | `number` | `BS-LIT-010: lowercase d exponent` | n/a | covered | — | AMB-10 |
| BS-LIT-011 | LongInteger literal: `&` suffix on decimal (`9876543210&`) and hex (`&hFEDCBA9876543210&`) integers. | EVT §Numeric literals, §Types; RN §Roku OS 7.0 | 7.0 | documented | `number` | `BS-LIT-011: LongInteger literals` | n/a | covered | — | LIT-07, VER-10 |
| BS-LIT-012 | `%` suffix on integer literals (`125%`, `100%`). | EVT §Type declaration characters; CA §Use of wrapper functions on intrinsic types | baseline | documented | `number` | `BS-LIT-012: integer suffix on a literal` | n/a | covered | — | LIT-08 |
| BS-LIT-013 | Other numeric forms: trailing dot (`5.`), suffixes other than `&` on hex (`&hFF%`), `&h` without digits, `5.e3`, and designators on literals other than those shown (`5$`, `1.5%`, `2.5&`). | EVT §Type declaration characters allows a designator "at the end of either a variable or a literal" without listing the combinations | unknown | unresolved | none beyond the planned `number` token shape | n/a — unresolved | n/a | none | — | AMB-10 |
| BS-LIT-014 | After digits, `.` followed by a letter is member access, not a fraction: `5.tostr()`, `100%.tostr()`, `"5".toint()`, `"01234567".left(3)`. | CA §Use of wrapper functions on intrinsic types | baseline | documented | `number` token shape, `member_expression` | `BS-LIT-014: method call on a numeric literal`<br>`BS-LIT-014: method call on a string literal` | n/a | covered | — | LIT-09 |
| BS-LIT-015 | String literal: text between double quotes on one line. | EVT §String literals | baseline | documented | `string` | `BS-LIT-015: string literals` | `BS-LIT-015: unterminated string at end of line` (recovery) | covered | — | LIT-10 |
| BS-LIT-016 | `""` inside a string is one quotation mark; `""""` is a one-character string. | EVT §String literals; RN §Roku OS 6.2 | 6.2 | documented | `string` | `BS-LIT-016: doubled quotation marks` | n/a | covered | — | LIT-10, VER-08 |
| BS-LIT-017 | No other escape mechanism: backslash and every character except `"` and line terminators are literal string content. | EVT §String literals (only `""` documented) | unknown | provisional | `string` | `BS-LIT-017: backslash and non-ASCII text in strings` | n/a | covered | — | LIT-10, AMB-11 |
| BS-LIT-018 | Strings spanning lines. | none | unknown | unresolved | none — a line terminator ends string scanning | n/a — unresolved | n/a | none | — | AMB-11 |
| BS-LIT-019 | `LINE_NUM` source literal (reserved word). | EVT §Source literals; RW; RF §Run | baseline | documented | `source_literal` | `BS-LIT-019: LINE_NUM source literal` | n/a | covered | — | LEX-14 |
| BS-LIT-020 | A function name used as a value (`fivevar = five`) is an ordinary identifier expression. | EVT §Function literals, §Function call operator | baseline | documented | `identifier` | `BS-LIT-020: function name used as a value` | n/a | covered | — | LIT-13 |

### TYPE

| ID | Requirement | Evidence | Since | Status | Grammar | Positive fixtures | Negative / recovery fixtures | Coverage | KL | Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| BS-TYPE-001 | `AS` type names in any letter case: `Integer Float Double Boolean String Object Dynamic Function`, plus `Void` for return types. One `type` rule serves parameters and return types. | PS §FUNCTION(…) AS type | baseline | documented | `type` | `BS-TYPE-001: parameter and return type names` | n/a | covered | — | TYP-01, VER-01. RN §Roku OS 3.0 lists "typed values in function parameters and returns", but its compatibility note shows declared return types already existed in BrightScript v2.0, so no version boundary is established for the syntax. `void` on a parameter is accepted by the shared rule (non-contractual). |
| BS-TYPE-002 | `LongInteger`, `Interface` and `Invalid` as `AS` type names. | EVT §Types lists the types, not their use in `AS` | unknown | unresolved | none | n/a — unresolved | n/a | none | — | TYP-02, AMB-26 |
| BS-TYPE-003 | Dynamic typing, declared-type conversion, promotion, rounding, autoboxing and `type()` results. | EVT §Types, §Type conversion (promotion), §Effects of type conversions on accuracy; CA | baseline | out-of-scope | none | n/a | n/a | none | — | TYP-04 |

### EXP

| ID | Requirement | Evidence | Since | Status | Grammar | Positive fixtures | Negative / recovery fixtures | Coverage | KL | Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| BS-EXP-001 | Primary expressions: identifiers, literals, `LINE_NUM`, parenthesized expressions, array and associative-array literals, anonymous functions. | EVT §Literals (constants), §Function call operator; PS §Anonymous functions | baseline | documented | `expression` supertype | `BS-EXP-001: primary expressions` | n/a | covered | — | EXP-01 |
| BS-EXP-002 | Parentheses group an expression and override precedence. | EVT §Operators | baseline | documented | `parenthesized_expression` | `BS-EXP-002: parentheses override precedence` | `BS-EXP-002: unclosed parenthesis` (recovery) | covered | — | EXP-01 |
| BS-EXP-003 | Call: an expression followed by `(`, zero or more comma-separated arguments and `)` (`five()`, `fivevar()`, `array[1]()`, `obj.add()`). | EVT §Function call operator | baseline | documented | `call_expression`, `argument_list` | `BS-EXP-003: call forms` | n/a | covered | — | EXP-02 |
| BS-EXP-004 | Dot member access: chained, applied to call results and parenthesized expressions, interface-qualified (`i.ifInt.SetInt(5)`, `(1+2).tostr()`). | EVT §Dot operator; CA §Use of wrapper functions on intrinsic types | baseline | documented | `member_expression` | `BS-EXP-004: member access chains` | n/a | covered | — | EXP-03 |
| BS-EXP-005 | Index access `[expr]`, chained (`a[1][2]`) and applied to member and call results. | EVT §Array operator | baseline | documented | `index_expression` | `BS-EXP-005: index access and chained indexing` | n/a | covered | — | EXP-04 |
| BS-EXP-006 | XML attribute operator `@`: `element@name` (`rsp.photos@perpage`, `m.xml@title`). | CA §Attribute operator | baseline | documented | `attribute_expression` | `BS-EXP-006: attribute operator` | n/a | covered | — | EXP-05 |
| BS-EXP-007 | Optional chaining `?.`, `?@`, `?[`, `?(` in expressions, freely chained (`array?[3]?.foo?.bar?()`); each shares its node type with the non-optional form. | EVT §Optional chaining operators; RN §Roku OS 11.0 | 11.0 | documented | `member_expression`, `attribute_expression`, `index_expression`, `call_expression` | `BS-EXP-007: optional chaining chain`<br>`BS-EXP-007: optional call and optional index with arguments` | n/a | covered | — | EXP-06, VER-19 |
| BS-EXP-008 | An optional-chaining operator as the outermost accessor of an assignment target (`array?[12] = x`, `a?.b = 1`). | EVT §Optional chaining operators › Support details ("Not supported") | 11.0 | invalid | `_assignment_target` excludes optional accessors | n/a | `BS-EXP-008: optional index as an assignment target`<br>`BS-EXP-008: optional member as an assignment target` | covered | — | EXP-06, ASN-01, AMB-16 |
| BS-EXP-009 | A standalone call statement whose outermost call is `?(` (`f?()`). | EVT §Optional chaining operators › Support details ("Not supported") | 11.0 | invalid | call statements require `(` as the outermost call | n/a | `BS-EXP-009: standalone optional call statement`<br>`BS-EXP-009: standalone optional call on a member` | covered | — | EXP-06, STM-17 |
| BS-EXP-010 | Optional chaining inside the argument lists and index expressions of call statements and assignment targets (`f(array?[12])`, `f(foo?.bar).member = 5`). | EVT §Optional chaining operators › Support details | 11.0 | documented | `call_expression`, `assignment_statement` | `BS-EXP-010: optional chaining inside statement subexpressions` | n/a | covered | — | EXP-06. Optional operators in the statement chain itself: BS-STMT-006. |
| BS-EXP-011 | `^` exponentiation, right associative (`2^3^2` = `2^(3^2)`). | EVT §Operators, §Exponentiation operator | baseline | documented | `binary_expression` (exponent level, right) | `BS-EXP-011: exponentiation is right associative` | n/a | covered | — | EXP-07 |
| BS-EXP-012 | Unary `-` and `+` bind looser than postfix operators and `^`, tighter than multiplicative operators (`-5.tostr()` = `-(5.tostr())`, `-2^2` = `-(2^2)`, `-a*b` = `(-a)*b`). | EVT §Operators, §Negation operator; CA §Use of wrapper functions on intrinsic types | baseline | documented | `unary_expression` (unary level) | `BS-EXP-012: unary minus against postfix and exponent`<br>`BS-EXP-012: unary operators against multiplication` | n/a | covered | — | EXP-08. CA says `-5.tostr()` "will cause an error": a runtime error from negating a string (BS-EXP-026); the parse is `-(5.tostr())`. |
| BS-EXP-013 | `*`, `/` and `MOD` share one level, left associative. | EVT §Operators, §Multiplicative operators | baseline | documented | `binary_expression` (multiplicative level) | `BS-EXP-013: multiplicative operators are left associative` | n/a | covered | — | EXP-09, AMB-13 (`*` lost in the rendered table; prose and examples keep it) |
| BS-EXP-014 | `\` integer division, same level as `*`. | EVT §Multiplicative operators; RN §Roku OS 6.1 | 6.1 | documented | `binary_expression` (multiplicative level) | `BS-EXP-014: integer division` | n/a | covered | — | EXP-09, VER-06 |
| BS-EXP-015 | `+` and `-` (also string concatenation), left associative, below multiplicative. | EVT §Operators, §Additive operators | baseline | documented | `binary_expression` (additive level) | `BS-EXP-015: additive operators against multiplicative` | n/a | covered | — | EXP-10 |
| BS-EXP-016 | `<<` and `>>` below additive and above comparisons. | EVT §Operators, §Integer bitshift operators; RN §Roku OS 6.1 | 6.1 | documented | `binary_expression` (shift level) | `BS-EXP-016: shifts between additive and comparison` | n/a | covered | — | EXP-11, VER-07 |
| BS-EXP-017 | Comparisons `=`, `<>`, `<`, `>`, `<=`, `>=` share one level, left associative (`a < b < c` = `(a < b) < c`). | EVT §Operators, §Comparison operators | baseline | documented | `binary_expression` (comparison level) | `BS-EXP-017: comparison operators and chains` | n/a | covered | — | EXP-12, AMB-13 |
| BS-EXP-018 | `NOT` is a prefix operator below comparisons and above `AND` (`not a = b` = `not (a = b)`, `not a and b` = `(not a) and b`). | EVT §Operators, §Logical and bitwise operators | baseline | documented | `unary_expression` (NOT level) | `BS-EXP-018: NOT below comparison and above AND` | n/a | covered | — | EXP-13 |
| BS-EXP-019 | `AND` binds tighter than `OR`; both left associative (`a or b and c` = `a or (b and c)`). | EVT §Operators, §Logical and bitwise operators | baseline | documented | `binary_expression` (AND and OR levels) | `BS-EXP-019: AND binds tighter than OR` | n/a | covered | — | EXP-14 |
| BS-EXP-020 | Inside an expression `=` is comparison; assignment is a statement, never an expression (`if a=5 then …`, `x = a = b`). | EVT §= operator | baseline | documented | `binary_expression`, `assignment_statement` | `BS-EXP-020: equals inside an expression is comparison` | n/a | covered | — | EXP-16 |
| BS-EXP-021 | Call, `.`, `[]`, `@` and their optional forms form one postfix level applied left to right; `@` binds like `.` (`x@y.z` = `(x@y).z`, `a.b@c` = `(a.b)@c`). | EVT §Operators (the table lists postfix operators on separate rows and omits `@`) | unknown | provisional | postfix level | `BS-EXP-021: mixed postfix chain`<br>`BS-EXP-021: attribute operator inside a member chain` | n/a | covered | — | EXP-15, AMB-13 |
| BS-EXP-022 | Adjacent operands without an operator outside PRINT (`"a"b"c"`). | CA §Attribute operator (unexplained example) | unknown | unresolved | none | n/a — unresolved | n/a | none | — | EXP-17, AMB-28. The example is excluded from fixtures. |
| BS-EXP-023 | A line break after a binary operator, inside grouping parentheses or inside index brackets. | none | unknown | unresolved | none | n/a — unresolved | n/a | none | — | LEX-05, AMB-07. BrighterScript (Level 4, `src/RokuConstants.ts` @ `01a359c6`) enables continuation after binary operators from Roku OS 15.3, citing release notes whose 15.3 section in snapshot `roku-docs-2026-09-23` does not mention it; the claim is not used. Revisited at the refresh `roku-docs-2026-09-23-r2`: still not mentioned. |
| BS-EXP-024 | Line breaks inside argument lists (after `(`, after a `,`, before `)`). | L1 shows a line break only in a parameter list (BS-FUNC-006) | unknown | unresolved | none | n/a — unresolved | n/a | none | — | LINE-05, AMB-07. BrighterScript (Level 4) accepts them only with its Roku OS 15.3 line-continuation capability (see BS-EXP-023). |
| BS-EXP-025 | Postfix operators on operand kinds that Level 1 does not show: a call or index applied directly to a literal (`"a"(1)`, `5[0]`), and member or index access on array or associative-array literals (`[1, 2].count()`, `[1][0]`). | L1 shows postfix operators on identifiers, on results of postfix operators, on parenthesized expressions and (member access only) on numeric and string literals | unknown | unresolved | none — the planned operand kinds (grammar-design §5) exclude them | n/a — unresolved | n/a | none | — | EXP-02, EXP-03, LIT-09 |
| BS-EXP-026 | Operator semantics: numeric promotion, concatenation, short-circuit evaluation, runtime errors, `?.` on interface names, the `TYPE?(` compile error. | EVT §Operators subsections; CA | baseline | out-of-scope | none | n/a | n/a | none | — | EXP-14, AMB-35 |
| BS-EXP-027 | A prefix operator may start the right operand of a tighter binary operator and applies to that operand at its own level: `2^-2` = `2^(-2)`, `x * -y` = `x * (-y)`, `a < not b` = `a < (not b)`. | L1 shows a prefix operator on the right only where it binds tighter than the operator (`<>-1.1`, CA §Use of wrapper functions on intrinsic types) | unknown | provisional | `unary_expression` inside `binary_expression` | `BS-EXP-027: prefix operators as right operands` | n/a | covered | — | AMB-13. Provisional, not tolerated: the form needs no extra rule (a prefix operator starts any operand); what is chosen is the tree shape. BrighterScript (Level 4) accepts these forms but is not evidence for their shape. |

### STMT

| ID | Requirement | Evidence | Since | Status | Grammar | Positive fixtures | Negative / recovery fixtures | Coverage | KL | Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| BS-STMT-001 | Assignment `target = expression`. A target is an identifier (with designator) or a chain of `.` member access, index access (one or more indexes) and calls that starts with an identifier and ends with `.name` or `[…]` (`aa.newkey`, `c[x, y, z]`, `f(x).y`). | PS §variable = expression; EVT §Dot operator, §Array operator, §Optional chaining operators › Support details (`f(foo?.bar).member = 5`) | baseline | documented | `assignment_statement`, `_assignment_target` | `BS-STMT-001: assignment to variables, members and indexes` | `BS-STMT-001: assignment missing its value` (recovery) | covered | — | ASN-01. Chains containing `?.`, `?[` or `@`: BS-EXP-008, BS-STMT-006. |
| BS-STMT-002 | Compound assignment `+=`, `-=`, `*=`, `/=`, `\=`, `<<=`, `>>=` on the same targets. `^=`, `MOD=` and other spellings are not accepted (no rule). | EVT §Mathematical and bitshift assignment operators (examples); RN §Roku OS 7.1 (list) | 7.1 | documented | `assignment_statement` | `BS-STMT-002: compound assignment operators` | n/a | covered | — | ASN-02, VER-12, AMB-14 |
| BS-STMT-003 | `x++` and `x--` statements on a variable. | EVT §Increment and decrement operators; PS §CONTINUE FOR / CONTINUE WHILE; RN §Roku OS 7.1 | 7.1 | documented | `update_statement` | `BS-STMT-003: increment and decrement statements` | n/a | covered | — | ASN-03, VER-11 |
| BS-STMT-004 | `++`/`--` on member and index targets (`a.b++`, `a[0]--`). Non-normative. Prefix forms and use inside expressions have no contractual behaviour. | Level 4: BrighterScript @ `01a359c6` `src/parser/Parser.ts` `expressionStatement()` accepts `++`/`--` after any non-call expression with no error diagnostic; L1 shows only variables | unknown | tolerated | `update_statement` over `_assignment_target` | `BS-STMT-004: increment and decrement on member and index targets` | n/a | covered | — | ASN-03, AMB-15. Changes no documented tree. |
| BS-STMT-005 | Call statement: a chain of `.` member access, index access and calls that starts with an identifier and ends with a call using `(` (`HandleButton(msg.GetInt())`, `cavemen.push("fred")`). | PS, EVT, CA examples | baseline | documented | `call_expression` in `statement` (`_stmt_call`) | `BS-STMT-005: call statements` | n/a | covered | — | STM-17 |
| BS-STMT-006 | Other statements built from expressions: bare expressions (`x`, `a + b`, `a.b`); call statements whose chain starts with something other than an identifier (`(f)()`, `"x".len()`); call statements and assignment or update targets whose chain contains `?.`, `?[`, `?(` or `@` before the last step (`a?.b.c()`, `a?.b.c = 1`, `x@y.z = 1`). | L1 says optional chaining "cannot be used directly in a standalone function call or as the target of an assignment" without defining "directly" | unknown | unresolved | none — statement chains contain only `.`, index access and `(` calls | n/a — unresolved | n/a | none | — | STM-17, AMB-16 |
| BS-STMT-007 | Single-line IF: `IF condition [THEN] statements [ELSE statements]` on one line; THEN optional; each branch holds one or more statements separated by `:` and extends to the end of the line. Statement kinds shown in single-line branches: assignment, call, PRINT (`?`), RETURN, EXIT WHILE, CONTINUE FOR, STOP. | PS §IF expression THEN statements [ELSE statements], §DIM, §WHILE, §CONTINUE FOR / CONTINUE WHILE; SS (example); CA §Attribute operator; EH §Reacting to an error without handling it | baseline | documented | `if_statement` (single-line form), `else_clause` | `BS-STMT-007: single-line IF with THEN`<br>`BS-STMT-007: single-line IF without THEN`<br>`BS-STMT-007: single-line IF with ELSE`<br>`BS-STMT-007: colon-separated statements in a single-line branch`<br>`BS-STMT-007: documented statement kinds in single-line branches` | n/a | covered | — | STM-01, AMB-04, AMB-05 |
| BS-STMT-008 | After the condition and optional THEN, a line end, comment or `:` selects the block form; any statement start selects the single-line form. | EVT §Optional chaining operators › Support details (comment case); L1 silent on `:` | unknown | provisional | `if_statement` factoring | `BS-STMT-008: THEN followed by a comment starts a block IF`<br>`BS-STMT-008: THEN followed by a colon starts a block IF` | n/a | covered | — | STM-02, AMB-04 |
| BS-STMT-009 | Single-line IF composition: ELSE belongs to the nearest single-line IF; a branch may hold a nested single-line IF; `ELSE IF` in single-line form is an ELSE branch holding a nested IF; branches also accept GOTO, END, THROW, DIM and update statements. A trailing `:` in a branch and block statements in a branch have no contractual behaviour. | L1 silent | unknown | provisional | `_inline_statement`, `if_statement` | `BS-STMT-009: nested single-line IF with ELSE`<br>`BS-STMT-009: single-line ELSE IF nests an IF`<br>`BS-STMT-009: other statement kinds in single-line branches` | n/a | covered | — | AMB-05. Repeated `:` in a branch: BS-LEX-011. |
| BS-STMT-010 | Block IF: `IF condition [THEN]`, line end, statements, any number of `ELSEIF`/`ELSE IF condition [THEN]` clauses, optional `ELSE`, closed by `END IF` or `ENDIF`. | PS §Block IF, ELSEIF, THEN, ENDIF | baseline | documented | `if_statement`, `else_if_clause`, `else_clause` | `BS-STMT-010: block IF with ELSE IF and ELSE`<br>`BS-STMT-010: ELSEIF and ENDIF spellings`<br>`BS-STMT-010: block IF without THEN`<br>`BS-STMT-010: ELSE IF and ELSEIF without THEN` | `BS-STMT-010: block IF missing END IF` (recovery) | covered | — | STM-02, AMB-03 |
| BS-STMT-011 | In a block IF, the `ELSE` and `ELSE IF … [THEN]` headers may end with `:` instead of a line end; a comment may follow them as it may follow any code (BS-LEX-012). Code directly after them on the same line has no contractual behaviour. Non-normative. | Level 4: BrighterScript @ `01a359c6` `src/parser/Parser.ts` `ifStatement()` → `blockConditionalBranch()` → `block()`, which starts with `consumeStatementSeparators(true)`, without an error diagnostic; L1 shows these headers only at line ends | unknown | tolerated | `else_clause`, `else_if_clause` (`block` starts with `_terminator`) | `BS-STMT-011: ELSE and ELSE IF headers followed by comments and colons` | n/a | covered | — | AMB-04, AMB-05. Changes no documented tree. |
| BS-STMT-012 | Counted loop `FOR counter = start TO end [STEP increment]`, body, `END FOR`. | PS §FOR counter = exp TO exp [STEP exp] / END FOR | baseline | documented | `for_statement` | `BS-STMT-012: FOR with and without STEP` | `BS-STMT-012: FOR missing END FOR` (recovery) | covered | — | STM-03 |
| BS-STMT-013 | Bare `NEXT` terminates FOR and FOR EACH. | PS §FOR …, §FOR EACH item IN object | baseline | documented | `for_statement`, `for_each_statement` | `BS-STMT-013: NEXT terminates FOR and FOR EACH` | n/a | covered | — | STM-03, AMB-06, VER-26 |
| BS-STMT-014 | `NEXT counter` and `NEXT i, j`. | none | unknown | unresolved | none | n/a — unresolved | n/a | none | — | AMB-06 |
| BS-STMT-015 | `FOR EACH item IN expression`, body, `END FOR`. | PS §FOR EACH item IN object | baseline | documented | `for_each_statement` | `BS-STMT-015: FOR EACH over an expression` | n/a | covered | — | STM-04 |
| BS-STMT-016 | `WHILE condition`, body, `END WHILE`. | PS §WHILE expression / EXIT WHILE / END WHILE | baseline | documented | `while_statement` | `BS-STMT-016: WHILE loop` | `BS-STMT-016: WHILE missing END WHILE` (recovery) | covered | — | STM-05 |
| BS-STMT-017 | `NEXT` does not terminate a WHILE loop. | PS §WHILE ("cannot be terminated with NEXT") | baseline | invalid | `while_statement` accepts only `END WHILE`/`ENDWHILE` | n/a | `BS-STMT-017: WHILE terminated by NEXT` | covered | — | STM-05 |
| BS-STMT-018 | `EXIT FOR` and `EXIT WHILE`. | PS §FOR, §FOR EACH, §WHILE; SS | baseline | documented | `exit_statement` | `BS-STMT-018: EXIT FOR and EXIT WHILE` | n/a | covered | — | STM-03, STM-05, STM-18 |
| BS-STMT-019 | `CONTINUE FOR` and `CONTINUE WHILE`. | PS §CONTINUE FOR / CONTINUE WHILE; RN §Roku OS 11.5 | 11.5 | documented | `continue_statement` | `BS-STMT-019: CONTINUE FOR and CONTINUE WHILE` | n/a | covered | — | STM-06, VER-22 |
| BS-STMT-020 | Compact `ENDWHILE` and `EXITWHILE` (reserved words) are equivalent to `END WHILE` and `EXIT WHILE`. | RW (membership only) | unknown | provisional | `kw('endwhile')`, `kw('exitwhile')` | `BS-STMT-020: ENDWHILE and EXITWHILE` | n/a | covered | — | AMB-03 |
| BS-STMT-021 | `ENDFOR`, `EXITFOR`, `FOREACH`, bare `EXIT`, bare `CONTINUE`. | none — absent from RW and examples | unknown | unresolved | none | n/a — unresolved | n/a | none | — | STM-18, AMB-03. BrighterScript (Level 4, `src/lexer/TokenKind.ts` @ `01a359c6`) lexes `endfor` as END FOR; not adopted, since the grammar has no rule for it (a `tolerated` row needs an implemented rule). |
| BS-STMT-022 | The words of a multi-word keyword (`END IF`, `ELSE IF`, `FOR EACH`, `EXIT FOR`, `END FUNCTION`, …) may be separated by any run of spaces and tabs, never by a line break. | L1 silent | unknown | provisional | single-token `END X` terminators, separate tokens for the other multi-word keywords (grammar-design §3) | `BS-STMT-022: multi-word keywords with extra spacing`<br>`BS-STMT-022: more multi-word keywords with extra spacing` | n/a | covered | — | AMB-03 |
| BS-STMT-023 | `RETURN [expression]`. | PS §RETURN [expression] | baseline | documented | `return_statement` | `BS-STMT-023: RETURN with and without a value` | n/a | covered | — | STM-07 |
| BS-STMT-024 | `PRINT` (or `?`) followed by items separated by `,` or `;`; a trailing `;` or `,` is allowed. | PS §PRINT item list; SS | baseline | documented | `print_statement` | `BS-STMT-024: PRINT separators and trailing semicolon`<br>`BS-STMT-024: question-mark PRINT with separators`<br>`BS-STMT-024: PRINT with a trailing comma` | n/a | covered | — | STM-08 |
| BS-STMT-025 | PRINT items may be adjacent without a separator (`print "a " 5 "!!"`, `print tab(5)"x";tab(25)"y"`, `print tab(40) pos(0)`). | PS §PRINT item list | baseline | documented | `print_statement` | `BS-STMT-025: adjacent PRINT items`<br>`BS-STMT-025: TAB and POS items` | n/a | covered | — | STM-08, AMB-17 |
| BS-STMT-026 | PRINT item boundaries: an item extends as far as the expression grammar allows (`print a -1` is one item `a - 1`; `print a (1)` is a call). | L1 silent | unknown | provisional | `print_statement` precedence | `BS-STMT-026: ambiguous adjacent PRINT items` | n/a | covered | — | AMB-17 |
| BS-STMT-027 | `GOTO label`. | PS §GOTO label; SS | baseline | documented | `goto_statement` | `BS-STMT-027: GOTO a label` | n/a | covered | — | STM-10 |
| BS-STMT-028 | GOTO with a line number. | PS §GOTO label (prose mentions a line number, no form) | unknown | unresolved | none | n/a — unresolved | n/a | none | — | AMB-31 |
| BS-STMT-029 | `END` terminates execution. | PS §END; SS | baseline | documented | `end_statement` | `BS-STMT-029: END statement` | n/a | covered | — | STM-11, AMB-25 |
| BS-STMT-030 | `STOP`. | PS §STOP; SS | baseline | documented | `stop_statement` | `BS-STMT-030: STOP statement` | n/a | covered | — | STM-12 |
| BS-STMT-031 | `LIBRARY "path"` at the top of a file (`Library "v30/bslCore.brs"`). | CA §Script libraries; EH §Handling only some errors | baseline | documented | `library_statement` | `BS-STMT-031: LIBRARY at the top of a file` | n/a | covered | — | STM-16 |
| BS-STMT-032 | LIBRARY is accepted wherever a statement is accepted; placement rules are not grammar. | L1 silent on placement | unknown | provisional | `library_statement` in `statement` | `BS-STMT-032: LIBRARY after a function declaration` | n/a | covered | — | STM-16, AMB-19 |
| BS-STMT-033 | A file is a sequence of statements: declarations, LIBRARY, directives and ordinary statements are all accepted at file level. | CA §Scope (named functions are global); L1 silent on statements outside functions | unknown | provisional | `source_file` | `BS-STMT-033: statements at file level` | n/a | covered | — | FUN-06, AMB-27 |
| BS-STMT-034 | `LET` statement. | RW only | unknown | unresolved | none | n/a — unresolved | n/a | none | — | ASN-04, AMB-23 |
| BS-STMT-035 | The headers of block IF, FOR, FOR EACH, WHILE, TRY and CATCH may end with `:` instead of a line end, so such a body may be written on one line with colons (FUNCTION and SUB: BS-FUNC-010). Non-normative. | Level 4: BrighterScript @ `01a359c6` `src/parser/Parser.ts` `block()` starts with `consumeStatementSeparators(true)`; `whileStatement()` and `tryCatchStatement()` consume separators before their blocks; no error diagnostic; L1 shows the form only for FUNCTION | unknown | tolerated | `block` starts with `_terminator` | `BS-STMT-035: one-line loop and TRY bodies with colons`<br>`BS-STMT-035: FOR EACH header ending with a colon` | n/a | covered | — | AMB-08. Changes no documented tree. |
| BS-STMT-036 | A block terminator closes only its own construct: `END IF`/`ENDIF` an IF, `END FOR`/`NEXT` a FOR or FOR EACH, `END WHILE` a WHILE, `END TRY`/`ENDTRY` a TRY, `END FUNCTION` a function, `END SUB` a sub; the compact forms of BS-STMT-020 and BS-FUNC-003 likewise. | PS (each statement defines its terminator) | baseline | documented | per-construct terminator tokens | `BS-STMT-036: nested blocks close with their own terminators`<br>`BS-STMT-036: compact terminators close their own constructs` | `BS-STMT-036: END IF closing a FOR body` (recovery)<br>`BS-STMT-036: END SUB closing a FUNCTION` (recovery) | covered | — | KR-005 (`docs/validation/known-regressions.md`). The recovery inputs lack the terminator PS documents for their construct; BrighterScript's `mismatchedEndCallableKeyword` error is reference only. |
| BS-STMT-037 | EXIT/CONTINUE inside a matching loop, GOTO target existence, label scope and reachability. | PS; CA §Scope | baseline | out-of-scope | none | `BS-STMT-037: EXIT FOR outside a loop is not rejected` (guard) | n/a | none | — | AMB-35 |
| BS-STMT-038 | Runtime meaning of statements: FOR bound evaluation, enumeration order, PRINT zones and number formatting, TAB/POS behaviour, END/STOP effects. | PS | baseline | out-of-scope | none | n/a | n/a | none | — | — |
| BS-STMT-039 | `PRINT` (or `?`) with no items. Non-normative. | Level 4: BrighterScript @ `01a359c6` `src/parser/Parser.ts` `printStatement()` ("print statements can be empty") with no error diagnostic; L1 silent | unknown | tolerated | `print_statement` | `BS-STMT-039: PRINT with no items` | n/a | covered | — | AMB-17. Changes no documented tree. |
| BS-STMT-040 | A PRINT (or `?`) item list that begins with a separator or holds two separators in a row (`print , a`, `? ;a`, `print a,,b`, `print a;;b`, `print ;`); separators produce no node. Non-normative. | Level 4: BrighterScript @ `01a359c6` `src/parser/Parser.ts` `printStatement()` accepts any sequence of `,`, `;` and expressions with no error diagnostic; L1 shows separators only between items and after the last one (PS §PRINT item list) | unknown | tolerated | `print_statement` | `BS-STMT-040: leading and repeated PRINT separators` | n/a | covered | — | AMB-17, S04-D2. Changes no documented tree. |

### FUNC

| ID | Requirement | Evidence | Since | Status | Grammar | Positive fixtures | Negative / recovery fixtures | Coverage | KL | Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| BS-FUNC-001 | Named function: `FUNCTION name(parameters) [AS type]`, body, `END FUNCTION`. | PS §FUNCTION(…) AS type / END FUNCTION; SS | baseline | documented | `function_declaration` | `BS-FUNC-001: function with typed parameters and return type`<br>`BS-FUNC-001: function without parameters` | `BS-FUNC-001: function missing END FUNCTION` (recovery) | covered | — | FUN-01 |
| BS-FUNC-002 | Named sub: `SUB name(parameters)`, body, `END SUB`; same node type as a function. | PS §FUNCTION (last paragraph); RW | baseline | documented | `function_declaration` | `BS-FUNC-002: sub declaration` | n/a | covered | — | FUN-02 |
| BS-FUNC-003 | Compact `ENDFUNCTION` and `ENDSUB` (reserved words). | RW (membership only) | unknown | provisional | `kw('endfunction')`, `kw('endsub')` | `BS-FUNC-003: ENDFUNCTION and ENDSUB` | n/a | covered | — | AMB-03 |
| BS-FUNC-004 | An `AS` return type on SUB. | none | unknown | unresolved | none | n/a — unresolved | n/a | none | — | FUN-02, AMB-26. BrighterScript (Level 4, `src/parser/Parser.ts` `functionDeclaration()` @ `01a359c6`) parses `as <type>` after SUB as after FUNCTION; not adopted, since the grammar has no rule for it. |
| BS-FUNC-005 | Parameters: zero or more, comma-separated, each `name [= default] [AS type]`; a default may reference earlier parameters (`b=a+5 as Integer`). | PS §FUNCTION(…) | baseline | documented | `parameter_list`, `parameter` | `BS-FUNC-005: parameters with defaults and types` | n/a | covered | — | FUN-03 |
| BS-FUNC-006 | A line break after a comma in a parameter list. | CA §Attribute operator (example function declaration) | baseline | documented | `parameter_list` | `BS-FUNC-006: parameter list continued after a comma` | n/a | covered | — | LEX-05, LINE-05 |
| BS-FUNC-007 | Line breaks after `(` and before `)` in a parameter list. | L1 shows a line break only after a comma (BS-FUNC-006) | unknown | unresolved | none | n/a — unresolved | n/a | none | — | AMB-07 |
| BS-FUNC-008 | Once a parameter has a default value, every following parameter needs one. | PS §FUNCTION(…) | baseline | out-of-scope | none | `BS-FUNC-008: default-parameter order is not enforced` (guard) | n/a | none | — | FUN-03, AMB-35 |
| BS-FUNC-009 | Anonymous function `FUNCTION (parameters) [AS type]`, body, `END FUNCTION`, usable wherever an expression is. | PS §Anonymous functions, §FUNCTION(…) heading | baseline | documented | `anonymous_function` | `BS-FUNC-009: anonymous function assigned to a variable`<br>`BS-FUNC-009: anonymous function as an associative-array value` | n/a | covered | — | FUN-05 |
| BS-FUNC-010 | One-line bodies with `:` (`FUNCTION explode() : THROW "Kaboom!" : END FUNCTION`, `function():return m.xml@title:end function`). | EVT §Optional chaining operators › Notes; CA §Attribute operator, §"m" the BrightScript "this pointer" | baseline | documented | `block` | `BS-FUNC-010: one-line function bodies` | n/a | covered | — | FUN-05, LEX-04 |
| BS-FUNC-011 | Anonymous `SUB (parameters)`, body, `END SUB`, same node type as an anonymous function. Non-normative. | Level 4: BrighterScript @ `01a359c6` `src/parser/Parser.ts` `anonymousFunction()` accepts `sub` and `function` alike with no error diagnostic; L1 shows only `function` | unknown | tolerated | `anonymous_function` | `BS-FUNC-011: anonymous sub` | n/a | covered | — | AMB-22. Changes no documented tree. |
| BS-FUNC-012 | Named declarations nested inside a body. | CA §Scope (named functions are global) | unknown | unresolved | none added — the shared statement list accepts them | n/a — unresolved | n/a | none | — | FUN-06, AMB-27 |
| BS-FUNC-013 | `m` is an ordinary identifier. | PS §FUNCTION; CA §"m" the BrightScript "this pointer" | baseline | documented | `identifier` | `BS-FUNC-013: m used as an identifier` | n/a | covered | — | FUN-08 |
| BS-FUNC-014 | Function semantics: scope, `m` binding, no closures, Void returns, unused-variable `_` tagging (11.0), stack depth (16.0), function-count limit (5.0). | PS; EVT §Types; CA §Scope; RN | baseline | out-of-scope | none | n/a | n/a | none | — | FUN-06, VER-02, VER-05, VER-21, VER-25 |

### ARRAY

| ID | Requirement | Evidence | Since | Status | Grammar | Positive fixtures | Negative / recovery fixtures | Coverage | KL | Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| BS-ARRAY-001 | Array literal: `[]`, or comma-separated elements (literals or expressions, nesting allowed) on one line. | EVT §Array literals | baseline | documented | `array_literal` | `BS-ARRAY-001: empty, flat and nested array literals` | `BS-ARRAY-001: array literal missing its closing bracket` (recovery) | covered | — | LIT-11 |
| BS-ARRAY-002 | Multi-line array literal: line breaks after `[`, between elements (with or without commas) and before `]`. | EVT §Array literals | baseline | documented | `array_literal` | `BS-ARRAY-002: multi-line array without commas`<br>`BS-ARRAY-002: multi-line array with commas` | n/a | covered | — | LIT-11, LINE-05 |
| BS-ARRAY-003 | A trailing comma before `]`, on the same line or before the closing line break. Empty elements (`[1,,2]`) have no contractual behaviour. Non-normative. | Level 4: BrighterScript @ `01a359c6` `src/parser/Parser.ts` `arrayLiteral()` stops at `]` after a separator with no error diagnostic; L1 silent | unknown | tolerated | `array_literal` | `BS-ARRAY-003: trailing comma in array literals` | n/a | covered | — | ARR-04, AMB-07. Changes no documented tree. |
| BS-ARRAY-004 | `DIM name[d1, …, dk]` with expression dimensions. | PS §DIM (examples); SS; EVT §Array operator | baseline | documented | `dim_statement` | `BS-ARRAY-004: DIM with one and several dimensions` | n/a | covered | — | STM-09, ARR-01 |
| BS-ARRAY-005 | `DIM name(d1, …, dk)`, the form of the PS §DIM heading, gives the same node as the bracket form. | PS §DIM (heading; its examples use brackets) | baseline | documented | `dim_statement` | `BS-ARRAY-005: DIM with parentheses` | n/a | covered | — | AMB-18 |
| BS-ARRAY-006 | Several declarators in one DIM (`dim a[1], b[2]`). | none | unknown | unresolved | none | n/a — unresolved | n/a | none | — | AMB-18 |
| BS-ARRAY-007 | A comma-separated index list `a[1,2,3]` is one index access with three indexes; it is not rewritten to `a[1][2][3]` (their equivalence is semantic). | EVT §Array operator; PS §DIM | baseline | documented | `index_expression` | `BS-ARRAY-007: multiple indexes in one access` | n/a | covered | — | EXP-04, ARR-02 |
| BS-ARRAY-008 | Array semantics: sizing, growth, `roArray` creation, enumeration. | PS §DIM; EVT §Array operator | baseline | out-of-scope | none | n/a | n/a | none | — | ARR-01 |
| BS-ARRAY-009 | In a multi-line array literal, a comma that starts a line (comma-first: a line `, 2` after a line `1`). | none — L1 multi-line examples put commas at line ends or use none (EVT §Array literals) | unknown | unresolved | none — `_sep` places a comma only directly after an element | n/a — unresolved | n/a | none | — | S04-D6. Yields `ERROR` today, which is not contractual. BrighterScript (Level 4) `arrayLiteral()` @ `01a359c6` also reports an error (reference only). |

### AA

| ID | Requirement | Evidence | Since | Status | Grammar | Positive fixtures | Negative / recovery fixtures | Coverage | KL | Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| BS-AA-001 | Associative-array literal: `{}` or `{ }`, or comma-separated `key: value` entries on one line; keys are identifiers; values are any expression including anonymous functions. | EVT §Associative array literals; PS §Anonymous functions | baseline | documented | `associative_array_literal`, `associative_array_entry` | `BS-AA-001: empty and one-line associative arrays`<br>`BS-AA-001: anonymous functions as values` | `BS-AA-001: associative array missing its closing brace` (recovery) | covered | — | LIT-12 |
| BS-AA-002 | String-literal keys (`{ "Jane Doe": 1001 }`). | EVT §Associative array literals; RN §Roku OS 7.0 | 7.0 | documented | `associative_array_entry` | `BS-AA-002: string keys` | n/a | covered | — | LIT-12, VER-09 |
| BS-AA-003 | Multi-line associative array: line breaks after `{`, between entries (with or without commas) and before `}`. | EVT §Associative array literals; PS §FUNCTION (`obj = { add: add … }`) | baseline | documented | `associative_array_literal` | `BS-AA-003: multi-line associative array without commas`<br>`BS-AA-003: multi-line associative array with commas` | n/a | covered | — | LIT-12, LINE-05 |
| BS-AA-004 | A trailing comma before `}`, on the same line or before the closing line break. Empty entries (`{a:1,,b:2}`) have no contractual behaviour. Non-normative. | Level 4: BrighterScript @ `01a359c6` `src/parser/Parser.ts` `aaLiteral()` stops at `}` after a separator with no error diagnostic; L1 silent | unknown | tolerated | `associative_array_literal` | `BS-AA-004: trailing comma in associative arrays` | n/a | covered | — | ARR-04, AMB-07. Changes no documented tree. |
| BS-AA-005 | Duplicate keys, key case folding (identifier keys lower-cased; quoted keys case-preserving since Roku OS 8) and lookup semantics. | EVT §Dot operator; RN §Roku OS 8 | baseline | out-of-scope | none | `BS-AA-005: duplicate keys are not rejected` (guard) | n/a | none | — | ARR-03, VER-15 |
| BS-AA-006 | In a multi-line associative array, a comma that starts a line (comma-first), and a line break between an entry's `:` and its value (`x:` on one line, `1` on the next). | none — L1 multi-line examples put commas at line ends or use none and keep each entry on one line (EVT §Associative array literals) | unknown | unresolved | none — `_sep` places a comma only directly after an entry; an entry has no line break | n/a — unresolved | n/a | none | — | S04-D6. Yields `ERROR` today, which is not contractual. BrighterScript (Level 4) `aaLiteral()` @ `01a359c6` also reports errors for both (reference only). |

### ERR

| ID | Requirement | Evidence | Since | Status | Grammar | Positive fixtures | Negative / recovery fixtures | Coverage | KL | Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| BS-ERR-001 | `TRY`, body, `CATCH variable`, body, `END TRY` or `ENDTRY`; bodies may be empty. | PS §TRY / CATCH variable / END TRY; RN §Roku OS 9.4 | 9.4 | documented | `try_statement`, `catch_clause` | `BS-ERR-001: TRY with CATCH`<br>`BS-ERR-001: empty TRY and CATCH bodies with ENDTRY` | `BS-ERR-001: TRY missing END TRY` (recovery) | covered | — | ERR-01, ERR-04, VER-18 |
| BS-ERR-002 | TRY statements nest inside TRY and CATCH bodies. | PS §Nested TRY/CATCH statements | 9.4 | documented | `try_statement` | `BS-ERR-002: nested TRY in TRY and CATCH bodies` | n/a | covered | — | ERR-01 |
| BS-ERR-003 | A CATCH clause without a simple variable: no variable, an index, a member, a numeric or string literal, or an expression. | PS §TRY / CATCH variable / END TRY (listed as not legal) | 9.4 | invalid | `catch_clause` | n/a | `BS-ERR-003: CATCH without a variable`<br>`BS-ERR-003: CATCH with an index`<br>`BS-ERR-003: CATCH with a member`<br>`BS-ERR-003: CATCH with a literal`<br>`BS-ERR-003: CATCH with an expression` | covered | — | ERR-01. PS calls its literal example (`CATCH 22`) a "literal constant". The literal words `true`, `false`, `invalid` and `LINE_NUM` are also reserved words; as the CATCH variable they are a reserved word used as a name (BS-LEX-023) and parse as an `identifier` (S04-M8). |
| BS-ERR-004 | `THROW expression` (string, associative-array literal, variable). | PS §THROW expression; EH §Throwing exceptions | 9.4 | documented | `throw_statement` | `BS-ERR-004: THROW forms` | n/a | covered | — | ERR-02 |
| BS-ERR-005 | `TRY` is a keyword at the start of a statement in a file or block statement list, and `CATCH` at such a start directly inside a TRY body; elsewhere both are identifiers, including `catch = 1` inside other bodies and `try = 1` in a single-line IF branch. `THROW` is a keyword at statement start; `throw` elsewhere has no contractual behaviour. | PS §TRY / CATCH ("not keywords … reserved identifiers"), §THROW ("is a keyword") | 9.4 | provisional | contextual `kw('try')`, `kw('catch')`, `kw('throw')`; `_try_body` | `BS-ERR-005: try and catch as identifiers`<br>`BS-ERR-005: try as an identifier in a single-line branch` | n/a | covered | — | ERR-03, AMB-02. Statement-initial `try` as a name is rejected (Known incompatibilities). |
| BS-ERR-006 | TRY without CATCH. | PS schematic always shows CATCH | unknown | unresolved | none — the grammar requires CATCH | n/a — unresolved | n/a | none | — | AMB-33 |
| BS-ERR-007 | Exception object fields, re-throw, `ERR_USER`/`ERR_BAD_THROW`, uncatchable STOP, the minimum-OS declaration, and the rule that a GOTO label may not appear between TRY and CATCH. | PS §TRY / CATCH, §THROW; EH | 9.4 | out-of-scope | none | `BS-ERR-007: label inside a TRY body is not rejected` (guard) | n/a | none | — | ERR-05, ERR-06, AMB-35 |

### COND

| ID | Requirement | Evidence | Since | Status | Grammar | Positive fixtures | Negative / recovery fixtures | Coverage | KL | Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| BS-COND-001 | `#const name = value` where value is `true`, `false` or a constant name. | CC (introduction) | unknown | documented | `const_directive` | `BS-COND-001: #const forms` | n/a | covered | — | CC-01, CC-04, VER-27 |
| BS-COND-002 | `#if condition` … `#end if`, the condition a constant name, `true` or `false`. Conditions are never evaluated; every branch is parsed as BrightScript (baseline, ADR-0004), except a literal-`false` branch, which is `inactive_text` (BS-COND-007). | CC §Uses, §Undefined constants | unknown | documented | `if_directive` | `BS-COND-002: #if around statements`<br>`BS-COND-002: #if true and #if name bodies are code` | `BS-COND-002: #if missing #end if` (recovery) | covered | — | CC-02, VER-27 |
| BS-COND-003 | `#else if condition` and `#else` branches. | CC §Uses | unknown | documented | `else_if_directive`, `else_directive` | `BS-COND-003: #else if and #else branches` | n/a | covered | — | CC-02 |
| BS-COND-004 | `#error message`; the message is free text to the end of the line. | CC §Uses | unknown | documented | `error_directive`, `error_message` | `BS-COND-004: #error with free text` | n/a | covered | — | CC-03 |
| BS-COND-005 | Directive words and constant names in any letter case. | CC §Criteria; SS | unknown | documented | directive tokens | `BS-COND-005: directives in mixed case` | n/a | covered | — | CC-04, LEX-01 |
| BS-COND-006 | Directives at file level, wrapping function declarations and statements. | CC §Block comments (declaration), §Undefined constants (statement) | unknown | documented | `if_directive` in `statement` | `BS-COND-006: #if around function declarations` | n/a | covered | — | CC-07, CC-08 |
| BS-COND-007 | Block-comment idiom: a literal-`false` branch whose content is not BrightScript. Represented per the ADR-0004 spike: PASS → `inactive_text`; FAIL → known limitation KL-001. Fixture expectations for both outcomes are in the workload matrix. | CC §Block comments; ADR-0004 | unknown | documented | `if_directive` + `inactive_text` (spike-gated) | `BS-COND-007: block comment with prose`<br>`BS-COND-007: commented-out function`<br>`BS-COND-007: spike S3 case variants of #if false`<br>`BS-COND-007: spike S4 #if falsey is code`<br>`BS-COND-007: spike S5 comment after #if false`<br>`BS-COND-007: spike S6 #else after a false branch`<br>`BS-COND-007: spike S7 #else if after a false branch`<br>`BS-COND-007: spike S8 nested block inside a false region`<br>`BS-COND-007: spike S9 directives inside a false region`<br>`BS-COND-007: spike S10 quotes and comments inside a false region`<br>`BS-COND-007: spike S11 #else if false`<br>`BS-COND-007: spike S12 REM-like prose inside a false region`<br>`BS-COND-007: directive-like words inside a false region` | `BS-COND-007: spike R1 error before a false region` (recovery)<br>`BS-COND-007: spike R2 error after a false region` (recovery)<br>`BS-COND-007: spike R3 false region without #end if` (recovery) | covered | — | CC-07, AMB-20. Spike result: PASS with design V1 (ADR-0004); KL-001 retired unused. |
| BS-COND-008 | A directive on its own line may be indented (CC §Uses shows an indented `#error`); `#const`, `#if`, `#else if`, `#else` and `#end if` may be followed by a comment; `#` is immediately followed by the directive word; the two words of `#else if`/`#end if` may be separated by spaces or tabs. A directive that shares its line with a statement (before or after a `:`) has no contractual behaviour. | CC §Uses (indentation); otherwise L1 silent | unknown | provisional | directive tokens | `BS-COND-008: indented directives with comments`<br>`BS-COND-008: comments after #const, #else if and #else` | n/a | covered | — | CC-08, AMB-21. L1 shows directives only on lines of their own and does not state that they must be (S04-D3). Directives are statements (grammar-design §6), so `x = 1 : #const a = true` parses without an error and `x = 1 #const a = true` with one. |
| BS-COND-009 | Compact `#elseif`/`#endif`, whitespace between `#` and the word, operators or parentheses in conditions (`#if not DEBUG`), expressions in `#const`, constant names that begin with a digit. | none; `#if not` was observed only in a Level 4 test description; CC §Criteria names the characters of a constant name (BS-COND-014) but not whether the first may be a digit | unknown | unresolved | none | n/a — unresolved | n/a | none | — | CC-02, CC-04, AMB-21; candidate "`#if not NAME`". Designators on constant names: BS-COND-014. |
| BS-COND-010 | Directives inside expressions or literals, and statements split across branch boundaries. | ADR-0004 consequences | unknown | unresolved | none | n/a — unresolved | n/a | none | — | AMB-20 |
| BS-COND-011 | Condition evaluation, manifest `bs_const`, undefined constants evaluating to `false` (since 16.0; earlier a compile error), redefinition, `#error` failing compilation. | CC §Criteria, §Undefined constants, §Manifest constant; RN §Roku OS 16.0 | baseline | out-of-scope | none | n/a | n/a | none | — | CC-05, CC-06, VER-24 |
| BS-COND-012 | Directives inside function and block bodies, and conditional blocks nested in conditional blocks. | L1 silent (CC examples are at file level) | unknown | provisional | `if_directive` in `statement` | `BS-COND-012: #if inside a function body`<br>`BS-COND-012: nested #if blocks` | n/a | covered | — | CC-08, AMB-21 |
| BS-COND-013 | `#const` with a number or string value (`#const x = 5`, `#const s = "a"`). | CC §Criteria ("This initial release only supports boolean constant values") | unknown | invalid | `const_directive` value is `identifier`, `true` or `false` | n/a | `BS-COND-013: #const with a non-boolean value`<br>`BS-COND-013: #const with a string value` | covered | — | CC-01, AMB-21. Operators or expressions in `#const` stay BS-COND-009. `#const x = invalid` and `#const x = LINE_NUM` parse with the word as a constant name, a reserved word used as a name (BS-LEX-023, S04-M8). |
| BS-COND-014 | A constant name consists of alphanumeric characters and `_` only, so a name carrying a type designator (`#const x$ = true`, `#if x$`) is not a valid constant name. Compile-time rule; the shared identifier token accepts a designator on a constant name. | CC §Criteria (constant names are made of alphanumeric characters and, optionally, `_`) | unknown | out-of-scope | none — `identifier` carries the designator (BS-LEX-017) | n/a | n/a | none | — | S04-D1. Treated like function-name designators (BS-LEX-019): rejecting it needs a second name token beside `identifier` (grammar-design §3), and rejecting every program the compiler rejects is a non-goal (grammar-contract). `#const x$ = true` parses without an error. |
| BS-COND-015 | `#error` with no message text (nothing, or only spaces and tabs, after the word); the `error_directive` has no `message`. Non-normative. | Level 4: BrighterScript @ `01a359c6` `src/lexer/Lexer.ts` (the `#error` case adds no message token when the rest of the line is empty) and `src/preprocessor/PreprocessorParser.ts` `hashError()`, with no parse diagnostic; L1 shows `#error` only with a message (CC §Uses) | unknown | tolerated | `error_directive` (optional `message`) | `BS-COND-015: #error without a message` | n/a | covered | — | S04-D2. Changes no documented tree. Failing compilation when the branch is active is evaluation (BS-COND-011). |

## Registry summary

| Area | Rows | documented | provisional | tolerated | unresolved | invalid | out-of-scope |
|---|---|---|---|---|---|---|---|
| LEX | 35 | 18 | 9 | 1 | 4 | 1 | 2 |
| LIT | 20 | 15 | 3 | 0 | 2 | 0 | 0 |
| TYPE | 3 | 1 | 0 | 0 | 1 | 0 | 1 |
| EXP | 27 | 18 | 2 | 0 | 4 | 2 | 1 |
| STMT | 40 | 20 | 7 | 5 | 5 | 1 | 2 |
| FUNC | 14 | 7 | 1 | 1 | 3 | 0 | 2 |
| ARRAY | 9 | 5 | 0 | 1 | 2 | 0 | 1 |
| AA | 6 | 3 | 0 | 1 | 1 | 0 | 1 |
| ERR | 7 | 3 | 1 | 0 | 1 | 1 | 1 |
| COND | 15 | 7 | 2 | 1 | 2 | 1 | 2 |
| **Total** | **176** | **97** | **25** | **10** | **25** | **6** | **13** |

The `tolerated` rows cite Level 4 evidence only (grammar-contract §3.3); none
changes a documented tree, and each is non-normative.

## Known incompatibilities

The grammar follows the current documentation (ADR-0003). Older meanings of
the same text:

| Text | Older or alternative reading | Current parse | Basis | Requirement |
|---|---|---|---|---|
| `IF x?("Hello")` ending its line | single-line IF printing `Hello` (older firmware) | block IF with an optional call | L1 states the change | BS-LEX-032 |
| statement-initial `try`, `throw` in a file or block statement list used as names (`try = 1`, `throw = 1`), and `throw` at the start of a single-line IF branch | identifiers (before Roku OS 9.4; L1 asks such code to be rewritten) | statement keywords, so the line is an error | provisional choice | BS-ERR-005, BS-LEX-025 |
| statement-initial `continue`, `library` in a file or block statement list used as names, and `continue` at the start of a single-line IF branch | identifiers (L1 says nothing about these words as names) | statement keywords, so the line is an error | provisional choice | BS-LEX-025 |

## Reconciliation

### Official sources → requirements

| Page | Sections inspected | Requirements derived | Sections excluded (reason) |
|---|---|---|---|
| LR | whole page | none | overview and authority statement only |
| SS | statement list; case note; colon note and examples | BS-LEX-001, 002, 005, 009, 010, 013, 031; BS-STMT-007, 018, 024, 027, 029, 030; BS-FUNC-001; BS-ARRAY-004; BS-COND-005 | — |
| PS | DIM; variable = expression; END; STOP; GOTO label; RETURN; FOR; FOR EACH; WHILE; CONTINUE; TRY / CATCH; Nested TRY/CATCH; THROW; REM; IF (single line); Block IF; PRINT item list (TAB, POS); FUNCTION; Anonymous functions | BS-LEX-002, 004, 005, 009, 010, 012, 013, 017, 021, 022, 025, 027; BS-TYPE-001; BS-EXP-001; BS-STMT-001, 003, 005, 007, 010, 012, 013, 015–019, 023–025, 027–030, 036–038; BS-FUNC-001, 002, 005, 008, 009, 013, 014; BS-ARRAY-004, 005, 007, 008; BS-AA-001, 003; BS-ERR-001–007 | exception-object and backtrace tables, Maximum stack depth, `m` binding paragraphs, print zones and number formatting (runtime; BS-ERR-007, BS-FUNC-014, BS-STMT-038) |
| EVT | Identifiers; Types; Comments › In BrightScript; Literals (string, numeric, source, function, array, associative array); Type declaration characters; Operators table; Function call, Dot, Array, Optional chaining (Notes, Support details), Exponentiation, Negation, Multiplicative, Additive, Increment and decrement, Mathematical and bitshift assignment, Integer bitshift, Comparison, Logical and bitwise, `=` operator | BS-LEX-001, 009, 012, 013, 015–019, 021, 024–026, 029–032, 035; BS-LIT-001–005, 007–009, 011–013, 015–017, 019, 020; BS-TYPE-002, 003; BS-EXP-001–005, 007–021, 026; BS-STMT-001–003, 005, 008; BS-FUNC-010, 014; BS-ARRAY-001, 002, 004, 007, 008; BS-AA-001–003, 005 | Comments › In XML (XML files); Dynamic vs. object types, Type conversion, Effects of type conversions (runtime; BS-TYPE-003); lookup case rules (BS-AA-005); short-circuit evaluation and operator results (BS-EXP-026) |
| RW | reserved-word list | BS-LEX-021–023, 025; BS-LIT-019; BS-STMT-020, 021, 034; BS-FUNC-002, 003 | — |
| CC | introduction; Criteria; Undefined constants; Defining a constant; Manifest constant; Uses; Block comments | BS-LEX-001, 009; BS-COND-001–008, 011, 012 | manifest syntax and evaluation rules (BS-COND-011) |
| EH | Catching and handling; The backtrace; Throwing exceptions; Invalid throws; Re-throwing; Reacting to an error without handling it; Handling only some errors; Miscellaneous examples | BS-LEX-024; BS-LIT-005, 008; BS-STMT-007, 031; BS-ERR-004, 007 | exception object, error number, backtrace fields, custom fields (runtime; BS-ERR-007); console and crash-dump transcripts (not source) |
| RN | all 44 release sections | `since` values of BS-LEX-018, 029, 030; BS-LIT-011, 016; BS-EXP-007–010, 014, 016; BS-STMT-002, 003, 019; BS-AA-002; BS-ERR-001–005; version notes of BS-TYPE-001, BS-COND-011, BS-FUNC-014 and BS-AA-005 | component, SceneGraph, media, DRM, tooling and platform entries (not language) |
| CA | Use of wrapper functions on intrinsic types; Dot operator; Attribute operator; Scope; "m" the BrightScript "this pointer"; Creating and using intrinsic objects; Script libraries | BS-LEX-004, 025, 027, 033; BS-LIT-012, 014; BS-TYPE-003; BS-EXP-004, 006, 012, 022, 026, 027; BS-STMT-005, 007, 031, 033, 037; BS-FUNC-006, 010, 012–014 | component model, intrinsic types and object types, statements working with interfaces, garbage collection, events, threading, XML namespaces, bslCore function list (runtime or API) |
| RF | all function sections | BS-LEX-022; BS-LIT-005, 019 | function behaviour, deprecations (API) |

Official code that is not valid source as printed and is never used as a
fixture: PS §WHILE `print "loop once".` (trailing period); RF §Run
`BreakIfRunError(LINE_NUM)     stop` (two statements without a separator); CA
§Attribute operator adjacent operands (BS-EXP-022); EVT §Identifiers bare
identifier list (`a`, `boy5`, `super_man$`); elisions and placeholders (PS
§CONTINUE `...`, the PS block-IF outline's `statements`, EVT §Logical
`then ...` and `IF aa?.foo THEN ...`, CA §Scope `.....`); fragments (EH §The
backtrace from `CATCH e`, which parses inside a TRY, and RF
`&hFC==ERR_NORMAL_END`); the SS list of statement types; program output and
console transcripts in PS §PRINT item list, CA, EH, RF (`20`) and RN 7.1
(`a from ' {...}`); the XML data listings in CA.

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
| LEX-05 | combined | BS-LEX-005, BS-EXP-023, 024, BS-FUNC-006, 007, BS-ARRAY-002, BS-AA-003 |
| LEX-06 | promoted | BS-LEX-012, 013 |
| LEX-07 | promoted | BS-LEX-015, 016, 026 |
| LEX-08 | promoted | BS-LEX-017, 018, 019, 020 |
| LEX-09 | promoted | BS-LEX-021, 022, 023 |
| LEX-10 | promoted | BS-LEX-025 |
| LEX-11 | promoted | BS-LEX-027, 028 |
| LEX-12 | combined | BS-LEX-029, BS-EXP-006, 011–019, BS-STMT-002 |
| LEX-13 | promoted | BS-LEX-031, 032, 035 |
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
| EXP-08 | promoted | BS-EXP-012, 027 |
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
| STM-08 | promoted | BS-STMT-024, 025, 026, 039 |
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
| ARR-04 | tolerated | BS-ARRAY-003, BS-AA-004 |
| ERR-01 | promoted | BS-ERR-001, 003, 006 |
| ERR-02 | promoted | BS-ERR-004 |
| ERR-03 | provisional | BS-ERR-005 |
| ERR-04 | combined | `since` of BS-ERR-001–005 |
| ERR-05 | out-of-scope | BS-ERR-007 |
| ERR-06 | out-of-scope | BS-ERR-007 |
| CC-01 | promoted | BS-COND-001, 013 |
| CC-02 | promoted | BS-COND-002, 003, 009 |
| CC-03 | promoted | BS-COND-004 |
| CC-04 | promoted | BS-COND-005 |
| CC-05 | out-of-scope | BS-COND-011 |
| CC-06 | out-of-scope | BS-COND-011 |
| CC-07 | promoted | BS-COND-007 |
| CC-08 | promoted | BS-COND-006, 008, 012 |
| LINE-01 | combined | BS-LEX-005, 006 |
| LINE-02 | duplicate | of LEX-04 |
| LINE-03 | promoted | BS-LEX-009 |
| LINE-04 | provisional | BS-LEX-008 |
| LINE-05 | combined | BS-ARRAY-002, BS-AA-003, BS-FUNC-006, BS-EXP-024 |
| LINE-06 | promoted | BS-LEX-033, 034 |

| Disposition | Items |
|---|---|
| promoted | 75 |
| combined | 8 |
| duplicate | 7 |
| out-of-scope | 6 |
| provisional | 2 |
| unresolved | 3 |
| tolerated | 1 |
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
| AMB-02 | BS-LEX-025, BS-ERR-005 | PS keyword notes; RW omissions | keyword recognition | PROVISIONAL-GRAMMAR-CHOICE | non-reserved syntax words are contextual; the TRY body is a separate rule so `catch` is a keyword only there | yes |
| AMB-03 | BS-STMT-010, 020, 021, 022; BS-FUNC-003; BS-ERR-001 | RW compact words; PS `ENDIF`, `ELSEIF`, `ENDTRY` | terminator tokens | PROVISIONAL-GRAMMAR-CHOICE | documented and reserved compact words accepted; `ENDFOR`/`EXITFOR`/`FOREACH` not; `END X` terminators are single tokens, other multi-word forms separate tokens | yes |
| AMB-04 | BS-STMT-007, 008, 011 | PS optional THEN; EVT comment case | IF form selection | PROVISIONAL-GRAMMAR-CHOICE | token after condition decides the form | yes |
| AMB-05 | BS-STMT-009 | SS colon example | single-line IF shape | PROVISIONAL-GRAMMAR-CHOICE | nearest-IF ELSE; defined inline statement set | yes |
| AMB-06 | BS-STMT-013, 014 | PS bare NEXT | terminator | RESOLVED-DOCUMENTED | bare NEXT accepted; `NEXT var` has no rule (unresolved) | yes (`NEXT var` only) |
| AMB-07 | BS-LEX-005–008, BS-EXP-023, 024, BS-FUNC-006, 007, BS-ARRAY-002, 003, BS-AA-003, 004 | multi-line literals; one parameter-list example | line model | PROVISIONAL-GRAMMAR-CHOICE | newlines are tokens, allowed inside literals and after a parameter-list comma; breaks in argument lists and after operators have no rule; trailing commas tolerated | yes |
| AMB-08 | BS-LEX-010, 011, 027, 028; BS-STMT-035 | label definition; colon separator | label and separator shape | PROVISIONAL-GRAMMAR-CHOICE | labels end their line; separator runs tolerated | yes |
| AMB-09 | BS-LEX-015–020 | identifier rules; designator table | identifier token | PROVISIONAL-GRAMMAR-CHOICE | designator is part of the identifier token everywhere | yes |
| AMB-10 | BS-LIT-004–014 | numeric examples | number token | PROVISIONAL-GRAMMAR-CHOICE | planned `number` token shape | yes |
| AMB-11 | BS-LIT-015–018, BS-LEX-033, 034 | only `""` documented | string token, encoding | PROVISIONAL-GRAMMAR-CHOICE | no escapes other than `""`; UTF-8 | yes |
| AMB-12 | BS-LEX-013, 014 | REM prose | comment token | PROVISIONAL-GRAMMAR-CHOICE | whole-word REM followed by space, tab or line end | yes |
| AMB-13 | BS-EXP-011–021, 027 | precedence table and prose | precedence | PROVISIONAL-GRAMMAR-CHOICE | official order; postfix level includes `@`; prefix operators as right operands | yes (`@`, postfix, prefix-right only) |
| AMB-14 | BS-STMT-002 | RN 7.1 list, EVT examples | compound operators | RESOLVED-DOCUMENTED | exactly seven operators | no |
| AMB-15 | BS-STMT-003, 004 | postfix statement examples | update statement | TOLERATED | postfix statement on variables (documented) and on member and index targets (Level 4) | yes |
| AMB-16 | BS-LEX-029–032, 035, BS-EXP-007–010 | EVT notes and support details | `?` tokenization | RESOLVED-DOCUMENTED | indivisible tokens + context-aware lexing; `?[` at statement start is provisional | yes (edge spellings) |
| AMB-17 | BS-STMT-024–026, 039 | PRINT prose and examples | PRINT list | PROVISIONAL-GRAMMAR-CHOICE | maximal-munch items; empty PRINT tolerated | yes |
| AMB-18 | BS-ARRAY-004–006 | heading vs examples | DIM | PROVISIONAL-GRAMMAR-CHOICE | brackets and parentheses; one declarator | yes |
| AMB-19 | BS-STMT-031, 032 | one top-of-file example | top-level shape | PROVISIONAL-GRAMMAR-CHOICE | LIBRARY is an ordinary statement | yes |
| AMB-20 | BS-COND-007 | block-comment idiom | CC body shape | PROVISIONAL-GRAMMAR-CHOICE (spike-gated) | ADR-0004 spike decides; FAIL ⇒ KNOWN-LIMITATION KL-001. Decided: PASS (V1) | no (design decision) |
| AMB-21 | BS-COND-001–005, 008, 009, 012, 013 | documented spellings only | directive tokens | PROVISIONAL-GRAMMAR-CHOICE | documented spellings; conditions are names or booleans; directives placed like statements | yes |
| AMB-22 | BS-FUNC-011 | Sub shortcut prose | anonymous sub | TOLERATED | accepted on Level 4 evidence, same node as anonymous function | yes |
| AMB-23 | BS-STMT-034 | RW only | none | FUTURE-L2 | no rule | yes |
| AMB-24 | BS-LEX-022, 023 | RW only | none | OUT-OF-SCOPE | `ObjFun` is an ordinary identifier | yes (reservation only) |
| AMB-25 | BS-STMT-029 | PS END | END vs END X | RESOLVED-DOCUMENTED | two-word terminators are single tokens; `end` alone is `end_statement` | no |
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
| PROVISIONAL-GRAMMAR-CHOICE | 20 | 1 |
| TOLERATED | 2 | 0 |
| OUT-OF-SCOPE | 5 | 0 |
| KNOWN-LIMITATION | 0 (KL-001 retired: the AMB-20 spike passed) | 0 |
| FUTURE-L2 | 4 | 1 |
| **Total** | **35** | **2** |

Where the requirements of one entry have different statuses, the disposition
names the governing choice and the behaviour column names the `tolerated` or
`unresolved` parts.

### Versioned changes → `since`

From `_ref/normative/roku-docs/notes/versioned-language-changes.md`; every
version below was re-checked against the release-notes snapshot.

| Research label | Roku OS | Change | Kind | Requirements / disposition |
|---|---|---|---|---|
| VER-01 | 3.0 | typed values in parameters and returns | runtime semantic (the syntax predates it) | BS-TYPE-001 `since` baseline |
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
| VER-27 | not stated | conditional compilation introduced | syntax | BS-COND-001–008, 012, 013 `since` unknown |
| VER-28 | not stated | `Eval` deprecated | API | none |
| VER-29 | not stated | `Run` deprecated | API | none; name covered by BS-LEX-022 |

Syntax-relevant entries: 13 (VER-06–12, 18–20, 22, 26, 27), all mapped. No
semantic change is implemented as a parser mode.

Correction to the research note: VER-01 was classified there as a parser
syntax change. The Roku OS 3.0 compatibility note says return statements that
return "a different type than specified in the function declaration" may have
run in v2.0, so declared types existed before 3.0; the `AS` syntax therefore has
no established boundary (`baseline`) and VER-01 is a semantic change. All other
entries agree with the snapshot.
