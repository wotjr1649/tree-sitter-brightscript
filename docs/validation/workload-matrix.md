# Workload matrix

The validation sets the first implementation must build and run, and the
catalogue of every corpus fixture named in the registry
([language-conformance.md](../specs/language-conformance.md)). Levels V0–V10
and gates are defined in [validation.md](validation.md); planned node names and
placement rules in [tree-schema.md](../specs/tree-schema.md); rule design in
[grammar-design.md](../specs/grammar-design.md).

Every set is automated (see Automation below). Results belong to one grammar
identity and are recorded in the release-candidate report, not here.

## Workload sets

| Set | Level | Inputs | Pass criterion | Bounds |
|---|---|---|---|---|
| W01 corpus | V2, V3 | every file under `test/corpus/` (catalogue below) | every fixture passes; each registry fixture exists exactly once; `:error` only on negative, recovery and KL-demonstrating fixtures; `:skip` only on a fixture listed under a `KL-NNN` | whole run ≤ 60 s |
| W02 byte-sensitive | V2, V3 | `test/corpus/bytes/` (CR bytes, byte-order mark) | as W01; trees equal their LF or BOM-less counterparts | — |
| W03 composite samples | V3, V6, V10 | `test/samples/*.brs`, independently written programs (below) | no error (root has-error state, hidden `MISSING` included); exactly the catalogued files; `program-crlf.brs` is the CRLF byte copy of `program.brs`; recorded in V6 | ≤ 1 s each |
| W04 precedence | V3 | fixtures of BS-EXP-002, 011–021, 027, covering every grouping case of grammar-design §5 | groupings exactly as listed | — |
| W05 equivalent spellings | V3 | pairs below | the two trees are identical after removing anonymous nodes and byte ranges | — |
| W06 nesting, length, repetition | V10 | generated inputs below | valid inputs: no error (root has-error state, hidden `MISSING` included); invalid inputs: an error; all inputs: no crash, no hang | per input ≤ 10 s, ≤ 1 GiB resident |
| W07 UTF-8 | V3, V10 | BS-LEX-033 fixtures; samples with non-ASCII strings and comments; invalid UTF-8 and NUL bytes (robustness only) | valid: no `ERROR`; invalid bytes: no crash | — |
| W08 recovery | V3, V10 | recovery and negative fixtures (catalogue) | `:error` holds; no crash; no hang | — |
| W09 conditional compilation | V3, V5 | BS-COND fixtures including the spike fixtures; E1–E6 | baseline fixtures pass; spike decided PASS or FAIL by grammar-design §11 | — |
| W10 incremental edits | V5 | edit scripts below | the final tree of `tree-sitter parse --edits` equals a fresh parse of the final text (default and `--cst` output); every script ends on text with no error (root has-error state) | — |
| W11 highlights | V4 | `queries/highlights.scm`, `test/highlight/*.brs` | query compiles; every capture assertion passes | — |
| W12 native oracle | V6 | all corpus inputs and `test/samples/*.brs` | output recorded per identity (validation.md identity binding); two recordings of one identity on one platform give byte-identical `inputs/`, `trees/`, `cst/` and `manifest.json` (the CLI timings are dropped; the date and the compiled-library hash go to `run.json`) | — |
| W13 fuzz and pathological | V10 | `tree-sitter fuzz` over the corpus; W06 inputs; seeds below | no crash, no hang, no runaway memory | fuzz: 1,000 iterations × 10 edits per fixture at release candidates, with a recorded seed (default 1) |
| W14 downstream parity | V9 (in `go-treesitter`) | W12 inputs and W10 edits for the same grammar identity | ordered trees equal the native V6 records; `CGO_ENABLED=0` build and tests pass | run only when that work is authorized |

### W03 composite samples

Independently written; no text copied from Roku pages or other parsers.

| File | Must contain |
|---|---|
| `program.brs` | LIBRARY; functions and subs with typed and default parameters; anonymous functions; every statement kind; single-line and block IFs with ELSE IF and ELSE; FOR with STEP, FOR EACH, WHILE, EXIT, CONTINUE, NEXT; labels and GOTO; DIM; PRINT with `,`, `;`, adjacency, TAB and POS; TRY/CATCH/THROW (nested); every literal form; every operator level; optional chaining; `@`; multi-line arrays and AAs with comments; `#const`, `#if`/`#else if`/`#else`, `#error`; `'` and REM comments |
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
| binary-operator chain `1+1+…` (tree depth ≈ operand count; S04-H5) | 100,000 operands |
| postfix chain `a.b.c…` with calls and indexes | 2,000 links |
| string literal | 1 MiB |
| file of functions | 50,000 lines |
| unterminated constructs (IF, FOR, AA, string, `#if`) at EOF | 1 each (an error expected) |

### W10 incremental edit scripts

Each script names a base fixture input, applies its edits in order with
`tree-sitter parse --edits` (each edit is followed by an incremental reparse)
and compares the final tree with a fresh parse of the final text. Edit strings
use the CLI form `row,column deleted-length inserted-text` (rows and columns
from 0); `↵` in inserted text is a line feed.

| Script | Base | Edits (in order) |
|---|---|---|
| I01 | `BS-LEX-009: blank lines around and inside blocks` | insert `y` after `x`; delete it |
| I02 | `BS-LEX-005: one statement per line` | delete the line feed after `x = 1`; re-insert it |
| I03 | `BS-LEX-010: colon-separated statements` | insert ` : z = 3` after `x=5`; delete it |
| I04 | `BS-STMT-007: single-line IF with THEN` | delete `print "out of range"` and insert `↵print 1↵end if`; restore the original text |
| I05 | `BS-STMT-010: block IF with ELSE IF and ELSE` | delete the `end if` line; re-insert it; delete the `else if n = 0 then` line and the line after it |
| I06 | `BS-LIT-016: doubled quotation marks` | insert `""` inside the second string; delete it |
| I07 | `BS-LEX-012: apostrophe comment lines` | insert `'` before `x = 1`; remove it |
| I08 | `BS-LEX-014: identifiers beginning with rem` | insert a space after the first `rem` of `remark`; remove it |
| I09 | `BS-EXP-007: optional chaining chain` | delete each `?`, then re-insert each |
| I10 | `BS-AA-003: multi-line associative array with commas` | remove the comma after `1`; restore it |
| I11 | `BS-LEX-006: mixed LF and CRLF line endings` | delete the CR of the first line ending; re-insert it |
| I12 | `BS-COND-002: #if around statements` | delete the `#end if` line; re-insert it |

Spike scripts (grammar-design §11). They decide criterion C5; if the spike
passes they stay in W10 permanently, if it fails they are recorded with the
spike evidence and leave W10. Base text:
`x = 1↵#if false↵    This is prose.↵#end if↵function foo() as void↵end function`

| Script | Edits (in order) |
|---|---|
| E1 (inside) | `2,12 5 text` |
| E2 (before) | `1,0 0 y = 2↵` |
| E3 (after) | `4,0 0 z = 3↵` |
| E4 (across, terminator) | `3,0 8` then `3,0 0 #end if↵` |
| E5 (across, condition) | `1,4 5 true` then `1,4 4 false` |
| E6 (inside, new branch) | `3,0 0 #else↵x = 2↵` |

### W11 highlight captures

Capture names are taken from the Tree-sitter CLI default theme (Level 3,
`crates/cli/src/highlight.rs` @ `v0.27.0`). `test/highlight/*.brs` asserts at
least one instance of every row. `test/highlight/tokens.brs` additionally
repeats the inputs of the fixtures marked **(token)** in the catalogue and
asserts the capture of every anonymous token that carries their requirement
(`?.`, `?@`, `?[`, `?(` as `@operator`; `?` as `@keyword`).

