# Workload matrix

The validation sets the first implementation must build and run, and the
catalogue of every corpus fixture named in the registry
([language-conformance.md](../specs/language-conformance.md)). Levels V0–V10
and gates are defined in [validation.md](validation.md); planned node names in
[tree-schema.md](../specs/tree-schema.md); rule design in
[grammar-design.md](../specs/grammar-design.md).

Nothing here has been run: there is no grammar yet.

## Workload sets

| Set | Level | Inputs | Pass criterion | Bounds |
|---|---|---|---|---|
| W01 corpus | V2, V3 | every file under `test/corpus/` (catalogue below) | every fixture passes; each registry fixture exists exactly once; `:error` only on negative, recovery and KL fixtures; `:skip` only on a fixture citing a `KL-NNN` | whole run ≤ 60 s |
| W02 byte-sensitive | V2, V3 | `test/corpus/bytes/` (CRLF, mixed endings, BOM, final newline) | as W01; trees equal their LF counterparts | — |
| W03 composite samples | V3, V6, V10 | `test/samples/*.brs`, independently written programs (below) | no `ERROR`/`MISSING`; recorded in V6 | ≤ 1 s each |
| W04 precedence | V3 | fixtures of BS-EXP-002, 011–021 and every grouping case of grammar-design §5 | groupings exactly as listed | — |
| W05 equivalent spellings | V3 | pairs below | the two trees are identical after removing anonymous nodes and byte ranges | — |
| W06 nesting, length, repetition | V10 | generated inputs below | valid inputs: no `ERROR`; all inputs: no crash, no hang | per input ≤ 10 s, ≤ 1 GiB resident |
| W07 UTF-8 | V3, V10 | BS-LEX-033 fixtures; samples with non-ASCII strings and comments; invalid UTF-8 and NUL bytes (robustness only) | valid: no `ERROR`; invalid bytes: no crash | — |
| W08 recovery | V3, V10 | recovery and negative fixtures (catalogue) | `:error` holds; no crash; no hang | — |
| W09 conditional compilation | V3, V5 | BS-COND fixtures; spike inputs S1–S11, R1–R3, E1–E6 (grammar-design §11) | baseline fixtures pass; spike decided PASS or FAIL by the ADR-0004 criteria | — |
| W10 incremental edits | V5 | edit scripts below | incremental tree equals the fresh parse of the edited text (same S-expression and byte ranges) | — |
| W11 highlights | V4 | `queries/highlights.scm`, `test/highlight/*.brs` | query compiles; every capture assertion passes | — |
| W12 native oracle | V6 | all corpus inputs and `test/samples/*.brs` | output recorded per identity (validation.md identity binding) | — |
| W13 fuzz and pathological | V10 | `tree-sitter fuzz` over the corpus; W06 inputs; seeds below | no crash, no hang, no runaway memory | fuzz: 1,000 iterations × 10 edits per fixture at release candidates |
| W14 downstream parity | V9 (in `go-treesitter`) | W12 inputs and W10 edits for the same grammar identity | ordered trees equal the native V6 records; `CGO_ENABLED=0` build and tests pass | run only when that work is authorized |

### W03 composite samples

Independently written; no text copied from Roku pages or other parsers.

| File | Must contain |
|---|---|
| `program.brs` | LIBRARY; functions and subs with typed and default parameters; anonymous functions and subs; every statement kind; single-line and block IFs with ELSE IF and ELSE; FOR with STEP, FOR EACH, WHILE, EXIT, CONTINUE, NEXT; labels and GOTO; DIM; PRINT with `,`, `;`, adjacency, TAB and POS; TRY/CATCH/THROW (nested); every literal form; every operator level; optional chaining; `@`; multi-line arrays and AAs with comments; `#const`, `#if`/`#else if`/`#else`, `#error`; `'` and REM comments |
| `program-crlf.brs` | byte copy of `program.brs` with CRLF endings, marked `-text` |
| `compact.brs` | colon-separated one-line bodies, compact terminators (`endif`, `endwhile`, `exitwhile`, `endfunction`, `endsub`, `endtry`, `elseif`), keyword case variants, `?` PRINT forms |

### W05 equivalent-spelling pairs

| Pair | Requirement |
|---|---|
| `IF x THEN PRINT 1` / `if x then print 1` | BS-LEX-001 |
| `print 1` / `? 1` | BS-LEX-031, BS-STMT-024 |
| `end if` / `endif` / `end   if` | BS-STMT-010, 022 |
| `else if` / `elseif` | BS-STMT-010 |
| `end for` / `next` | BS-STMT-013 |
| `end while` / `endwhile`; `exit while` / `exitwhile` | BS-STMT-020 |
| `end function` / `endfunction`; `end sub` / `endsub` | BS-FUNC-003 |
| `end try` / `endtry` | BS-ERR-001 |
| `' x` / `REM x` | BS-LEX-012, 013 |
| `dim a[5]` / `dim a(5)` | BS-ARRAY-005 |
| LF file / CRLF file | BS-LEX-006 |

### W06 generated inputs

Produced by a deterministic generator script committed with the
implementation; the files themselves are not committed.

| Input | Size |
|---|---|
| array literal, one element per line | 10,000 elements |
| AA literal, one entry per line | 5,000 entries |
| one line of colon-separated assignments | 2,000 statements |
| block IF with ELSE IF clauses | 1,000 clauses |
| nested IF / FOR / WHILE / TRY | depth 100 each |
| nested parentheses | depth 500 |
| postfix chain `a.b.c…` with calls and indexes | 2,000 links |
| string literal | 1 MiB |
| file of functions | 50,000 lines |
| unterminated constructs (IF, FOR, AA, string, `#if`) at EOF | 1 each (robustness only) |

### W10 incremental edit scripts

Each script names a base fixture, applies the edits with
`tree-sitter parse --edits` and compares the result with a fresh parse of the
edited text.