| Syntax | Capture |
|---|---|
| `comment`; `inactive_text` (spike PASS only) | `@comment` |
| `string`; `error_message` | `@string`; `@string.special` |
| `number` | `@number` |
| `true`, `false`, `invalid`, `source_literal` | `@constant.builtin` |
| statement, block and directive keywords, including the single-token terminators (`if then else elseif end endif for each in to step next while endwhile exit exitwhile continue return print ? dim goto stop library try catch endtry throw function sub endfunction endsub as`, `end if`, `end for`, `end while`, `end sub`, `end function`, `end try`, `#const #if #else #end #error`) | `@keyword` |
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
bytes and invalid UTF-8 (BS-LEX-034); line breaks in argument lists, after
`(` of a parameter list and after binary operators (BS-EXP-023, 024,
BS-FUNC-007); lone `"`, `#`, `?`, `&h`; 10,000 `(`; 10,000 `:`; `#if` without
`#end if`; directive-like region lines that end at a word boundary
(grammar-design §11); every other unresolved form listed in the registry; the
KL-002 witness `x = ` + `+*`×1,000 (validation.md). Only the robustness
criterion applies to them. The KL-002 scaling guard also parses the witness at
k = 250 and k = 1,000 and bounds the local exponent of the parse times
(validation.md "KL-002 and the V10 bound").

## Automation

Every command runs from the repository root; hosted CI (`.github/workflows/ci.yml`)
runs all of them except W12 and W14 on Windows and Ubuntu.

| Set | Command |
|---|---|
| W01, W02, W04, W07 (valid), W09 (fixtures), W11 | `python scripts/tscli.py test` (verified binary, private parser library, validation.md "Identity binding") and `python scripts/check_registry.py --complete` |
| W03 | `python scripts/check_samples.py` |
| W05 | `python scripts/check_spellings.py` |
| W06, W07 (invalid bytes), W08, W13 (KL-002 guard included) | `python scripts/check_robustness.py [--fuzz-iterations=N] [--fuzz-seed=N]` |
| W09 (C4), W10 (C5 included) | `python scripts/check_spike.py`, `python scripts/check_incremental.py` |
| W12 | `python scripts/record_oracle.py` (clean tree; output under `artifacts/oracle/`) |
| W14 | in `go-treesitter`, from the W12 inputs and W10 edits of the same identity |

## Corpus fixture catalogue

One row per registry fixture. Notation inside inputs: `↵` line feed, `␍`
carriage return, `⇥` tab, `‹BOM›` the bytes EF BB BF; every other character is
literal. The runner strips one final newline, so an input ends without one
unless its last character is `↵`.

Expected trees. The expected S-expression of a fixture is derived by hand
from the planned schema and the placement rules of tree-schema.md: named
nodes and fields only, fields exactly as planned (`operator` fields hold
anonymous tokens and do not appear). The column states it in full where it
contains a `comment` or where the catalogue gives it as `(…)`; elsewhere it
names every node and field that must appear and the derivation fills the
rest. `tree-sitter test --update` is never used to write a positive
expectation; a mismatch is investigated against the specification first.
`:error` marks negative, recovery and KL-demonstrating fixtures; they assert
only that an error is present (validation fixture rules). **(token)** marks a
fixture whose requirement also rests on an anonymous token; W11 asserts that
token.

### `test/corpus/lexical.txt`

| Fixture | Input | Expected |
|---|---|---|
| `BS-LEX-001: keywords in upper, lower and mixed case` | `IF x THEN PRINT "a"↵if x then print "a"↵If X Then Print "A"` | three `(if_statement condition: (identifier) consequence: (block (print_statement (string))))` |
| `BS-LEX-001: identifier spellings differing only in case` | `myVar = 1↵MYVAR = 2↵myvar = 3` | three `(assignment_statement left: (identifier) right: (number))` |
| `BS-LEX-002: indentation and repeated spaces` | `sub main()↵    x   =   1↵        print    x↵end sub` | `(function_declaration name: (identifier) parameters: (parameter_list) body: (block (assignment_statement …) (print_statement (identifier))))` |
| `BS-LEX-003: tab indentation and tabs between tokens` | `sub main()↵⇥x⇥=⇥1↵end sub` | `(function_declaration name: (identifier) parameters: (parameter_list) body: (block (assignment_statement …)))` |
| `BS-LEX-004: keyword directly followed by a string` | `if c <> k then print"error" : stop` | `(if_statement condition: (binary_expression …) consequence: (block (print_statement (string)) (stop_statement)))` |
| `BS-LEX-004: compact one-line anonymous function` | `photo.GetTitle=function():return m.xml@title:end function` | `(assignment_statement left: (member_expression …) right: (anonymous_function parameters: (parameter_list) body: (block (return_statement value: (attribute_expression object: (member_expression …) attribute: (identifier))))))` |
| `BS-LEX-005: one statement per line` | `x = 1↵y = 2↵print x + y` | `assignment_statement`, `assignment_statement`, `(print_statement (binary_expression …))` |
| `BS-LEX-008: final line without a line terminator` | `x = 1` | `(source_file (assignment_statement left: (identifier) right: (number)))` |
| `BS-LEX-008: final line with a line terminator` | `x = 1↵` | same tree as the previous fixture |
| `BS-LEX-008: empty file` | (empty) | `(source_file)` |
| `BS-LEX-008: only comments and blank lines` | `' a↵↵REM b↵` | `(source_file (comment) (comment))` |
| `BS-LEX-008: only indented blank lines` | `  ↵⇥↵  ` | `(source_file)` |
| `BS-LEX-009: blank lines around and inside blocks` | `↵↵sub main()↵↵  x = 1↵↵end sub↵↵` | `(source_file (function_declaration name: (identifier) parameters: (parameter_list) body: (block (assignment_statement …))))` |
| `BS-LEX-010: colon-separated statements` | `x=5:print 25; " is"; x^2` | `(assignment_statement …)`, `(print_statement (number) (string) (binary_expression …))` |
| `BS-LEX-010: colon-separated statements in a block body` | `sub main()↵  a = 1 : b = 2 : print a↵end sub` | `block` holding two `assignment_statement`s and a `print_statement` |
| `BS-LEX-011: repeated, leading and trailing colons` | `: x = 1 :: y = 2 :` | `(source_file (assignment_statement …) (assignment_statement …))` |
| `BS-LEX-012: apostrophe comment lines` | `' first↵'second↵x = 1` | `(source_file (comment) (comment) (assignment_statement left: (identifier) right: (number)))` |
| `BS-LEX-012: comment after code on the same line` | `x = 1 ' set x↵y = 2'no space` | `(source_file (assignment_statement left: (identifier) right: (number)) (comment) (assignment_statement left: (identifier) right: (number)) (comment))` |
| `BS-LEX-012: apostrophe inside a string` | `s = "don't stop"` | `(source_file (assignment_statement left: (identifier) right: (string)))` |
| `BS-LEX-013: REM comments in mixed case` | `REM upper↵rem lower↵Rem ** mixed **` | `(source_file (comment) (comment) (comment))` |
| `BS-LEX-014: identifiers beginning with rem` | `remark = 1↵rem1 = 2↵rem_x = remark + rem1` | three `assignment_statement`s; no `comment` |
| `BS-LEX-014: REM after code and after a colon` | `x = 1 rem note↵y = 2 : REM note` | `(source_file (assignment_statement left: (identifier) right: (number)) (comment) (assignment_statement left: (identifier) right: (number)) (comment))` |
| `BS-LEX-014: bare REM line` | `x = 1↵REM↵y = 2` | `(source_file (assignment_statement left: (identifier) right: (number)) (comment) (assignment_statement left: (identifier) right: (number)))` |
| `BS-LEX-015: identifier forms` | `a = boy5 + super_man$ + _x + a_very_long_identifier_name_123` | `binary_expression`s over four `identifier`s |
| `BS-LEX-017: variables with type designators` | `a = 1 : a$ = "s" : a% = 2 : a! = 1.5 : a# = 2.5` | five `(assignment_statement left: (identifier) right: …)` |
| `BS-LEX-017: designators on parameters and loop and catch variables` | `sub f(a$, n%)↵  for i% = 1 to n%↵  end for↵  for each s$ in list↵  end for↵  try↵    x = 1↵  catch e$↵  end try↵end sub` | `parameter name: (identifier)` twice; `for_statement counter: (identifier)`; `for_each_statement item: (identifier)`; `catch_clause variable: (identifier)` |
| `BS-LEX-018: LongInteger designator on a variable` | `id& = 9876543210&` | `(assignment_statement left: (identifier) right: (number))` |
| `BS-LEX-021: reserved keywords in statement positions` | `Function f() As Integer↵  Dim a[2]↵  For i = 1 To 2 Step 1↵    If a[i] = Invalid Then Exit For↵  Next↵  While True : Exit While : End While↵  Goto done↵done:↵  Return 1↵End Function` | `function_declaration` whose `block` holds `dim_statement`, `for_statement` (with `if_statement` → `exit_statement`), `while_statement` (→ `exit_statement`), `goto_statement`, `label_statement`, `return_statement` |
| `BS-LEX-021: reserved keywords in mixed case` | `Sub Main()↵  For Each v In list↵    If v = False And Not x Or y Then↵      Print LINE_NUM↵    ElseIf v Then↵      Stop↵    Else↵      While z↵        ExitWhile↵      EndWhile↵    EndIf↵  Next↵EndSub↵Function F()↵EndFunction` | `(source_file (function_declaration name: (identifier) parameters: (parameter_list) body: (block (for_each_statement item: (identifier) collection: (identifier) body: (block (if_statement condition: (binary_expression left: (binary_expression left: (binary_expression left: (identifier) right: (false)) right: (unary_expression operand: (identifier))) right: (identifier)) consequence: (block (print_statement (source_literal))) alternative: (else_if_clause condition: (identifier) consequence: (block (stop_statement))) alternative: (else_clause body: (block (while_statement condition: (identifier) body: (block (exit_statement)))))))))) (function_declaration name: (identifier) parameters: (parameter_list) body: (block)))` |
| `BS-LEX-022: reserved built-in function calls` | `o = CreateObject("roList")↵t = Type(o)↵b = Box(1)↵g = GetGlobalAA()↵e = GetLastRunCompileError()↵print tab(5) pos(0)` | each right side `(call_expression function: (identifier) arguments: (argument_list …))`; `print_statement` with two `call_expression`s |
| `BS-LEX-022: Eval, Run and GetLastRunRunTimeError calls` | `r = Eval("x = 1")↵Run("pkg:/source/other.brs")↵e = GetLastRunRunTimeError()` | `(source_file (assignment_statement left: (identifier) right: (call_expression function: (identifier) arguments: (argument_list (string)))) (call_expression function: (identifier) arguments: (argument_list (string))) (assignment_statement left: (identifier) right: (call_expression function: (identifier) arguments: (argument_list))))` |
| `BS-LEX-024: keywords as member names` | `list.next()↵player.stop()↵x = obj.end + obj.if + obj.print` | two `call_expression` statements over `member_expression property: (identifier)`; `binary_expression`s over three `member_expression`s |
| `BS-LEX-024: keywords as associative-array keys` | `aa = { function: "main()", end: 1, if: 2, next: 3 }` | four `(associative_array_entry key: (identifier) value: …)` |
| `BS-LEX-024: function as a member name after an index` | `name = e.backtrace[i].function` | `(source_file (assignment_statement left: (identifier) right: (member_expression object: (index_expression object: (member_expression object: (identifier) property: (identifier)) index: (identifier)) property: (identifier))))` |
| `BS-LEX-025: non-reserved keyword words as identifiers` | `mod = 3↵x = mod + in + as + integer + string↵y = a mod b` | `assignment_statement left: (identifier)`; `binary_expression`s over five `identifier`s; a `binary_expression` for `a mod b` |
| `BS-LEX-025: more non-reserved words as identifiers` | `x = continue + library + throw + try + catch + endtry↵y = float + double + boolean + object + dynamic + void` | `(source_file (assignment_statement left: (identifier) right: (binary_expression left: (binary_expression left: (binary_expression left: (binary_expression left: (binary_expression left: (identifier) right: (identifier)) right: (identifier)) right: (identifier)) right: (identifier)) right: (identifier))) (assignment_statement left: (identifier) right: (binary_expression left: (binary_expression left: (binary_expression left: (binary_expression left: (binary_expression left: (identifier) right: (identifier)) right: (identifier)) right: (identifier)) right: (identifier)) right: (identifier))))` |
| `BS-LEX-026: identifiers beginning with keywords` | `iffy = 1 : endpoint = 2 : format = 3 : printer = 4 : nextItem = 5 : stepSize = 6 : notify = 7 : order = 8 : android = 9 : returnValue = 10 : falsey = 11` | eleven `(assignment_statement left: (identifier) right: (number))` |
| `BS-LEX-033: UTF-8 text in comments and strings` | `' café ☕↵s = "Grüße, 世界"` | `(source_file (comment) (assignment_statement left: (identifier) right: (string)))` |