| Script | Base | Edits |
|---|---|---|
| I01 | `BS-LEX-009: blank lines around and inside blocks` | insert a character inside an identifier; delete it |
| I02 | `BS-LEX-005: one statement per line` | delete the newline between two statements; re-insert it |
| I03 | `BS-LEX-010: colon-separated statements` | insert `:` between tokens; remove a `:` |
| I04 | `BS-STMT-007: single-line IF with THEN` | delete the statement after THEN (block form); re-insert it |
| I05 | `BS-STMT-010: block IF with ELSE IF and ELSE` | delete `end if`; re-insert it; delete the `ELSE IF` line |
| I06 | `BS-LIT-016: doubled quotation marks` | insert `""` inside a string; delete one `"` |
| I07 | `BS-LEX-012: apostrophe comment lines` | insert `'` at the start of a code line; remove it |
| I08 | `BS-LEX-014: identifiers beginning with rem` | change `remark` to `rem ark` and back |
| I09 | `BS-EXP-007: optional chaining chain` | delete and re-insert each `?` |
| I10 | `BS-AA-003: multi-line associative array with commas` | remove a comma; join two entry lines; split them again |
| I11 | `BS-LEX-006: mixed LF and CRLF line endings` | replace one `\r\n` with `\n` and back |
| I12 | `BS-COND-002: #if around statements` | delete `#end if`; re-insert it |
| E1–E6 | spike inputs | as listed in grammar-design §11 |

### W11 highlight captures

Capture names are taken from the Tree-sitter CLI default theme (Level 3,
`crates/cli/src/highlight.rs` @ `v0.27.0`). `test/highlight/*.brs` asserts at
least one instance of every row.

| Syntax | Capture |
|---|---|
| `comment`; `inactive_text` (spike PASS only) | `@comment` |
| `string`; `error_message` | `@string`; `@string.special` |
| `number` | `@number` |
| `true`, `false`, `invalid`, `source_literal` | `@constant.builtin` |
| statement, block and directive keywords (`if then else elseif end endif for each in to step next while endwhile exit exitwhile continue return print ? dim goto stop library try catch endtry throw function sub endfunction endsub as #const #if #else #end #error`) | `@keyword` |
| operators, including `and or not mod` and optional-chaining tokens | `@operator` |
| `type` | `@type.builtin` |
| `function_declaration` name; called identifier or member property of a `call_expression` | `@function` |
| call of a reserved callable name (BS-LEX-022, case-insensitive match) | `@function.builtin` |
| `parameter` name | `@variable.parameter` |
| `member_expression` property; identifier AA key | `@property` |
| `attribute_expression` attribute | `@attribute` |
| `label_statement` name; `goto_statement` label; `const_directive` name; directive condition identifier | `@constant` |
| identifier `m` | `@variable.builtin` |
| other identifiers | `@variable` |
| `( ) [ ] { }` | `@punctuation.bracket` |
| `, ; : .` | `@punctuation.delimiter` |

### W13 pathological seeds

Bare CR line endings (BS-LEX-007); non-ASCII identifiers (BS-LEX-016); NUL
bytes and invalid UTF-8 (BS-LEX-034); lone `"`, `#`, `?`, `&h`; 10,000 `(`;
10,000 `:`; `#if` without `#end if`; every unresolved form listed in the
registry. Only the robustness criterion applies to them.

## Corpus fixture catalogue

One row per registry fixture. Notation inside inputs: `↵` line feed, `␍`
carriage return, `⇥` tab, `‹BOM›` the bytes EF BB BF; every other character is
literal. The runner strips one final newline, so an input ends without one
unless its last character is `↵`. Expected trees use planned node names; a
fixture's full S-expression is written from the planned schema and must match
exactly. `:error` marks negative and recovery fixtures; they assert only that
an error is present (validation fixture rules). Corpus expectations show only
named nodes, so a fixture whose requirement is carried by an anonymous token
is marked **(cst)** and uses the `:cst` attribute, which prints the concrete
tree including anonymous tokens (Level 3, "Writing Tests"; present in every
eligible generator).

### `test/corpus/lexical.txt`