### `test/corpus/bytes/` (marked `-text`)

The last input line, just before the divider, ends with LF alone
(grammar-design §2).

| Fixture | Input | Expected |
|---|---|---|
| `BS-LEX-006: CRLF line endings` | `x = 1␍↵y = 2␍↵z = 3` | three `(assignment_statement left: (identifier) right: (number))` |
| `BS-LEX-006: mixed LF and CRLF line endings` | `x = 1␍↵y = 2↵z = 3` | three `(assignment_statement left: (identifier) right: (number))` |
| `BS-LEX-006: CRLF between comment lines` | `' a␍↵' b␍↵' c` | `(source_file (comment) (comment) (comment))` |
| `BS-LEX-033: leading byte-order mark` | `‹BOM›x = 1` | `(source_file (assignment_statement left: (identifier) right: (number)))` |

### `test/corpus/literals.txt`

| Fixture | Input | Expected |
|---|---|---|
| `BS-LIT-001: boolean literals` | `a = true : b = FALSE : c = True` | `right: (true)`, `(false)`, `(true)` |
| `BS-LIT-002: invalid literal` | `if x = invalid then x = INVALID` | condition `(binary_expression left: (identifier) right: (invalid))`; assignment `right: (invalid)` |
| `BS-LIT-003: decimal integers` | `x = 0 : y = 255 : z = 2147483647` | three `number`s |
| `BS-LIT-004: negative number is unary negation` | `x = -5` | `right: (unary_expression operand: (number))` |
| `BS-LIT-005: hex integers with either prefix case` | `a = &HFF : b = &hFF : c = &h28` | three `number`s |
| `BS-LIT-006: lowercase hex digits` | `a = &hff : b = &hFe` | two `number`s |
| `BS-LIT-007: float literal forms` | `a = 2.01 : b = 1.23456E+30 : c = 2! : d = 125! : e = 1.5E-3` | five `number`s |
| `BS-LIT-008: lowercase unsigned exponent and leading-dot fraction` | `a = 1e1000000 : b = .1 : c = 0.5e3` | three `number`s |
| `BS-LIT-009: double literal forms` | `a = 1.23456789D-12 : b = 2.3# : c = 125#` | three `number`s |
| `BS-LIT-010: lowercase d exponent` | `a = 1.5d-3` | one `number` |
| `BS-LIT-011: LongInteger literals` | `a = 9876543210& : b = &hFEDCBA9876543210&` | two `number`s |
| `BS-LIT-012: integer suffix on a literal` | `a = 125% : b = 100%` | two `number`s |
| `BS-LIT-014: method call on a numeric literal` | `print 5.tostr() + "th"↵if 100%.tostr() <> "100" then stop↵x = (-5).tostr()` | `call_expression function: (member_expression object: (number) property: (identifier))`; the same with `100%`; `member_expression object: (parenthesized_expression (unary_expression …))` |
| `BS-LIT-014: method call on a string literal` | `x = "5".toint() + 5↵y = "01234567".left(3)` | `member_expression object: (string)` under `call_expression` |
| `BS-LIT-015: string literals` | `a = "this is a string" : b = "" : c = " "` | three `string`s |
| `BS-LIT-016: doubled quotation marks` | `s = """"↵t = "say ""hi"""` | two `string`s |
| `BS-LIT-017: backslash and non-ASCII text in strings` | `p = "C:\path\n"↵q = "naïve ✓"` | two `string`s, no child nodes |
| `BS-LIT-019: LINE_NUM source literal` | `print LINE_NUM↵x = line_num + 1` | `(source_literal)` in both |
| `BS-LIT-020: function name used as a value` | `fivevar = five↵print fivevar()` | `(assignment_statement left: (identifier) right: (identifier))`; `(print_statement (call_expression …))` |