| Fixture | Input | Expected |
|---|---|---|
| `BS-LEX-001: keywords in upper, lower and mixed case` | `IF x THEN PRINT "a"↵if x then print "a"↵If X Then Print "A"` | three `if_statement`s of identical shape: `condition: (identifier)`, `consequence: (block (print_statement (string)))` |
| `BS-LEX-001: identifier spellings differing only in case` | `myVar = 1↵MYVAR = 2↵myvar = 3` | three `assignment_statement`s with `left: (identifier)` |
| `BS-LEX-002: indentation and repeated spaces` | `sub main()↵    x   =   1↵        print    x↵end sub` | `function_declaration` whose `block` holds `assignment_statement`, `print_statement` |
| `BS-LEX-003: tab indentation and tabs between tokens` | `sub main()↵⇥x⇥=⇥1↵end sub` | same shape as the previous fixture |
| `BS-LEX-004: keyword directly followed by a string` | `if c <> k then print"error" : stop` | `if_statement` whose `consequence` block holds `print_statement (string)` and `stop_statement` |
| `BS-LEX-004: compact one-line anonymous function` | `photo.GetTitle=function():return m.xml@title:end function` | `assignment_statement left: (member_expression) right: (anonymous_function body: (block (return_statement value: (attribute_expression object: (member_expression) attribute: (identifier)))))` |
| `BS-LEX-005: one statement per line` | `x = 1↵y = 2↵print x + y` | `assignment_statement`, `assignment_statement`, `print_statement (binary_expression)` |
| `BS-LEX-008: final line without a line terminator` | `x = 1` | `(source_file (assignment_statement …))` |
| `BS-LEX-008: final line with a line terminator` | `x = 1↵` | same tree as the previous fixture |
| `BS-LEX-008: empty file` | (empty) | `(source_file)` |
| `BS-LEX-008: only comments and blank lines` | `' a↵↵REM b↵` | `(source_file (comment) (comment))` |
| `BS-LEX-009: blank lines around and inside blocks` | `↵↵sub main()↵↵  x = 1↵↵end sub↵↵` | one `function_declaration` whose `block` holds one `assignment_statement` |
| `BS-LEX-010: colon-separated statements` | `x=5:print 25; " is"; x^2` | `assignment_statement`, `print_statement` with `number`, `string`, `binary_expression` |
| `BS-LEX-010: colon-separated statements in a block body` | `sub main()↵  a = 1 : b = 2 : print a↵end sub` | `block` holding two `assignment_statement`s and a `print_statement` |
| `BS-LEX-011: repeated, leading and trailing colons` | `: x = 1 :: y = 2 :` | two `assignment_statement`s, no other named node |
| `BS-LEX-012: apostrophe comment lines` | `' first↵'second↵x = 1` | `comment`, `comment`, `assignment_statement` |
| `BS-LEX-012: comment after code on the same line` | `x = 1 ' set x↵y = 2'no space` | `assignment_statement`, `comment`, `assignment_statement`, `comment` |
| `BS-LEX-012: apostrophe inside a string` | `s = "don't stop"` | `assignment_statement right: (string)`; no `comment` |
| `BS-LEX-013: REM comments in mixed case` | `REM upper↵rem lower↵Rem ** mixed **` | three `comment`s |
| `BS-LEX-013: bare REM line` | `x = 1↵REM↵y = 2` | `assignment_statement`, `comment`, `assignment_statement` |
| `BS-LEX-014: identifiers beginning with rem` | `remark = 1↵rem1 = 2↵rem_x = remark + rem1` | three `assignment_statement`s; no `comment` |
| `BS-LEX-014: REM after code and after a colon` | `x = 1 rem note↵y = 2 : REM note` | `assignment_statement`, `comment`, `assignment_statement`, `comment` |
| `BS-LEX-015: identifier forms` | `a = boy5 + super_man$ + _x + a_very_long_identifier_name_123` | `binary_expression`s over four `identifier`s |
| `BS-LEX-017: variables with type designators` | `a = 1 : a$ = "s" : a% = 2 : a! = 1.5 : a# = 2.5` | five `assignment_statement`s with `left: (identifier)` |
| `BS-LEX-018: LongInteger designator on a variable` | `id& = 9876543210&` | `assignment_statement left: (identifier) right: (number)` |
| `BS-LEX-021: reserved keywords in statement positions` | `Function f() As Integer↵  Dim a[2]↵  For i = 1 To 2 Step 1↵    If a[i] = Invalid Then Exit For↵  Next↵  While True : Exit While : End While↵  Goto done↵done:↵  Return 1↵End Function` | `function_declaration` whose `block` holds `dim_statement`, `for_statement` (with `if_statement` → `exit_statement`), `while_statement` (→ `exit_statement`), `goto_statement`, `label_statement`, `return_statement` |
| `BS-LEX-022: reserved built-in function calls` | `o = CreateObject("roList")↵t = Type(o)↵b = Box(1)↵g = GetGlobalAA()↵e = GetLastRunCompileError()↵print tab(5) pos(0)` | each right side is `call_expression function: (identifier)`; `print_statement` with two `call_expression`s |
| `BS-LEX-024: keywords as member names` | `list.next()↵player.stop()↵x = obj.end + obj.if + obj.print` | two `call_expression` statements over `member_expression property: (identifier)`; `binary_expression`s over three `member_expression`s |
| `BS-LEX-024: keywords as associative-array keys` | `aa = { function: "main()", end: 1, if: 2, next: 3 }` | four `associative_array_entry key: (identifier)` |
| `BS-LEX-025: non-reserved keyword words as identifiers` | `mod = 3↵x = mod + in + as + integer + string↵y = a mod b` | `assignment_statement left: (identifier)`; `binary_expression`s over five `identifier`s; `binary_expression` with operator `mod` |
| `BS-LEX-026: identifiers beginning with keywords` | `iffy = 1 : endpoint = 2 : format = 3 : printer = 4 : nextItem = 5 : stepSize = 6 : notify = 7 : order = 8 : android = 9 : returnValue = 10 : falsey = 11` | eleven `assignment_statement`s with `left: (identifier)` |
| `BS-LEX-033: UTF-8 text in comments and strings` | `' café ☕↵s = "Grüße, 世界"` | `comment`, `assignment_statement right: (string)` |

### `test/corpus/bytes/` (marked `-text`)

| Fixture | Input | Expected |
|---|---|---|
| `BS-LEX-006: CRLF line endings` | `x = 1␍↵y = 2␍↵z = 3` | three `assignment_statement`s, same as LF |
| `BS-LEX-006: mixed LF and CRLF line endings` | `x = 1␍↵y = 2↵z = 3` | three `assignment_statement`s |
| `BS-LEX-033: leading byte-order mark` | `‹BOM›x = 1` | `(source_file (assignment_statement …))`, no `ERROR` |

### `test/corpus/literals.txt`