### `test/corpus/expressions.txt`

| Fixture | Input | Expected |
|---|---|---|
| `BS-EXP-001: primary expressions` | `x = [a, 1, "s", true, invalid, LINE_NUM, (b), {k: 1}, function() : return 1 : end function]` | `array_literal` holding `identifier`, `number`, `string`, `true`, `invalid`, `source_literal`, `parenthesized_expression`, `associative_array_literal`, `anonymous_function` |
| `BS-EXP-003: call forms` | `print five()↵print fivevar()↵print array[1]()↵obj.add()↵m.f(1, 2)` | `call_expression` with `function:` `identifier`, `identifier`, `index_expression`, `member_expression`, `member_expression` |
| `BS-EXP-004: member access chains` | `i.ifInt.SetInt(5)↵x = (1+2).tostr()↵y = f().a.b` | nested `member_expression`s; `object: (parenthesized_expression …)`; `object: (call_expression …)` |
| `BS-EXP-005: index access and chained indexing` | `x = a[1]↵y = a[1][2]↵z = f()[0]↵w = a.b[i + 1]` | `index_expression`s, nested in the second, over `call_expression` and `member_expression` objects |
| `BS-EXP-006: attribute operator` | `n = rsp.photos@perpage↵t = m.xml@title` | `(attribute_expression object: (member_expression …) attribute: (identifier))` |
| `BS-EXP-007: optional chaining chain` | `x = array?[3]?.foo?.bar?()` | (token) `(call_expression function: (member_expression object: (member_expression object: (index_expression object: (identifier) index: (number)) property: (identifier)) property: (identifier)) arguments: (argument_list))` |
| `BS-EXP-007: optional call and optional index with arguments` | `x = i?(1, "String", explode())↵y = i?[explode()]` | (token) `call_expression` with an `argument_list` of three expressions; `index_expression` |
| `BS-EXP-008: optional index as an assignment target` | `array?[12] = x` | `:error` |
| `BS-EXP-008: optional member as an assignment target` | `a?.b = 1` | `:error` |
| `BS-EXP-009: standalone optional call statement` | `f?()` | `:error` |
| `BS-EXP-009: standalone optional call on a member` | `a.b?()` | `:error` |
| `BS-EXP-010: optional chaining inside statement subexpressions` | `f(array?[12])↵f(foo?.bar).member = 5` | call statement with an `index_expression` argument; `(assignment_statement left: (member_expression object: (call_expression …) property: (identifier)) right: (number))` |
| `BS-LEX-029: optional-chaining tokens after whitespace` | `a = b ?. c↵x = s ?[ 5 ]↵y = f ?( 1 )↵z = e ?@ id` | (token) `member_expression`, `index_expression`, `call_expression`, `attribute_expression` |
| `BS-LEX-030: split optional-chaining token` | `a = b ? . c` | `:error` |

### `test/corpus/precedence.txt`

| Fixture | Input | Expected grouping |
|---|---|---|
| `BS-EXP-002: parentheses override precedence` | `x = (a + b) * c` | `(a + b) * c` |
| `BS-EXP-011: exponentiation is right associative` | `x = 2^3^2↵y = a.b ^ 2` | `2^(3^2)`; `(a.b) ^ 2` |
| `BS-EXP-012: unary minus against postfix and exponent` | `a = -5.tostr()↵b = -2^2` | `-(5.tostr())`; `-(2^2)` |
| `BS-EXP-012: unary operators against multiplication` | `a = -x * y↵c = +x` | `(-x) * y`; `+x` |
| `BS-EXP-013: multiplicative operators are left associative` | `x = a / b mod c \ d * e` | `(((a / b) mod c) \ d) * e` |
| `BS-EXP-014: integer division` | `x = 7 \ 2` | one `binary_expression` |
| `BS-EXP-015: additive operators against multiplicative` | `x = a + b * c↵y = a - b - c↵s = "a" + b + "c"` | `a + (b * c)`; `(a - b) - c`; `("a" + b) + "c"` |
| `BS-EXP-016: shifts between additive and comparison` | `x = a << b + c↵y = a < b << c↵z = 7 >> 1` | `a << (b + c)`; `a < (b << c)`; `7 >> 1` |
| `BS-EXP-017: comparison operators and chains` | `x = a < b < c↵y = a = b <> c↵z = a <= b and c >= d` | `(a < b) < c`; `(a = b) <> c`; `(a <= b) and (c >= d)` |
| `BS-EXP-018: NOT below comparison and above AND` | `x = not a = b↵y = not a and b↵z = not not a` | `not (a = b)`; `(not a) and b`; `not (not a)` |
| `BS-EXP-019: AND binds tighter than OR` | `x = a or b and c↵y = a or b or c↵z = a = c and not (b > 40)↵w = not a <> b and c or d` | `a or (b and c)`; `(a or b) or c`; `(a = c) and (not (b > 40))`; `((not (a <> b)) and c) or d` |
| `BS-EXP-020: equals inside an expression is comparison` | `x = a = b↵if a=5 then print "a is 5"` | `(assignment_statement left: (identifier) right: (binary_expression left: (identifier) right: (identifier)))`; condition `binary_expression` |
| `BS-EXP-021: mixed postfix chain` | `x = a?.b.c?[0]?(1)↵y = f(1)[2].g(3)` | (token) `(((a?.b).c)?[0])?(1)`; `((f(1))[2]).g(3)` |
| `BS-EXP-021: attribute operator inside a member chain` | `x = e@y.z↵w = a.b@c` | `(e@y).z`; `(a.b)@c` |
| `BS-EXP-027: prefix operators as right operands` | `a = 2^-2↵b = x * -y↵c = a < not b` | `2^(-2)`; `x * (-y)`; `a < (not b)` |

### `test/corpus/statements.txt`