| Fixture | Input | Expected |
|---|---|---|
| `BS-LIT-001: boolean literals` | `a = true : b = FALSE : c = True` | `right: (true)`, `(false)`, `(true)` |
| `BS-LIT-002: invalid literal` | `if x = invalid then x = INVALID` | condition `binary_expression right: (invalid)`; assignment `right: (invalid)` |
| `BS-LIT-003: decimal integers` | `x = 0 : y = 255 : z = 2147483647` | three `number`s |
| `BS-LIT-004: negative number is unary negation` | `x = -5` | `right: (unary_expression operator: "-" operand: (number))` |
| `BS-LIT-005: hex integers with either prefix case` | `a = &HFF : b = &hFF : c = &h28` | three `number`s |
| `BS-LIT-006: lowercase hex digits` | `a = &hff : b = &hFe` | two `number`s |
| `BS-LIT-007: float literal forms` | `a = 2.01 : b = 1.23456E+30 : c = 2! : d = 125! : e = 1.5E-3` | five `number`s |
| `BS-LIT-008: lowercase unsigned exponent and leading-dot fraction` | `a = 1e1000000 : b = .1 : c = 0.5e3` | three `number`s |
| `BS-LIT-009: double literal forms` | `a = 1.23456789D-12 : b = 2.3# : c = 125#` | three `number`s |
| `BS-LIT-010: lowercase d exponent` | `a = 1.5d-3` | one `number` |
| `BS-LIT-011: LongInteger literals` | `a = 9876543210& : b = &hFEDCBA9876543210&` | two `number`s |
| `BS-LIT-012: integer suffix on a literal` | `a = 125% : b = 100%` | two `number`s |
| `BS-LIT-014: method call on a numeric literal` | `print 5.tostr() + "th"↵if 100%.tostr() <> "100" then stop↵x = (-5).tostr()` | `call_expression function: (member_expression object: (number))`; the same with `100%`; `member_expression object: (parenthesized_expression (unary_expression))` |
| `BS-LIT-014: method call on a string literal` | `x = "5".toint() + 5↵y = "01234567".left(3)` | `member_expression object: (string)` under `call_expression` |
| `BS-LIT-015: string literals` | `a = "this is a string" : b = "" : c = " "` | three `string`s |
| `BS-LIT-016: doubled quotation marks` | `s = """"↵t = "say ""hi"""` | two `string`s |
| `BS-LIT-017: backslash and non-ASCII text in strings` | `p = "C:\path\n"↵q = "naïve ✓"` | two `string`s, no child nodes |
| `BS-LIT-019: LINE_NUM source literal` | `print LINE_NUM↵x = line_num + 1` | `(source_literal)` in both |
| `BS-LIT-020: function name used as a value` | `fivevar = five↵print fivevar()` | `assignment_statement right: (identifier)`; `print_statement (call_expression)` |

### `test/corpus/expressions.txt`

| Fixture | Input | Expected |
|---|---|---|
| `BS-EXP-001: primary expressions` | `x = [a, 1, "s", true, invalid, LINE_NUM, (b), {k: 1}, function() : return 1 : end function]` | `array_literal` holding `identifier`, `number`, `string`, `true`, `invalid`, `source_literal`, `parenthesized_expression`, `associative_array_literal`, `anonymous_function` |
| `BS-EXP-003: call forms` | `print five()↵print fivevar()↵print array[1]()↵obj.add()↵m.f(1, 2)` | `call_expression` with `function:` `identifier`, `identifier`, `index_expression`, `member_expression`, `member_expression` |
| `BS-EXP-004: member access chains` | `i.ifInt.SetInt(5)↵x = (1+2).tostr()↵y = f().a.b` | nested `member_expression`s; `object: (parenthesized_expression)`; `object: (call_expression)` |
| `BS-EXP-005: index access and chained indexing` | `x = a[1]↵y = a[1][2]↵z = f()[0]↵w = a.b[i + 1]` | `index_expression`s, nested in the second, over `call_expression` and `member_expression` objects |
| `BS-EXP-006: attribute operator` | `n = rsp.photos@perpage↵t = m.xml@title` | `attribute_expression object: (member_expression) attribute: (identifier)` |
| `BS-EXP-007: optional chaining chain` | `x = array?[3]?.foo?.bar?()` | (cst) `call_expression (argument_list "?(")` over `member_expression "?."` over `member_expression "?."` over `index_expression "?["` |
| `BS-EXP-007: optional call and optional index with arguments` | `x = i?(1, "String", explode())↵y = i?[explode()]` | (cst) `call_expression` whose `argument_list` starts with `?(` and holds three expressions; `index_expression` with `?[` |
| `BS-EXP-008: optional index as an assignment target` | `array?[12] = x` | `:error` |
| `BS-EXP-008: optional member as an assignment target` | `a?.b = 1` | `:error` |
| `BS-EXP-009: standalone optional call statement` | `f?()` | `:error` |
| `BS-EXP-010: optional chaining inside statement subexpressions` | `f(array?[12])↵f(foo?.bar).member = 5` | call statement with an `index_expression "?["` argument; `assignment_statement left: (member_expression object: (call_expression))` |
| `BS-EXP-024: call arguments across lines` | `f(↵  1,↵  2↵)` | call statement, `argument_list` with two `number`s |
| `BS-EXP-025: postfix operand kinds` | `print "a" (1)↵print x (1)↵y = [1, 2].count()` | `print_statement (string) (parenthesized_expression)`; `print_statement (call_expression)`; `member_expression object: (array_literal)` |
| `BS-LEX-029: optional-chaining tokens after whitespace` | `a = b ?. c↵x = s ?[ 5 ]↵y = f ?( 1 )↵z = e ?@ id` | (cst) `member_expression "?."`, `index_expression "?["`, `call_expression` with `?(`, `attribute_expression "?@"` |
| `BS-LEX-030: split optional-chaining token` | `a = b ? . c` | `:error` |

### `test/corpus/precedence.txt`

| Fixture | Input | Expected grouping |
|---|---|---|
| `BS-EXP-002: parentheses override precedence` | `x = (a + b) * c` | `(a + b) * c` |
| `BS-EXP-011: exponentiation is right associative` | `x = 2^3^2` | `2^(3^2)` |
| `BS-EXP-012: unary minus against postfix and exponent` | `a = -5.tostr()↵b = -2^2↵c = 2^-2` | `-(5.tostr())`; `-(2^2)`; `2^(-2)` |
| `BS-EXP-012: unary operators against multiplication` | `a = -x * y↵b = x * -y↵c = +x` | `(-x) * y`; `x * (-y)`; `+x` |
| `BS-EXP-013: multiplicative operators are left associative` | `x = a / b mod c \ d * e` | `(((a / b) mod c) \ d) * e` |
| `BS-EXP-014: integer division` | `x = 7 \ 2` | `binary_expression` with operator `\` |
| `BS-EXP-015: additive operators against multiplicative` | `x = a + b * c↵y = a - b - c↵s = "a" + b + "c"` | `a + (b * c)`; `(a - b) - c`; `("a" + b) + "c"` |
| `BS-EXP-016: shifts between additive and comparison` | `x = a << b + c↵y = a < b << c↵z = 7 >> 1` | `a << (b + c)`; `a < (b << c)`; `7 >> 1` |
| `BS-EXP-017: comparison operators and chains` | `x = a < b < c↵y = a = b <> c↵z = a <= b and c >= d` | `(a < b) < c`; `(a = b) <> c`; `(a <= b) and (c >= d)` |
| `BS-EXP-018: NOT below comparison and above AND` | `x = not a = b↵y = not a and b↵z = not not a` | `not (a = b)`; `(not a) and b`; `not (not a)` |
| `BS-EXP-019: AND binds tighter than OR` | `x = a or b and c↵y = a or b or c↵z = a = c and not (b > 40)` | `a or (b and c)`; `(a or b) or c`; `(a = c) and (not (b > 40))` |
| `BS-EXP-020: equals inside an expression is comparison` | `x = a = b↵if a=5 then print "a is 5"` | `assignment_statement right: (binary_expression "=")`; condition `binary_expression "="` |
| `BS-EXP-021: mixed postfix chain` | `x = a?.b.c?[0]?(1)↵y = f(1)[2].g(3)` | (cst) `(((a?.b).c)?[0])?(1)`; `((f(1))[2]).g(3)` |
| `BS-EXP-021: attribute operator inside a member chain` | `x = e@y.z↵w = a.b@c` | `(e@y).z`; `(a.b)@c` |

### `test/corpus/statements.txt`

| Fixture | Input | Expected |
|---|---|---|
| `BS-STMT-001: assignment to variables, members and indexes` | `a$ = "a rose"↵aa.newkey = "v"↵array[2] = "two"↵c[x, y, z] = k↵f(x).y = 1` | `left:` `identifier`; `member_expression`; `index_expression`; `index_expression` with three `index`; `member_expression object: (call_expression)` |
| `BS-STMT-002: compound assignment operators` | `x+=1↵x-=1↵x*=3↵x/=2↵x\=2↵x<<=8↵x>>=4` | seven `assignment_statement`s, operators in that order |
| `BS-STMT-003: increment and decrement statements` | `x++↵x--↵counter++` | three `update_statement`s with `operand: (identifier)` |
| `BS-STMT-004: increment and decrement on member and index targets` | `a.b++↵a[0]--` | `update_statement operand: (member_expression)`; `operand: (index_expression)` |
| `BS-STMT-005: call statements` | `HandleButton(msg.GetInt())↵cavemen.push("fred")↵m.top.observeField("x", "onX")` | three `call_expression` statements |
| `BS-STMT-023: RETURN with and without a value` | `function f()↵  if x then return↵  return 1↵end function` | `return_statement` without `value`; `return_statement value: (number)` |
| `BS-STMT-024: PRINT separators and trailing semicolon` | `print 25; " is equal to"; x^2↵print "zone 1","zone 2"↵print a$;a$,a$;" ";a$↵print "no newline";` | four `print_statement`s with 3, 2, 5 and 1 expression children |
| `BS-STMT-024: question-mark PRINT with separators` | `? 25; " is"; x^2` | `print_statement` with three expression children |
| `BS-STMT-025: adjacent PRINT items` | `print "this is a five " 5 "!!"` | `print_statement (string) (number) (string)` |
| `BS-STMT-025: TAB and POS items` | `print tab(5)"tabbed 5";tab(25)"tabbed 25"↵print tab(40) pos(0)↵print "these" tab(pos(0)+5)"words"` | items alternate `call_expression` and `string` as written |
| `BS-STMT-026: ambiguous adjacent PRINT items` | `print a -1↵print a (1)↵print "a" (1)` | one `binary_expression`; one `call_expression`; `string` then `parenthesized_expression` |
| `BS-STMT-026: PRINT with no items` | `print↵?` | two `print_statement`s without children |
| `BS-STMT-027: GOTO a label` | `start:↵goto start` | `label_statement name: (identifier)`, `goto_statement label: (identifier)` |
| `BS-STMT-029: END statement` | `if done then end↵end` | `if_statement` with `(block (end_statement))`; `end_statement` |
| `BS-STMT-030: STOP statement` | `if x then stop↵stop` | `if_statement` with `(block (stop_statement))`; `stop_statement` |
| `BS-STMT-031: LIBRARY at the top of a file` | `Library "v30/bslCore.brs"↵sub main()↵end sub` | `library_statement path: (string)`, `function_declaration` |
| `BS-STMT-032: LIBRARY after a function declaration` | `sub a()↵end sub↵LIBRARY "v30/bslCore.brs"` | `function_declaration`, `library_statement` |
| `BS-STMT-033: statements at file level` | `x = 1↵print x↵sub main()↵end sub↵if x then y = 2` | `assignment_statement`, `print_statement`, `function_declaration`, `if_statement` under `source_file` |
| `BS-STMT-037: EXIT FOR outside a loop is not rejected` | `exit for` | `(source_file (exit_statement))` (guard) |
| `BS-LEX-027: label line` | `sub main()↵mylabel:↵  print "here"↵  goto mylabel↵end sub` | `block` holding `label_statement`, `print_statement`, `goto_statement` |
| `BS-LEX-028: label followed by a comment` | `start: ' entry point↵goto start` | `label_statement`, `comment`, `goto_statement` |
| `BS-LEX-031: question-mark PRINT alias forms` | `?("Hello")↵?.1↵?[1]↵? "x"` | `print_statement (parenthesized_expression (string))`; `(number)`; `(array_literal (number))`; `(string)` |