| Fixture | Input | Expected |
|---|---|---|
| `BS-STMT-001: assignment to variables, members and indexes` | `a$ = "a rose"↵aa.newkey = "v"↵array[2] = "two"↵c[x, y, z] = k↵f(x).y = 1` | `left:` `identifier`; `member_expression`; `index_expression`; `index_expression` with three `index`; `(member_expression object: (call_expression …) property: (identifier))` |
| `BS-STMT-002: compound assignment operators` | `x+=1↵x-=1↵x*=3↵x/=2↵x\=2↵x<<=8↵x>>=4` | seven `(assignment_statement left: (identifier) right: (number))` |
| `BS-STMT-003: increment and decrement statements` | `x++↵x--↵counter++` | three `(update_statement operand: (identifier))` |
| `BS-STMT-004: increment and decrement on member and index targets` | `a.b++↵a[0]--` | `(update_statement operand: (member_expression …))`; `(update_statement operand: (index_expression …))` |
| `BS-STMT-005: call statements` | `HandleButton(msg.GetInt())↵cavemen.push("fred")↵m.top.observeField("x", "onX")` | three `call_expression` statements |
| `BS-STMT-023: RETURN with and without a value` | `function f()↵  if x then return↵  return 1↵end function` | `(return_statement)`; `(return_statement value: (number))` |
| `BS-STMT-024: PRINT separators and trailing semicolon` | `print 25; " is equal to"; x^2↵print "zone 1","zone 2"↵print a$;a$,a$;" ";a$↵print "no newline";` | four `print_statement`s with 3, 2, 5 and 1 expression children |
| `BS-STMT-024: question-mark PRINT with separators` | `? 25; " is"; x^2` | `(print_statement (number) (string) (binary_expression …))` |
| `BS-STMT-024: PRINT with a trailing comma` | `print a, b,` | `(source_file (print_statement (identifier) (identifier)))` |
| `BS-STMT-025: adjacent PRINT items` | `print "this is a five " 5 "!!"` | `(print_statement (string) (number) (string))` |
| `BS-STMT-025: TAB and POS items` | `print tab(5)"tabbed 5";tab(25)"tabbed 25"↵print tab(40) pos(0)↵print "these" tab(pos(0)+5)"words"` | items alternate `call_expression` and `string` as written |
| `BS-STMT-026: ambiguous adjacent PRINT items` | `print a -1↵print a (1)` | `(print_statement (binary_expression …))`; `(print_statement (call_expression …))` |
| `BS-STMT-039: PRINT with no items` | `print↵?` | `(source_file (print_statement) (print_statement))` |
| `BS-STMT-040: leading and repeated PRINT separators` | `print , a↵? ;a↵print a,,b↵print a;;b↵print ;` | `(source_file (print_statement (identifier)) (print_statement (identifier)) (print_statement (identifier) (identifier)) (print_statement (identifier) (identifier)) (print_statement))` |
| `BS-STMT-027: GOTO a label` | `start:↵goto start` | `(source_file (label_statement name: (identifier)) (goto_statement label: (identifier)))` |
| `BS-STMT-029: END statement` | `if done then end↵end` | `(if_statement condition: (identifier) consequence: (block (end_statement)))`; `(end_statement)` |
| `BS-STMT-030: STOP statement` | `if x then stop↵stop` | `(if_statement condition: (identifier) consequence: (block (stop_statement)))`; `(stop_statement)` |
| `BS-STMT-031: LIBRARY at the top of a file` | `Library "v30/bslCore.brs"↵sub main()↵end sub` | `(library_statement path: (string))`, `function_declaration` |
| `BS-STMT-032: LIBRARY after a function declaration` | `sub a()↵end sub↵LIBRARY "v30/bslCore.brs"` | `function_declaration`, `library_statement` |
| `BS-STMT-033: statements at file level` | `x = 1↵print x↵sub main()↵end sub↵if x then y = 2` | `assignment_statement`, `print_statement`, `function_declaration`, `if_statement` under `source_file` |
| `BS-STMT-037: EXIT FOR outside a loop is not rejected` | `exit for` | `(source_file (exit_statement))` (guard) |
| `BS-LEX-027: label line` | `sub main()↵mylabel:↵  print "here"↵  goto mylabel↵end sub` | `block` holding `label_statement`, `print_statement`, `goto_statement` |
| `BS-LEX-028: label followed by a comment` | `start: ' entry point↵goto start` | `(source_file (label_statement name: (identifier)) (comment) (goto_statement label: (identifier)))` |
| `BS-LEX-031: question-mark PRINT alias forms` | `?("Hello")↵?.1` | `(print_statement (parenthesized_expression (string)))`; `(print_statement (number))` |
| `BS-LEX-035: question mark followed by a bracket at statement start` | `?[1]` | `(source_file (print_statement (array_literal (number))))` |

### `test/corpus/if.txt`

| Fixture | Input | Expected |
|---|---|---|
| `BS-STMT-007: single-line IF with THEN` | `if x > 127 then print "out of range"` | `(source_file (if_statement condition: (binary_expression left: (identifier) right: (number)) consequence: (block (print_statement (string)))))` |
| `BS-STMT-007: single-line IF without THEN` | `if debug print "timeout"` | `(source_file (if_statement condition: (identifier) consequence: (block (print_statement (string)))))` |
| `BS-STMT-007: single-line IF with ELSE` | `if caveman = "fred" then print "flintstone" else print "rubble"` | `(if_statement condition: (binary_expression …) consequence: (block (print_statement (string))) alternative: (else_clause body: (block (print_statement (string)))))` |
| `BS-STMT-007: colon-separated statements in a single-line branch` | `if myname="fred" then yourname = "barney" : ? yourname` | `(if_statement condition: (binary_expression …) consequence: (block (assignment_statement …) (print_statement (identifier))))` |
| `BS-STMT-007: documented statement kinds in single-line branches` | `if k <> 0 then exit while↵if fruit = "lemon" then continue for↵if m.owner <> invalid then return m.owner↵if x then stop↵if y then f(1)` | five `if_statement`s whose `consequence` blocks hold `exit_statement`, `continue_statement`, `return_statement`, `stop_statement`, `call_expression` |
| `BS-STMT-008: THEN followed by a comment starts a block IF` | `if x then ' comment↵  y = 1↵end if` | `(source_file (if_statement condition: (identifier) (comment) consequence: (block (assignment_statement left: (identifier) right: (number)))))` |
| `BS-STMT-008: THEN followed by a colon starts a block IF` | `if x then : y = 1 : end if` | `(source_file (if_statement condition: (identifier) consequence: (block (assignment_statement left: (identifier) right: (number)))))` |
| `BS-STMT-009: nested single-line IF with ELSE` | `if a then if b then x = 1 else x = 2` | `(if_statement condition: (identifier) consequence: (block (if_statement condition: (identifier) consequence: (block (assignment_statement …)) alternative: (else_clause body: (block (assignment_statement …))))))` |
| `BS-STMT-009: single-line ELSE IF nests an IF` | `if a then x = 1 else if b then x = 2 else x = 3` | `(if_statement condition: (identifier) consequence: (block (assignment_statement …)) alternative: (else_clause body: (block (if_statement condition: (identifier) consequence: (block (assignment_statement …)) alternative: (else_clause body: (block (assignment_statement …)))))))` |
| `BS-STMT-009: other statement kinds in single-line branches` | `if a then goto done↵if b then end↵if c then throw "e"↵if d then dim x[2]↵if e then n++` | five `if_statement`s whose `consequence` blocks hold `goto_statement`, `end_statement`, `throw_statement`, `dim_statement`, `update_statement` |
| `BS-STMT-010: block IF with ELSE IF and ELSE` | `if n < 0 then↵  throw "negative"↵else if n = 0 then↵  return 1↵else↵  return n * f(n-1)↵end if` | `(if_statement condition: (binary_expression …) consequence: (block (throw_statement value: (string))) alternative: (else_if_clause condition: (binary_expression …) consequence: (block (return_statement value: (number)))) alternative: (else_clause body: (block (return_statement value: (binary_expression …)))))` |
| `BS-STMT-010: ELSEIF and ENDIF spellings` | `if a then↵  x = 1↵elseif b then↵  x = 2↵endif` | `(if_statement condition: (identifier) consequence: (block (assignment_statement …)) alternative: (else_if_clause condition: (identifier) consequence: (block (assignment_statement …))))` |
| `BS-STMT-010: block IF without THEN` | `if msg.isFullResult()↵  return 9↵end if` | `(if_statement condition: (call_expression …) consequence: (block (return_statement value: (number))))` |
| `BS-STMT-010: ELSE IF and ELSEIF without THEN` | `if a↵  x = 1↵else if b↵  x = 2↵elseif c↵  x = 3↵end if` | `(source_file (if_statement condition: (identifier) consequence: (block (assignment_statement left: (identifier) right: (number))) alternative: (else_if_clause condition: (identifier) consequence: (block (assignment_statement left: (identifier) right: (number)))) alternative: (else_if_clause condition: (identifier) consequence: (block (assignment_statement left: (identifier) right: (number))))))` |
| `BS-STMT-011: ELSE and ELSE IF headers followed by comments and colons` | `if a then↵  x = 1↵else if b then ' second↵  x = 2↵else : x = 3↵end if` | `(source_file (if_statement condition: (identifier) consequence: (block (assignment_statement left: (identifier) right: (number))) alternative: (else_if_clause condition: (identifier) (comment) consequence: (block (assignment_statement left: (identifier) right: (number)))) alternative: (else_clause body: (block (assignment_statement left: (identifier) right: (number))))))` |
| `BS-LEX-032: IF with an optional call starts a block IF` | `IF x?("Hello")↵  PRINT "Hi"↵END IF` | (token) `(source_file (if_statement condition: (call_expression function: (identifier) arguments: (argument_list (string))) consequence: (block (print_statement (string)))))` |

### `test/corpus/loops.txt`