### `test/corpus/if.txt`

| Fixture | Input | Expected |
|---|---|---|
| `BS-STMT-007: single-line IF with THEN` | `if x > 127 then print "out of range"` | `if_statement condition: (binary_expression) consequence: (block (print_statement (string)))` |
| `BS-STMT-007: single-line IF without THEN` | `if debug print "timeout"` | same shape with `condition: (identifier)` |
| `BS-STMT-007: single-line IF with ELSE` | `if caveman = "fred" then print "flintstone" else print "rubble"` | `alternative: (else_clause body: (block (print_statement)))` |
| `BS-STMT-007: colon-separated statements in a single-line branch` | `if myname="fred" then yourname = "barney" : ? yourname` | `consequence` block holding `assignment_statement` and `print_statement` |
| `BS-STMT-008: THEN followed by a comment starts a block IF` | `if x then ' comment↵  y = 1↵end if` | block-form `if_statement` with `consequence: (block (assignment_statement))` and a `comment` |
| `BS-STMT-008: THEN followed by a colon starts a block IF` | `if x then : y = 1 : end if` | block-form `if_statement` with `consequence: (block (assignment_statement))` |
| `BS-STMT-009: nested single-line IF with ELSE` | `if a then if b then x = 1 else x = 2` | outer `if_statement` without `alternative`; its `consequence` holds the inner `if_statement` with `alternative: (else_clause)` |
| `BS-STMT-009: single-line ELSE IF nests an IF` | `if a then x = 1 else if b then x = 2 else x = 3` | outer `alternative: (else_clause body: (block (if_statement alternative: (else_clause))))` |
| `BS-STMT-010: block IF with ELSE IF and ELSE` | `if n < 0 then↵  throw "negative"↵else if n = 0 then↵  return 1↵else↵  return n * f(n-1)↵end if` | `if_statement` with `consequence`, `alternative: (else_if_clause)`, `alternative: (else_clause)` |
| `BS-STMT-010: ELSEIF and ENDIF spellings` | `if a then↵  x = 1↵elseif b then↵  x = 2↵endif` | `if_statement` with `alternative: (else_if_clause)` |
| `BS-STMT-010: block IF without THEN` | `if msg.isFullResult()↵  return 9↵end if` | block-form `if_statement condition: (call_expression)` |
| `BS-STMT-011: ELSE and ELSE IF headers followed by comments and colons` | `if a then↵  x = 1↵else if b then ' second↵  x = 2↵else : x = 3↵end if` | `else_if_clause` with a following `comment`; `else_clause body: (block (assignment_statement))` |
| `BS-LEX-032: IF with an optional call starts a block IF` | `IF x?("Hello")↵  PRINT "Hi"↵END IF` | (cst) block-form `if_statement condition: (call_expression function: (identifier) arguments: (argument_list "?(" (string)))` |

### `test/corpus/loops.txt`

| Fixture | Input | Expected |
|---|---|---|
| `BS-STMT-012: FOR with and without STEP` | `for i = 10 to 1 Step -1↵  print i↵end for↵for j = 1 to n↵end for` | `for_statement counter start end step: (unary_expression) body`; second without `step` |
| `BS-STMT-013: NEXT terminates FOR and FOR EACH` | `for i=10 to 1 step -1↵  print i↵next↵for each n in aa↵  print n;aa[n]↵next` | `for_statement`, `for_each_statement` |
| `BS-STMT-015: FOR EACH over an expression` | `for each caveman in cavemen↵  print caveman↵end for↵for each k in m.getList()↵end for` | `for_each_statement item: (identifier) collection:` `identifier`, then `call_expression` |
| `BS-STMT-016: WHILE loop` | `while k = 0↵  k = 1↵end while` | `while_statement condition: (binary_expression) body: (block (assignment_statement))` |
| `BS-STMT-017: WHILE terminated by NEXT` | `while x↵  x = x - 1↵next` | `:error` |
| `BS-STMT-018: EXIT FOR and EXIT WHILE` | `for i = 1 to 3↵  if i = 2 then exit for↵end for↵while true↵  exit while↵end while` | two `exit_statement`s |
| `BS-STMT-019: CONTINUE FOR and CONTINUE WHILE` | `for each fruit in fruits↵  if fruit = "lemon" then continue for↵end for↵while c < 3↵  c++↵  continue while↵end while` | two `continue_statement`s |
| `BS-STMT-020: ENDWHILE and EXITWHILE` | `while true↵  exitwhile↵endwhile` | `while_statement body: (block (exit_statement))` |
| `BS-STMT-022: multi-word keywords with extra spacing` | `for each⇥x in xs↵  if x then↵  end   if↵end⇥for` | `for_each_statement` whose body holds an `if_statement` |
| `BS-STMT-035: one-line loop and TRY bodies with colons` | `for i = 1 to 3 : print i : end for↵while x : x = x - 1 : end while↵try : f() : catch e : print e : end try` | `for_statement`, `while_statement`, `try_statement` with one statement per body |
| `BS-STMT-036: nested blocks close with their own terminators` | `for i = 1 to 2↵  if x then↵    while y↵      y = false↵    end while↵  end if↵end for` | `for_statement` → `if_statement` → `while_statement`, nested in that order |

### `test/corpus/functions.txt`

| Fixture | Input | Expected |
|---|---|---|
| `BS-TYPE-001: parameter and return type names` | `function f(a as integer, b as Float, c as DOUBLE, d as boolean, e as string, f as object, g as dynamic, h as function) as void↵end function` | eight `parameter type: (type)`; `return_type: (type)` |
| `BS-FUNC-001: function with typed parameters and return type` | `function add(a as Integer, b as Integer) as Integer↵  return a+b↵end function` | `function_declaration name parameters: (parameter_list (parameter) (parameter)) return_type: (type) body` |
| `BS-FUNC-001: function without parameters` | `function five() as Integer↵  return 5↵end function↵function Main()↵end function` | two `function_declaration`s with empty `parameter_list`s |
| `BS-FUNC-002: sub declaration` | `sub main()↵  print "x"↵end sub` | `function_declaration` |
| `BS-FUNC-003: ENDFUNCTION and ENDSUB` | `function f()↵endfunction↵sub g()↵endsub` | two `function_declaration`s |
| `BS-FUNC-005: parameters with defaults and types` | `function add3(a as Integer, b=a+5 as Integer) as Integer↵  return a+b↵end function↵sub s(x = 1, y = "a")↵end sub` | `parameter name default: (binary_expression) type: (type)`; `parameter default: (number)`, `parameter default: (string)` |
| `BS-FUNC-006: parameter list continued after a comma` | `function helper(http as Object, xmllist as Object,↵    owner=invalid as dynamic) as Object↵  return invalid↵end function` | `parameter_list` with three `parameter`s |
| `BS-FUNC-007: parameter list opened and closed on separate lines` | `sub f(↵  a,↵  b↵)↵end sub` | `parameter_list` with two `parameter`s |
| `BS-FUNC-008: default-parameter order is not enforced` | `function f(a = 1, b)↵end function` | `function_declaration`, no `ERROR` (guard) |
| `BS-FUNC-009: anonymous function assigned to a variable` | `myfunc = function (a, b)↵  return a+b↵end function↵print myfunc(1,2)` | `assignment_statement right: (anonymous_function)`; `print_statement (call_expression)` |
| `BS-FUNC-009: anonymous function as an associative-array value` | `q = {↵  starring : function(o, e)↵    return 0↵  end function↵}` | `associative_array_entry value: (anonymous_function)` |
| `BS-FUNC-010: one-line function bodies` | `FUNCTION explode() : THROW "Kaboom!" : END FUNCTION↵FUNCTION x(_) : RETURN TRUE : END FUNCTION↵obj = { Get : function() : return m.Value : end function }` | two `function_declaration`s with one-statement bodies; `anonymous_function` value |
| `BS-FUNC-011: anonymous sub` | `cb = sub (x)↵  print x↵end sub` | `assignment_statement right: (anonymous_function)` |
| `BS-FUNC-013: m used as an identifier` | `function add() as void↵  m.result = m.a + m.b↵end function` | `member_expression object: (identifier)` for each `m` |

### `test/corpus/collections.txt`

| Fixture | Input | Expected |
|---|---|---|
| `BS-ARRAY-001: empty, flat and nested array literals` | `myarray = []↵myarray = [ 1, 2, 3 ]↵myarray = [ x+5, true, 1<>2, ["a","b"] ]` | `array_literal` with 0, 3 and 4 children, the last holding an `array_literal` |
| `BS-ARRAY-002: multi-line array without commas` | `a = [↵  "able"↵  "baker"↵]` | `array_literal (string) (string)` |
| `BS-ARRAY-002: multi-line array with commas` | `a = [↵  3.1415,↵  2.71828↵]` | `array_literal (number) (number)` |
| `BS-ARRAY-003: trailing comma in array literals` | `a = [1, 2,]↵b = [↵  1,↵  2,↵]` | two `array_literal`s with two `number`s each |
| `BS-ARRAY-004: DIM with one and several dimensions` | `Dim array[5]↵dim c[5, 4, 6]↵dim d[n + 1]` | `dim_statement name` with 1, 3 and 1 `dimension` |
| `BS-ARRAY-005: DIM with parentheses` | `dim a(5, 4)` | `dim_statement name: (identifier) dimension: (number) dimension: (number)` |
| `BS-ARRAY-007: multiple indexes in one access` | `item = array[1,2,3]↵item = array[1][2][3]` | one `index_expression` with three `index`; three nested `index_expression`s |
| `BS-AA-001: empty and one-line associative arrays` | `aa = { }↵aa = {}↵aa = { key1: "value", key2: 55, key3: 5+3 }` | `associative_array_literal` with 0, 0 and 3 entries |
| `BS-AA-001: anonymous functions as values` | `obj = {↵  Set : function(x) : m.Value = x : end function↵  Value : 0↵}` | two entries; the first `value: (anonymous_function)` |
| `BS-AA-002: string keys` | `aa = { "Jane Doe": 1001, "John Doe": 1002 }` | two entries with `key: (string)` |
| `BS-AA-003: multi-line associative array without commas` | `aa = {↵  Myfunc1: aFunction↵  Myval1: "the value"↵}` | two entries |
| `BS-AA-003: multi-line associative array with commas` | `aa = {↵  alpha: 1,↵  zulu: 26↵}` | two entries |
| `BS-AA-004: trailing comma in associative arrays` | `aa = { a: 1, }↵bb = {↵  a: 1,↵  b: 2,↵}` | one and two entries |
| `BS-AA-005: duplicate keys are not rejected` | `aa = { a: 1, a: 2 }` | two entries, no `ERROR` (guard) |

### `test/corpus/error-handling.txt`