| Fixture | Input | Expected |
|---|---|---|
| `BS-STMT-012: FOR with and without STEP` | `for i = 10 to 1 Step -1↵  print i↵end for↵for j = 1 to n↵end for` | `(for_statement counter: (identifier) start: (number) end: (number) step: (unary_expression …) body: (block (print_statement (identifier))))`; `(for_statement counter: (identifier) start: (number) end: (identifier) body: (block))` |
| `BS-STMT-013: NEXT terminates FOR and FOR EACH` | `for i=10 to 1 step -1↵  print i↵next↵for each n in aa↵  print n;aa[n]↵next` | `for_statement`, `for_each_statement` |
| `BS-STMT-015: FOR EACH over an expression` | `for each caveman in cavemen↵  print caveman↵end for↵for each k in m.getList()↵end for` | `(for_each_statement item: (identifier) collection: (identifier) body: …)`; `collection: (call_expression …)` |
| `BS-STMT-016: WHILE loop` | `while k = 0↵  k = 1↵end while` | `(while_statement condition: (binary_expression …) body: (block (assignment_statement …)))` |
| `BS-STMT-017: WHILE terminated by NEXT` | `while x↵  x = x - 1↵next` | `:error` |
| `BS-STMT-018: EXIT FOR and EXIT WHILE` | `for i = 1 to 3↵  if i = 2 then exit for↵end for↵while true↵  exit while↵end while` | two `exit_statement`s |
| `BS-STMT-019: CONTINUE FOR and CONTINUE WHILE` | `for each fruit in fruits↵  if fruit = "lemon" then continue for↵end for↵while c < 3↵  c++↵  continue while↵end while` | two `continue_statement`s |
| `BS-STMT-020: ENDWHILE and EXITWHILE` | `while true↵  exitwhile↵endwhile` | `(while_statement condition: (true) body: (block (exit_statement)))` |
| `BS-STMT-022: multi-word keywords with extra spacing` | `for each⇥x in xs↵  if x then↵  end   if↵end⇥for` | `(for_each_statement item: (identifier) collection: (identifier) body: (block (if_statement condition: (identifier) consequence: (block))))` |
| `BS-STMT-022: more multi-word keywords with extra spacing` | `function f()↵  for i = 1 to 2↵    if a then↵      exit  for↵    else  if b then↵      continue⇥for↵    end if↵  end  for↵  while x↵    exit⇥while↵  end  while↵  try↵  catch e↵  end  try↵end  function↵sub s()↵end⇥sub` | `(source_file (function_declaration name: (identifier) parameters: (parameter_list) body: (block (for_statement counter: (identifier) start: (number) end: (number) body: (block (if_statement condition: (identifier) consequence: (block (exit_statement)) alternative: (else_if_clause condition: (identifier) consequence: (block (continue_statement)))))) (while_statement condition: (identifier) body: (block (exit_statement))) (try_statement body: (block) handler: (catch_clause variable: (identifier) body: (block))))) (function_declaration name: (identifier) parameters: (parameter_list) body: (block)))` |
| `BS-STMT-035: one-line loop and TRY bodies with colons` | `for i = 1 to 3 : print i : end for↵while x : x = x - 1 : end while↵try : f() : catch e : print e : end try` | `for_statement`, `while_statement`, `try_statement`, each body holding one statement |
| `BS-STMT-035: FOR EACH header ending with a colon` | `for each v in list : print v : end for` | `(source_file (for_each_statement item: (identifier) collection: (identifier) body: (block (print_statement (identifier)))))` |
| `BS-STMT-036: nested blocks close with their own terminators` | `for i = 1 to 2↵  if x then↵    while y↵      y = false↵    end while↵  end if↵end for` | `for_statement` → `if_statement` → `while_statement`, nested in that order |
| `BS-STMT-036: compact terminators close their own constructs` | `function f()↵  try↵    while x↵      if y then↵        x = false↵      endif↵    endwhile↵  catch e↵  endtry↵endfunction↵sub s()↵endsub` | `(source_file (function_declaration name: (identifier) parameters: (parameter_list) body: (block (try_statement body: (block (while_statement condition: (identifier) body: (block (if_statement condition: (identifier) consequence: (block (assignment_statement left: (identifier) right: (false))))))) handler: (catch_clause variable: (identifier) body: (block))))) (function_declaration name: (identifier) parameters: (parameter_list) body: (block)))` |

### `test/corpus/functions.txt`

| Fixture | Input | Expected |
|---|---|---|
| `BS-TYPE-001: parameter and return type names` | `function f(a as integer, b as Float, c as DOUBLE, d as boolean, e as string, f as object, g as dynamic, h as function) as void↵end function` | eight `(parameter name: (identifier) type: (type))`; `return_type: (type)` |
| `BS-FUNC-001: function with typed parameters and return type` | `function add(a as Integer, b as Integer) as Integer↵  return a+b↵end function` | `(function_declaration name: (identifier) parameters: (parameter_list (parameter name: (identifier) type: (type)) (parameter name: (identifier) type: (type))) return_type: (type) body: (block (return_statement value: (binary_expression …))))` |
| `BS-FUNC-001: function without parameters` | `function five() as Integer↵  return 5↵end function↵function Main()↵end function` | two `function_declaration`s with `parameters: (parameter_list)` |
| `BS-FUNC-002: sub declaration` | `sub main()↵  print "x"↵end sub` | `(function_declaration name: (identifier) parameters: (parameter_list) body: (block (print_statement (string))))` |
| `BS-FUNC-003: ENDFUNCTION and ENDSUB` | `function f()↵endfunction↵sub g()↵endsub` | two `function_declaration`s with empty `block`s |
| `BS-FUNC-005: parameters with defaults and types` | `function add3(a as Integer, b=a+5 as Integer) as Integer↵  return a+b↵end function↵sub s(x = 1, y = "a")↵end sub` | `(parameter name: (identifier) default: (binary_expression …) type: (type))`; `(parameter name: (identifier) default: (number))`, `(parameter name: (identifier) default: (string))` |
| `BS-FUNC-006: parameter list continued after a comma` | `function helper(http as Object, xmllist as Object,↵    owner=invalid as dynamic) as Object↵  return invalid↵end function` | `parameter_list` with three `parameter`s |
| `BS-FUNC-008: default-parameter order is not enforced` | `function f(a = 1, b)↵end function` | `function_declaration`, no `ERROR` (guard) |
| `BS-FUNC-009: anonymous function assigned to a variable` | `myfunc = function (a, b)↵  return a+b↵end function↵print myfunc(1,2)` | `(assignment_statement left: (identifier) right: (anonymous_function parameters: (parameter_list …) body: (block (return_statement …))))`; `print_statement` |
| `BS-FUNC-009: anonymous function as an associative-array value` | `q = {↵  starring : function(o, e)↵    return 0↵  end function↵}` | `(associative_array_entry key: (identifier) value: (anonymous_function …))` |
| `BS-FUNC-010: one-line function bodies` | `FUNCTION explode() : THROW "Kaboom!" : END FUNCTION↵FUNCTION x(_) : RETURN TRUE : END FUNCTION↵obj = { Get : function() : return m.Value : end function }` | two `function_declaration`s with one-statement bodies; `anonymous_function` value |
| `BS-FUNC-011: anonymous sub` | `cb = sub (x)↵  print x↵end sub` | `(assignment_statement left: (identifier) right: (anonymous_function parameters: (parameter_list (parameter name: (identifier))) body: (block (print_statement (identifier)))))` |
| `BS-FUNC-013: m used as an identifier` | `function add() as void↵  m.result = m.a + m.b↵end function` | `member_expression object: (identifier)` for each `m` |

### `test/corpus/collections.txt`