| Fixture | Input | Expected |
|---|---|---|
| `BS-ERR-001: TRY with CATCH` | `try↵  print 1/0↵catch e↵  print "Division failed: ", e↵end try` | `try_statement body handler: (catch_clause variable: (identifier) body)` |
| `BS-ERR-001: empty TRY and CATCH bodies with ENDTRY` | `try↵catch e↵endtry` | `try_statement` with statement-free blocks |
| `BS-ERR-002: nested TRY in TRY and CATCH bodies` | `try↵  try↵    x = 1↵  catch e↵  end try↵catch e↵  try↵    print e.message↵  catch e2↵  end try↵end try` | inner `try_statement`s in the outer `body` and in the `catch_clause` body |
| `BS-ERR-003: CATCH without a variable` | `try↵catch↵end try` | `:error` |
| `BS-ERR-003: CATCH with an index` | `try↵catch someArray[23]↵end try` | `:error` |
| `BS-ERR-003: CATCH with a member` | `try↵catch bill.ted↵end try` | `:error` |
| `BS-ERR-003: CATCH with a literal` | `try↵catch 22↵end try` | `:error` |
| `BS-ERR-003: CATCH with an expression` | `try↵catch a+wave↵end try` | `:error` |
| `BS-ERR-004: THROW forms` | `throw "Cannot calculate."↵THROW {number: ERR_DIV_ZERO, message: "Division by zero"}↵throw e` | `throw_statement value:` `string`, `associative_array_literal`, `identifier` |
| `BS-ERR-005: try, catch and throw as identifiers` | `x = try + catch + throw↵catch = 1↵f(try)` | `binary_expression`s over three `identifier`s; `assignment_statement left: (identifier)`; call with an `identifier` argument |
| `BS-ERR-007: label inside a TRY body is not rejected` | `try↵here:↵  x = 1↵catch e↵end try` | `try_statement` whose `body` holds a `label_statement`; no `ERROR` (guard) |

### `test/corpus/conditional-compilation.txt`

| Fixture | Input | Expected |
|---|---|---|
| `BS-COND-001: #const forms` | `#const someFlag = true↵#const anotherFlag = false↵#const someOtherFlag = someFlag` | three `const_directive name value` with `true`, `false`, `identifier` |
| `BS-COND-002: #if around statements` | `#if mylibrary_enable_detailed_logging↵    ? "hello world"↵#end if` | `if_directive condition: (identifier) consequence: (block (print_statement))` |
| `BS-COND-002: #if true and #if name bodies are code` | `#if true↵  x = 1↵#end if↵#if DEBUG↵  y = 2↵#end if` | two `if_directive`s with `assignment_statement` bodies |
| `BS-COND-003: #else if and #else branches` | `#const FeatureA = true↵#if FeatureA↵  'code for Feature A↵#else if FeatureB↵  x = 1↵#else↵  y = 2↵#end if` | `if_directive` with `alternative: (else_if_directive)` and `alternative: (else_directive)` |
| `BS-COND-004: #error with free text` | `#if FeatureAImplemented↵  ' code↵#else↵  #error TO DO: implement feature A, don't forget↵#end if` | `else_directive body: (block (error_directive message: (error_message)))`; the apostrophe is message text |
| `BS-COND-005: directives in mixed case` | `#CONST Flag = TRUE↵#If flag↵  x = 1↵#Else If other↵#ELSE↵#End If` | `const_directive`, `if_directive` with `else_if_directive` and `else_directive` |
| `BS-COND-006: #if around function declarations` | `#if DEBUG↵function debugOnly()↵end function↵#end if` | `if_directive consequence: (block (function_declaration))` |
| `BS-COND-006: nested #if blocks` | `#if A↵  #if B↵    x = 1↵  #end if↵#end if` | `if_directive` → `if_directive` → `assignment_statement` |
| `BS-COND-007: block comment with prose` | `#if false↵    This is a function that does nothing.↵    It takes no parameters.↵#end if↵function foo() as void↵    'do nothing↵end function` | spike PASS: `if_directive condition: (false) consequence: (inactive_text)`, then `function_declaration`; spike FAIL: `:error`, cites KL-001 |
| `BS-COND-007: commented-out function` | `#if false↵    function Order66() as void↵        'code for Order66↵    end function↵#end if` | spike PASS: `consequence: (inactive_text (comment))`; spike FAIL: `consequence: (block (function_declaration))` |
| `BS-COND-008: indented directives with comments` | `sub main()↵    #if DEBUG ' debug only↵        print "d"↵    #else   if   OTHER↵    #end⇥if ' done↵end sub` | `function_declaration` whose `block` holds an `if_directive` with an `else_if_directive`; two `comment`s |

The ADR-0004 spike adds its own inputs S1–S11 and R1–R3 to this file, named
BS-COND-007: spike followed by the input ID (for example BS-COND-007: spike S1); their inputs and expectations are
in grammar-design §11.

### `test/corpus/recovery.txt`

Only the presence of an error is asserted (`:error`).

| Fixture | Input |
|---|---|
| `BS-LIT-015: unterminated string at end of line` | `a = "open↵b = 1` |
| `BS-EXP-002: unclosed parenthesis` | `x = (a + b` |
| `BS-STMT-001: assignment missing its value` | `x =` |
| `BS-STMT-010: block IF missing END IF` | `if x then↵  y = 1` |
| `BS-STMT-012: FOR missing END FOR` | `for i = 1 to 2↵  print i` |
| `BS-STMT-016: WHILE missing END WHILE` | `while true↵  x = 1` |
| `BS-STMT-036: END IF closing a FOR body` | `for i = 1 to 2↵  x = 1↵end if` |
| `BS-FUNC-001: function missing END FUNCTION` | `function f()↵  x = 1` |
| `BS-ARRAY-001: array literal missing its closing bracket` | `a = [1, 2` |
| `BS-AA-001: associative array missing its closing brace` | `aa = { a: 1` |
| `BS-ERR-001: TRY missing END TRY` | `try↵  x = 1↵catch e` |
| `BS-COND-002: #if missing #end if` | `#if DEBUG↵  x = 1` |

## Counts

| Item | Count |
|---|---|
| registry fixtures catalogued | 191 |
| positive (including 4 guards) | 169 |
| negative (`invalid` evidence) | 10 |
| recovery | 12 |
| corpus files | 13 (`bytes/` counted once) |
| spike inputs (added by the spike) | 14 corpus + 6 incremental |
| incremental scripts | 12 + E1–E6 |
| equivalent-spelling pairs | 11 |
| generated inputs | 10 |
| highlight capture rows | 17 |