| Fixture | Input | Expected |
|---|---|---|
| `BS-ARRAY-001: empty, flat and nested array literals` | `myarray = []↵myarray = [ 1, 2, 3 ]↵myarray = [ x+5, true, 1<>2, ["a","b"] ]` | `array_literal` with 0, 3 and 4 children, the last holding an `array_literal` |
| `BS-ARRAY-002: multi-line array without commas` | `a = [↵  "able"↵  "baker"↵]` | `(array_literal (string) (string))` |
| `BS-ARRAY-002: multi-line array with commas` | `a = [↵  3.1415,↵  2.71828↵]` | `(array_literal (number) (number))` |
| `BS-ARRAY-003: trailing comma in array literals` | `a = [1, 2,]↵b = [↵  1,↵  2,↵]` | two `(array_literal (number) (number))` |
| `BS-ARRAY-004: DIM with one and several dimensions` | `Dim array[5]↵dim c[5, 4, 6]↵dim d[n + 1]` | `dim_statement name` with 1, 3 and 1 `dimension` |
| `BS-ARRAY-005: DIM with parentheses` | `dim a(5, 4)` | `(dim_statement name: (identifier) dimension: (number) dimension: (number))` |
| `BS-ARRAY-007: multiple indexes in one access` | `item = array[1,2,3]↵item = array[1][2][3]` | `(index_expression object: (identifier) index: (number) index: (number) index: (number))`; three nested `index_expression`s |
| `BS-AA-001: empty and one-line associative arrays` | `aa = { }↵aa = {}↵aa = { key1: "value", key2: 55, key3: 5+3 }` | `associative_array_literal` with 0, 0 and 3 entries |
| `BS-AA-001: anonymous functions as values` | `obj = {↵  Set : function(x) : m.Value = x : end function↵  Value : 0↵}` | two entries; the first `value: (anonymous_function …)` |
| `BS-AA-002: string keys` | `aa = { "Jane Doe": 1001, "John Doe": 1002 }` | two `(associative_array_entry key: (string) value: (number))` |
| `BS-AA-003: multi-line associative array without commas` | `aa = {↵  Myfunc1: aFunction↵  Myval1: "the value"↵}` | two entries |
| `BS-AA-003: multi-line associative array with commas` | `aa = {↵  alpha: 1,↵  zulu: 26↵}` | two entries |
| `BS-AA-004: trailing comma in associative arrays` | `aa = { a: 1, }↵bb = {↵  a: 1,↵  b: 2,↵}` | one and two entries |
| `BS-AA-005: duplicate keys are not rejected` | `aa = { a: 1, a: 2 }` | two entries, no `ERROR` (guard) |

### `test/corpus/error-handling.txt`

| Fixture | Input | Expected |
|---|---|---|
| `BS-ERR-001: TRY with CATCH` | `try↵  print 1/0↵catch e↵  print "Division failed: ", e↵end try` | `(try_statement body: (block (print_statement …)) handler: (catch_clause variable: (identifier) body: (block (print_statement …))))` |
| `BS-ERR-001: empty TRY and CATCH bodies with ENDTRY` | `try↵catch e↵endtry` | `(try_statement body: (block) handler: (catch_clause variable: (identifier) body: (block)))` |
| `BS-ERR-002: nested TRY in TRY and CATCH bodies` | `try↵  try↵    x = 1↵  catch e↵  end try↵catch e↵  try↵    print e.message↵  catch e2↵  end try↵end try` | inner `try_statement`s in the outer `body` and in the `catch_clause` body |
| `BS-ERR-003: CATCH without a variable` | `try↵catch↵end try` | `:error` |
| `BS-ERR-003: CATCH with an index` | `try↵catch someArray[23]↵end try` | `:error` |
| `BS-ERR-003: CATCH with a member` | `try↵catch bill.ted↵end try` | `:error` |
| `BS-ERR-003: CATCH with a literal` | `try↵catch 22↵end try` | `:error` |
| `BS-ERR-003: CATCH with an expression` | `try↵catch a+wave↵end try` | `:error` |
| `BS-ERR-004: THROW forms` | `throw "Cannot calculate."↵THROW {number: ERR_DIV_ZERO, message: "Division by zero"}↵throw e` | `throw_statement value:` `string`, `associative_array_literal`, `identifier` |
| `BS-ERR-005: try and catch as identifiers` | `x = try + catch↵catch = 1↵sub f()↵  catch = 2↵  x = 0↵  catch = 3↵  if x then↵    catch = 4↵  end if↵end sub↵try↵  if y then↵    catch = 5↵  end if↵catch e↵end try` | every `catch = …` is `(assignment_statement left: (identifier) right: (number))`; the last lines form one `try_statement` whose `handler` has `variable: (identifier)` |
| `BS-ERR-005: try as an identifier in a single-line branch` | `if a then try = 1↵if b then x = 1 else try = 2` | `(source_file (if_statement condition: (identifier) consequence: (block (assignment_statement left: (identifier) right: (number)))) (if_statement condition: (identifier) consequence: (block (assignment_statement left: (identifier) right: (number))) alternative: (else_clause body: (block (assignment_statement left: (identifier) right: (number))))))` |
| `BS-ERR-007: label inside a TRY body is not rejected` | `try↵here:↵  x = 1↵catch e↵end try` | `try_statement` whose `body` holds a `label_statement`; no `ERROR` (guard) |

### `test/corpus/conditional-compilation.txt`

| Fixture | Input | Expected |
|---|---|---|
| `BS-COND-001: #const forms` | `#const someFlag = true↵#const anotherFlag = false↵#const someOtherFlag = someFlag` | three `const_directive name: (identifier) value:` `(true)`, `(false)`, `(identifier)` |
| `BS-COND-002: #if around statements` | `#if mylibrary_enable_detailed_logging↵    ? "hello world"↵#end if` | `(source_file (if_directive condition: (identifier) consequence: (block (print_statement (string)))))` |
| `BS-COND-002: #if true and #if name bodies are code` | `#if true↵  x = 1↵#end if↵#if DEBUG↵  y = 2↵#end if` | `(if_directive condition: (true) consequence: (block (assignment_statement …)))`; `(if_directive condition: (identifier) consequence: (block (assignment_statement …)))` |
| `BS-COND-003: #else if and #else branches` | `#const FeatureA = true↵#if FeatureA↵  'code for Feature A↵#else if FeatureB↵  x = 1↵#else↵  y = 2↵#end if` | `(source_file (const_directive name: (identifier) value: (true)) (if_directive condition: (identifier) consequence: (block (comment)) alternative: (else_if_directive condition: (identifier) consequence: (block (assignment_statement left: (identifier) right: (number)))) alternative: (else_directive body: (block (assignment_statement left: (identifier) right: (number))))))` |
| `BS-COND-004: #error with free text` | `#if FeatureAImplemented↵  ' code↵#else↵  #error TO DO: implement feature A, don't forget↵#end if` | `(source_file (if_directive condition: (identifier) consequence: (block (comment)) alternative: (else_directive body: (block (error_directive message: (error_message))))))` |
| `BS-COND-005: directives in mixed case` | `#CONST Flag = TRUE↵#If flag↵  x = 1↵#Else If other↵#ELSE↵#End If` | `(source_file (const_directive name: (identifier) value: (true)) (if_directive condition: (identifier) consequence: (block (assignment_statement …)) alternative: (else_if_directive condition: (identifier) consequence: (block)) alternative: (else_directive body: (block))))` |
| `BS-COND-006: #if around function declarations` | `#if DEBUG↵function debugOnly()↵end function↵#end if` | `(source_file (if_directive condition: (identifier) consequence: (block (function_declaration name: (identifier) parameters: (parameter_list) body: (block)))))` |
| `BS-COND-008: indented directives with comments` | `sub main()↵    #if DEBUG ' debug only↵        print "d"↵    #else   if   OTHER↵    #end⇥if ' done↵end sub` | `(source_file (function_declaration name: (identifier) parameters: (parameter_list) body: (block (if_directive condition: (identifier) (comment) consequence: (block (print_statement (string))) alternative: (else_if_directive condition: (identifier) consequence: (block))) (comment))))` |
| `BS-COND-008: comments after #const, #else if and #else` | `#const A = true ' note↵#if A↵#else if B ' note↵#else ' note↵#end if` | `(source_file (const_directive name: (identifier) value: (true)) (comment) (if_directive condition: (identifier) consequence: (block) alternative: (else_if_directive condition: (identifier) (comment) consequence: (block)) alternative: (else_directive (comment) body: (block))))` |
| `BS-COND-012: #if inside a function body` | `sub main()↵#if DEBUG↵  print "d"↵#end if↵end sub` | `(function_declaration … body: (block (if_directive condition: (identifier) consequence: (block (print_statement (string))))))` |
| `BS-COND-012: nested #if blocks` | `#if A↵  #if B↵    x = 1↵  #end if↵#end if` | `(if_directive condition: (identifier) consequence: (block (if_directive condition: (identifier) consequence: (block (assignment_statement …)))))` |
| `BS-COND-013: #const with a non-boolean value` | `#const x = 5` | `:error` |
| `BS-COND-013: #const with a string value` | `#const s = "a"` | `:error` |
| `BS-COND-015: #error without a message` | `#error↵#if DEBUG↵  #error⇥↵#end if` | `(source_file (error_directive) (if_directive condition: (identifier) consequence: (block (error_directive))))` |

ADR-0004 literal-false fixtures (grammar-design §11). The PASS column applies
to design V1; under V2 every `(comment)` inside `inactive_text` is absent. On
FAIL, `:error` fixtures are listed as KL-001 demonstrating fixtures. Outcome:
the spike passed with design V1, so the corpus uses the PASS column.

| Fixture | Input | PASS (V1) | FAIL |
|---|---|---|---|
| `BS-COND-007: block comment with prose` | `#if false↵    This is a function that does nothing.↵    It takes no parameters.↵#end if↵function foo() as void↵    'do nothing↵end function` | `(source_file (if_directive condition: (false) consequence: (inactive_text)) (function_declaration name: (identifier) parameters: (parameter_list) return_type: (type) body: (block (comment))))` | `:error` |
| `BS-COND-007: commented-out function` | `#if false↵    function Order66() as void↵        'code for Order66↵    end function↵#end if` | `(source_file (if_directive condition: (false) consequence: (inactive_text (comment))))` | `(source_file (if_directive condition: (false) consequence: (block (function_declaration name: (identifier) parameters: (parameter_list) return_type: (type) body: (block (comment))))))` |
| `BS-COND-007: spike S3 case variants of #if false` | `#IF FALSE↵    Some prose here.↵#END IF↵#If False↵    More prose.↵#End If` | `(source_file (if_directive condition: (false) consequence: (inactive_text)) (if_directive condition: (false) consequence: (inactive_text)))` | `:error` |
| `BS-COND-007: spike S4 #if falsey is code` | `#if falsey↵    x = 1↵#end if↵#if falsey ' note↵    y = 2↵#end if` | `(source_file (if_directive condition: (identifier) consequence: (block (assignment_statement left: (identifier) right: (number)))) (if_directive condition: (identifier) (comment) consequence: (block (assignment_statement left: (identifier) right: (number)))))` | same as PASS |
| `BS-COND-007: spike S5 comment after #if false` | `#if false ' note↵    Prose with words.↵#end if` | `(source_file (if_directive condition: (false) (comment) consequence: (inactive_text)))` | `:error` |
| `BS-COND-007: spike S6 #else after a false branch` | `#if false↵    Prose line.↵#else↵    x = 1↵#end if` | `(source_file (if_directive condition: (false) consequence: (inactive_text) alternative: (else_directive body: (block (assignment_statement left: (identifier) right: (number))))))` | `:error` |
| `BS-COND-007: spike S7 #else if after a false branch` | `#if false↵    Prose line.↵#else if DEBUG↵    x = 1↵#end if` | `(source_file (if_directive condition: (false) consequence: (inactive_text) alternative: (else_if_directive condition: (identifier) consequence: (block (assignment_statement left: (identifier) right: (number))))))` | `:error` |
| `BS-COND-007: spike S8 nested block inside a false region` | `#if false↵    Outer prose.↵    #if DEBUG↵        Inner prose.↵    #else↵        More inner prose.↵    #end if↵    Outer prose again.↵#end if↵x = 1` | `(source_file (if_directive condition: (false) consequence: (inactive_text)) (assignment_statement left: (identifier) right: (number)))` | `:error` |
| `BS-COND-007: spike S9 directives inside a false region` | `#if false↵    #const flag = true↵    #error not compiled↵#end if` | `(source_file (if_directive condition: (false) consequence: (inactive_text)))` | `(source_file (if_directive condition: (false) consequence: (block (const_directive name: (identifier) value: (true)) (error_directive message: (error_message)))))` |
| `BS-COND-007: spike S10 quotes and comments inside a false region` | `#if false↵    Don't "stop" here↵    ' a real comment↵    REM another comment↵#end if` | `(source_file (if_directive condition: (false) consequence: (inactive_text (comment) (comment))))` | `:error` |
| `BS-COND-007: spike S11 #else if false` | `#if DEBUG↵    x = 1↵#else if false↵    Prose line.↵#end if` | `(source_file (if_directive condition: (identifier) consequence: (block (assignment_statement left: (identifier) right: (number))) alternative: (else_if_directive condition: (false) consequence: (inactive_text))))` | `:error` |
| `BS-COND-007: spike S12 REM-like prose inside a false region` | `#if false↵    Remember this.↵    REMARK: prose.↵    remote control↵#end if` | `(source_file (if_directive condition: (false) consequence: (inactive_text)))` | `:error` |
| `BS-COND-007: directive-like words inside a false region` | `#if false↵    #ifdef FOO↵    #endregion notes↵    #elsewhere prose↵    #iffy↵#end if↵x = 1` | `(source_file (if_directive condition: (false) consequence: (inactive_text)) (assignment_statement left: (identifier) right: (number)))` | `:error` |
| `BS-COND-007: spike R1 error before a false region` | `x = = 1↵#if false↵    Prose.↵#end if↵function foo()↵end function` | `:error` (C4 check in grammar-design §11) | `:error` |
| `BS-COND-007: spike R2 error after a false region` | `#if false↵    Prose.↵#end if↵x = = 1↵function foo()↵end function` | `:error` (C4 check) | `:error` |
| `BS-COND-007: spike R3 false region without #end if` | `#if false↵    Prose without an end.` | `:error` | `:error` |

### `test/corpus/recovery.txt`

Only the presence of an error is asserted (`:error`); each input lacks the
terminator or delimiter its construct is documented to have.

| Fixture | Input |
|---|---|
| `BS-LIT-015: unterminated string at end of line` | `a = "open↵b = 1` |
| `BS-EXP-002: unclosed parenthesis` | `x = (a + b` |
| `BS-STMT-001: assignment missing its value` | `x =` |
| `BS-STMT-010: block IF missing END IF` | `if x then↵  y = 1` |
| `BS-STMT-012: FOR missing END FOR` | `for i = 1 to 2↵  print i` |
| `BS-STMT-016: WHILE missing END WHILE` | `while true↵  x = 1` |
| `BS-STMT-036: END IF closing a FOR body` | `for i = 1 to 2↵  x = 1↵end if` |
| `BS-STMT-036: END SUB closing a FUNCTION` | `function f()↵  x = 1↵end sub` |
| `BS-FUNC-001: function missing END FUNCTION` | `function f()↵  x = 1` |
| `BS-ARRAY-001: array literal missing its closing bracket` | `a = [1, 2` |
| `BS-AA-001: associative array missing its closing brace` | `aa = { a: 1` |
| `BS-ERR-001: TRY missing END TRY` | `try↵  x = 1↵catch e` |
| `BS-COND-002: #if missing #end if` | `#if DEBUG↵  x = 1` |

## Counts

| Item | Count |
|---|---|
| registry fixtures catalogued | 224 |
| positive (including 4 guards; on a spike FAIL, 10 literal-false fixtures take their `:error` form) | 195 |
| negative (`invalid` evidence) | 13 |
| recovery (including spike R1–R3) | 16 |
| corpus files | 13 (`bytes/` counted once) |
| incremental scripts | 12 + E1–E6 |
| equivalent-spelling pairs | 11 |
| generated inputs | 10 |
| highlight capture rows | 17 |
