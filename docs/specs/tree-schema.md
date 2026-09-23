# Tree schema

The parse tree is this repository's public interface: queries, editors and
downstream runtimes depend on node types and field names. This document holds
the stability policy and naming rules, the planned public schema that the first
implementation builds, and the released node catalogue once the grammar
exists.

## Tiers

| Tier | Contents | Stability |
|---|---|---|
| Public | Named node types for declarations, statements, expressions, literals, comments and conditional-compilation constructs; their field names; supertypes; every node referenced by a shipped query | Deliberately designed; changes classified below |
| Internal | Hidden rules (`_name`), anonymous tokens, helper nodes not listed in the catalogue | May change freely before 1.0 |

A node becomes public when it is added to the catalogue below.

## Naming and shape rules

- Node types and fields use `snake_case`, named for the BrightScript construct,
  not for a downstream use (no code-graph or editor-specific names).
- Names are chosen independently; they are not taken from the legacy grammar
  or from BrighterScript's AST.
- Every construct a consumer needs to find is a named node; its semantically
  distinct children are reachable by field name rather than position.
- Equivalent spellings (letter case, `END IF` vs `ENDIF`, `?` vs `PRINT`)
  produce the same node types. Whether the original spelling is recoverable
  from anonymous tokens is decided per construct and recorded here.
- Categories that consumers match as a group (statements, expressions) are
  expressed as supertypes where that keeps queries simple.
- Error-recovery trees are not part of the schema.

## Compatibility and versioning

The grammar version in `tree-sitter.json` is embedded in generated
`parser.c`, so a version bump is a regeneration
([ADR-0002](../design/decisions/ADR-0002-generator-pin-and-generated-artifacts.md)).

| Change | Before 1.0 | From 1.0 |
|---|---|---|
| Public node type or field removed or renamed; public structure changed incompatibly | MINOR bump, recorded | MAJOR |
| Public node type or field added | MINOR | MINOR |
| Internal change only | PATCH if `node-types.json` is unchanged, otherwise MINOR | MINOR |
| Fix with no node-type or structure change | PATCH | PATCH |

From 1.0 this matches Tree-sitter's
[publishing guidance](https://tree-sitter.github.io/tree-sitter/creating-parsers/6-publishing.html)
(incompatible node-type or structure changes are major; new node types are
minor).

Any change to the public tier updates the catalogue in the same commit, and
the `src/node-types.json` diff is reviewed. Queries that reference changed
nodes are updated in the same commit.

1.0 freezes the public tier; the other 1.0 conditions are the v1.0 gates in
[validation.md](../validation/validation.md).

## Catalogue

Empty. It is filled when the implementation reconciles the planned public
schema below with the generated `src/node-types.json`; only then do the nodes
become public in the sense of the tiers above.

## Planned public schema

Designed in Session 02 from the requirement registry
([language-conformance.md](language-conformance.md)); planned rule families are
in [grammar-design.md](grammar-design.md). **A planned node is not a released
public node.** A difference found at reconciliation is resolved by changing the
grammar to match this schema, or by changing this section with a recorded
reason in the same commit.

Names follow Tree-sitter's standard rule names (`source_file`, `block`,
`identifier`, `string`, `comment`, `type`; Level 3, "Standard Rule Names") and
the `*_statement`, `*_expression`, `*_clause` and `*_list` conventions of
official grammars; the remaining names are the construct names used by the
Roku documentation. No name is taken from the legacy grammar or BrighterScript.

### Supertypes

| Supertype | Subtypes |
|---|---|
| `statement` | `assignment_statement`, `update_statement`, `call_expression`, `if_statement`, `for_statement`, `for_each_statement`, `while_statement`, `exit_statement`, `continue_statement`, `return_statement`, `print_statement`, `dim_statement`, `goto_statement`, `label_statement`, `end_statement`, `stop_statement`, `library_statement`, `throw_statement`, `try_statement`, `function_declaration`, `const_directive`, `if_directive`, `error_directive` (23) |
| `expression` | `identifier`, `number`, `string`, `true`, `false`, `invalid`, `source_literal`, `array_literal`, `associative_array_literal`, `parenthesized_expression`, `anonymous_function`, `unary_expression`, `binary_expression`, `call_expression`, `member_expression`, `index_expression`, `attribute_expression` (17) |

`call_expression` is in both: a call is also a statement.

### Planned nodes

Fields are written `field: allowed types`; `?` optional, `*` repeated, `+` one
or more. Unnamed children are named nodes without a field.

| Node | Fields | Unnamed children | Requirements | Query use |
|---|---|---|---|---|
| `source_file` | — | `statement`* | BS-STMT-033, BS-LEX-008 | root |
| `comment` | — | — | BS-LEX-012–014 | highlight |
| `identifier` | — | — | BS-LEX-015, 017, 018, 024, BS-LIT-020, BS-FUNC-013 | highlight, tags |
| `number` | — | — | BS-LIT-003, 005–012 | highlight |
| `string` | — | — | BS-LIT-015–017 | highlight |
| `true`, `false` | — | — | BS-LIT-001 | highlight |
| `invalid` | — | — | BS-LIT-002 | highlight |
| `source_literal` | — | — | BS-LIT-019 | highlight |
| `array_literal` | — | `expression`* | BS-ARRAY-001–003 | — |
| `associative_array_literal` | — | `associative_array_entry`* | BS-AA-001–004 | — |
| `associative_array_entry` | `key: identifier or string`, `value: expression` | — | BS-AA-001, 002, BS-LEX-024 | highlight (key) |
| `parenthesized_expression` | — | `expression` | BS-EXP-002 | — |
| `unary_expression` | `operator: - + not`, `operand: expression` | — | BS-LIT-004, BS-EXP-012, 018 | highlight (operator) |
| `binary_expression` | `left: expression`, `operator: ^ * / \ mod + - << >> = <> < > <= >= and or`, `right: expression` | — | BS-EXP-011–020 | highlight (operator) |
| `call_expression` | `function: identifier, member_expression, index_expression, call_expression, attribute_expression or parenthesized_expression`, `arguments: argument_list` | — | BS-EXP-003, 007, 010, BS-STMT-005, BS-LEX-022, 032 | highlight, tags (calls) |
| `argument_list` | — | `expression`* | BS-EXP-003, 024 | — |
| `member_expression` | `object: expression`, `property: identifier` | — | BS-EXP-004, 007, BS-LIT-014, BS-LEX-024 | highlight (property) |
| `index_expression` | `object: expression`, `index: expression`+ | — | BS-EXP-005, 007, BS-ARRAY-007 | — |
| `attribute_expression` | `object: expression`, `attribute: identifier` | — | BS-EXP-006, 007 | highlight (attribute) |
| `anonymous_function` | `parameters: parameter_list`, `return_type: type`?, `body: block` | — | BS-FUNC-009–011 | highlight |
| `assignment_statement` | `left: identifier, member_expression or index_expression`, `operator: = += -= *= /= \= <<= >>=`, `right: expression` | — | BS-STMT-001, 002, BS-EXP-010 | — |
| `update_statement` | `operand: identifier, member_expression or index_expression`, `operator: ++ --` | — | BS-STMT-003, 004 | — |
| `if_statement` | `condition: expression`, `consequence: block`, `alternative: else_if_clause* else_clause?` | — | BS-STMT-007–011, BS-LEX-032 | highlight, folds |
| `else_if_clause` | `condition: expression`, `consequence: block` | — | BS-STMT-010, 011 | — |
| `else_clause` | `body: block` | — | BS-STMT-007, 009–011 | — |
| `block` | — | `statement`* | BS-STMT-035 and every body | folds |
| `for_statement` | `counter: identifier`, `start: expression`, `end: expression`, `step: expression`?, `body: block` | — | BS-STMT-012, 013 | — |
| `for_each_statement` | `item: identifier`, `collection: expression`, `body: block` | — | BS-STMT-013, 015 | — |
| `while_statement` | `condition: expression`, `body: block` | — | BS-STMT-016, 020 | — |
| `exit_statement` | — | — | BS-STMT-018, 020 | highlight |
| `continue_statement` | — | — | BS-STMT-019 | highlight |
| `return_statement` | `value: expression`? | — | BS-STMT-023 | — |
| `print_statement` | — | `expression`* | BS-STMT-024–026, BS-LEX-031 | — |
| `dim_statement` | `name: identifier`, `dimension: expression`+ | — | BS-ARRAY-004, 005 | — |
| `goto_statement` | `label: identifier` | — | BS-STMT-027 | tags (label reference) |
| `label_statement` | `name: identifier` | — | BS-LEX-027, 028 | highlight, tags |
| `end_statement` | — | — | BS-STMT-029 | highlight |
| `stop_statement` | — | — | BS-STMT-030 | highlight |
| `library_statement` | `path: string` | — | BS-STMT-031, 032 | highlight |
| `throw_statement` | `value: expression` | — | BS-ERR-004 | — |
| `try_statement` | `body: block`, `handler: catch_clause` | — | BS-ERR-001, 002 | — |
| `catch_clause` | `variable: identifier`, `body: block` | — | BS-ERR-001 | — |
| `function_declaration` | `name: identifier`, `parameters: parameter_list`, `return_type: type`?, `body: block` | — | BS-FUNC-001–003 | highlight, tags (definition) |
| `parameter_list` | — | `parameter`* | BS-FUNC-005–007 | — |
| `parameter` | `name: identifier`, `default: expression`?, `type: type`? | — | BS-FUNC-005 | highlight |
| `type` | — | — | BS-TYPE-001 | highlight |
| `const_directive` | `name: identifier`, `value: identifier, true or false` | — | BS-COND-001 | highlight |
| `if_directive` | `condition: identifier, true or false`, `consequence: block or inactive_text`, `alternative: else_if_directive* else_directive?` | — | BS-COND-002, 006, 007 | highlight |
| `else_if_directive` | `condition: identifier, true or false`, `consequence: block or inactive_text` | — | BS-COND-003, 007 | highlight |
| `else_directive` | `body: block` | — | BS-COND-003 | highlight |
| `error_directive` | `message: error_message`? | — | BS-COND-004 | highlight |
| `error_message` | — | — | BS-COND-004 | highlight |
| `inactive_text` | — | `comment`* (other text is hidden) | BS-COND-007 | highlight |

`inactive_text` exists only if the ADR-0004 spike passes
([grammar-design.md §11](grammar-design.md#11-conditional-compilation));
otherwise it is removed from this section and never becomes public. Counts:
53 unconditional node types (`true` and `false` counted separately), 1
conditional, 2 supertypes, 33 field names.

Rules applied: every node cites at least one requirement; `block`,
`argument_list` and `parameter_list` are public because fields point to them
and queries match them, not for parser convenience; hidden helpers
(`_terminator`, `_newline`, `_inline_block`, the statement-level chains, the
optional-chaining variants, `_sep`, `_cc_condition`, `_inactive_line`) stay
internal; punctuation and keywords stay anonymous. Every planned node and
field is intended to survive to 1.0; `inactive_text` is the only planned node
whose existence depends on an experiment.

### Fields

| Field | Semantic purpose | Nodes |
|---|---|---|
| `name` | declared or referenced name | `function_declaration`, `parameter`, `dim_statement`, `label_statement`, `const_directive` |
| `parameters` | parameter list | `function_declaration`, `anonymous_function` |
| `return_type` | declared return type | `function_declaration`, `anonymous_function` |
| `body` | statement block | `function_declaration`, `anonymous_function`, `else_clause`, `for_statement`, `for_each_statement`, `while_statement`, `try_statement`, `catch_clause`, `else_directive` |
| `default` | default parameter value | `parameter` |
| `type` | declared parameter type | `parameter` |
| `left` | assignment target or left operand | `assignment_statement`, `binary_expression` |
| `right` | assigned value or right operand | `assignment_statement`, `binary_expression` |
| `operator` | operator token | `assignment_statement`, `binary_expression`, `unary_expression`, `update_statement` |
| `operand` | operand of a prefix or update operator | `unary_expression`, `update_statement` |
| `function` | called expression | `call_expression` |
| `arguments` | argument list | `call_expression` |
| `object` | accessed value | `member_expression`, `index_expression`, `attribute_expression` |
| `property` | member name | `member_expression` |
| `index` | one index expression, repeated for `a[i, j]` | `index_expression` |
| `attribute` | XML attribute name | `attribute_expression` |
| `key` | entry key | `associative_array_entry` |
| `value` | entry value, thrown value, returned value, constant value | `associative_array_entry`, `throw_statement`, `return_statement`, `const_directive` |
| `condition` | tested condition | `if_statement`, `else_if_clause`, `while_statement`, `if_directive`, `else_if_directive` |
| `consequence` | branch body | `if_statement`, `else_if_clause`, `if_directive`, `else_if_directive` |
| `alternative` | following branches | `if_statement`, `if_directive` |
| `counter` | FOR counter variable | `for_statement` |
| `start` | FOR initial value | `for_statement` |
| `end` | FOR final value | `for_statement` |
| `step` | FOR increment | `for_statement` |
| `item` | FOR EACH item variable | `for_each_statement` |
| `collection` | FOR EACH enumerated value | `for_each_statement` |
| `handler` | CATCH clause | `try_statement` |
| `variable` | CATCH exception variable | `catch_clause` |
| `dimension` | one DIM dimension, repeated | `dim_statement` |
| `label` | GOTO target | `goto_statement` |
| `path` | library path | `library_statement` |
| `message` | `#error` text | `error_directive` |

### Spelling and normalization

Equivalent spellings produce one public shape. The original spelling is
recoverable as shown.

| Construct | Spellings | Public shape | Spelling recoverable from |
|---|---|---|---|
| keywords | any letter case | anonymous token named by the lower-case word | source bytes of the token |
| PRINT | `PRINT`, `?` | `print_statement` | anonymous child `print` or `?` |
| block IF end | `END IF`, `ENDIF` | `if_statement` | anonymous children `end` `if`, or `endif` |
| ELSE IF | `ELSE IF`, `ELSEIF` | `else_if_clause` | anonymous children |
| single-line and block IF | one line, or a block closed by END IF | `if_statement` | presence of the closing keyword tokens |
| FOR terminator | `END FOR`, `NEXT` | `for_statement`, `for_each_statement` | anonymous children |
| WHILE end, EXIT WHILE | `END WHILE`, `ENDWHILE`; `EXIT WHILE`, `EXITWHILE` | `while_statement`, `exit_statement` | anonymous children |
| TRY end | `END TRY`, `ENDTRY` | `try_statement` | anonymous children |
| FUNCTION and SUB | `FUNCTION … END FUNCTION`/`ENDFUNCTION`, `SUB … END SUB`/`ENDSUB` | `function_declaration`, `anonymous_function` | anonymous keyword children |
| comments | `'…`, `REM …` | `comment` | node text |
| optional access | `.` `?.`, `[` `?[`, `(` `?(`, `@` `?@` | `member_expression`, `index_expression`, `call_expression`, `attribute_expression` | anonymous operator token (for calls, the first token of `argument_list`) |
| DIM brackets | `[…]`, `(…)` | `dim_statement` | anonymous children |
| numeric forms | decimal, hex, exponent, suffixes | `number` | node text |
| designators | `a`, `a$`, `a%`, … | `identifier` | node text |
| multidimensional index | `a[1,2]`, `a[1][2]` | **not normalized**: one `index_expression` with two `index` fields, or two nested nodes | tree shape |
| line endings | LF, CRLF | identical trees | source bytes only |
| multi-word keyword spacing | `END IF`, `END   IF` | identical trees | source bytes only |

### Requirement ↔ schema mapping

Every `documented` and `provisional` requirement, by category: **S**
structural (the listed planned node carries it), **N** normalized into the
listed node, **L** lexical-only (no public node by design; realised by tokens,
hidden rules or anonymous children).

| Requirement | Cat. | Planned shape |
|---|---|---|
| BS-LEX-001 | L | `kw()` tokens, `identifier` text |
| BS-LEX-002 | L | whitespace extra |
| BS-LEX-003 | L | whitespace extra |
| BS-LEX-004 | L | token boundaries |
| BS-LEX-005 | L | `_newline`, `_terminator` |
| BS-LEX-006 | L | `_newline` |
| BS-LEX-008 | S | `source_file` |
| BS-LEX-009 | L | `_terminator` runs |
| BS-LEX-010 | L | `_terminator` |
| BS-LEX-011 | L | `_terminator` runs |
| BS-LEX-012 | S | `comment` |
| BS-LEX-013 | N | `comment` |
| BS-LEX-014 | L | `comment` token shape |
| BS-LEX-015 | S | `identifier` |
| BS-LEX-017 | N | `identifier` |
| BS-LEX-018 | N | `identifier` |
| BS-LEX-021 | L | `kw()` tokens |
| BS-LEX-022 | S | `call_expression` on `identifier` |
| BS-LEX-024 | S | `identifier` as `member_expression` property and `associative_array_entry` key |
| BS-LEX-025 | L | contextual `kw()` tokens |
| BS-LEX-026 | L | `word` token |
| BS-LEX-027 | S | `label_statement` |
| BS-LEX-028 | S | `label_statement` |
| BS-LEX-029 | N | postfix nodes (anonymous `?.` `?@` `?[` `?(`) |
| BS-LEX-031 | N | `print_statement` |
| BS-LEX-032 | S | `if_statement` with a `call_expression` condition |
| BS-LEX-033 | L | runtime BOM skip; `string` and `comment` text |
| BS-LIT-001 | S | `true`, `false` |
| BS-LIT-002 | S | `invalid` |
| BS-LIT-003 | S | `number` |
| BS-LIT-004 | S | `unary_expression` |
| BS-LIT-005 | N | `number` |
| BS-LIT-006 | N | `number` |
| BS-LIT-007 | N | `number` |
| BS-LIT-008 | N | `number` |
| BS-LIT-009 | N | `number` |
| BS-LIT-010 | N | `number` |
| BS-LIT-011 | N | `number` |
| BS-LIT-012 | N | `number` |
| BS-LIT-014 | S | `member_expression` with a `number` or `string` object |
| BS-LIT-015 | S | `string` |
| BS-LIT-016 | N | `string` |
| BS-LIT-017 | L | `string` token shape |
| BS-LIT-019 | S | `source_literal` |
| BS-LIT-020 | S | `identifier` |
| BS-TYPE-001 | S | `type` |
| BS-EXP-001 | S | `expression` supertype |
| BS-EXP-002 | S | `parenthesized_expression` |
| BS-EXP-003 | S | `call_expression`, `argument_list` |
| BS-EXP-004 | S | `member_expression` |
| BS-EXP-005 | S | `index_expression` |
| BS-EXP-006 | S | `attribute_expression` |
| BS-EXP-007 | N | postfix nodes |
| BS-EXP-010 | S | `call_expression`, `assignment_statement` |
| BS-EXP-011 | S | `binary_expression` |
| BS-EXP-012 | S | `unary_expression` |
| BS-EXP-013 | S | `binary_expression` |
| BS-EXP-014 | S | `binary_expression` |
| BS-EXP-015 | S | `binary_expression` |
| BS-EXP-016 | S | `binary_expression` |
| BS-EXP-017 | S | `binary_expression` |
| BS-EXP-018 | S | `unary_expression` |
| BS-EXP-019 | S | `binary_expression` |
| BS-EXP-020 | S | `binary_expression`, `assignment_statement` |
| BS-EXP-021 | S | nesting of postfix nodes |
| BS-EXP-024 | L | `_newline` in `argument_list` |
| BS-EXP-025 | S | allowed `object` and `function` types |
| BS-STMT-001 | S | `assignment_statement` |
| BS-STMT-002 | N | `assignment_statement` (`operator`) |
| BS-STMT-003 | S | `update_statement` |
| BS-STMT-004 | S | `update_statement` |
| BS-STMT-005 | S | `call_expression` as a `statement` |
| BS-STMT-007 | N | `if_statement`, `block`, `else_clause` |
| BS-STMT-008 | N | `if_statement` |
| BS-STMT-009 | S | nested `if_statement` in `block` and `else_clause` |
| BS-STMT-010 | S | `if_statement`, `else_if_clause`, `else_clause` |
| BS-STMT-011 | L | clause header terminators |
| BS-STMT-012 | S | `for_statement` |
| BS-STMT-013 | N | `for_statement`, `for_each_statement` |
| BS-STMT-015 | S | `for_each_statement` |
| BS-STMT-016 | S | `while_statement` |
| BS-STMT-018 | S | `exit_statement` |
| BS-STMT-019 | S | `continue_statement` |
| BS-STMT-020 | N | `while_statement`, `exit_statement` |
| BS-STMT-022 | L | separate keyword tokens |
| BS-STMT-023 | S | `return_statement` |
| BS-STMT-024 | S | `print_statement` |
| BS-STMT-025 | S | `print_statement` |
| BS-STMT-026 | S | `print_statement` |
| BS-STMT-027 | S | `goto_statement` |
| BS-STMT-029 | S | `end_statement` |
| BS-STMT-030 | S | `stop_statement` |
| BS-STMT-031 | S | `library_statement` |
| BS-STMT-032 | S | `library_statement` |
| BS-STMT-033 | S | `source_file` |
| BS-STMT-035 | S | `block` |
| BS-STMT-036 | S | block-structured statement nodes |
| BS-FUNC-001 | S | `function_declaration`, `parameter_list` |
| BS-FUNC-002 | N | `function_declaration` |
| BS-FUNC-003 | N | `function_declaration` |
| BS-FUNC-005 | S | `parameter_list`, `parameter` |
| BS-FUNC-006 | L | `_newline` in `parameter_list` |
| BS-FUNC-007 | L | `_newline` in `parameter_list` |
| BS-FUNC-009 | S | `anonymous_function` |
| BS-FUNC-010 | S | `block` |
| BS-FUNC-011 | N | `anonymous_function` |
| BS-FUNC-013 | S | `identifier` |
| BS-ARRAY-001 | S | `array_literal` |
| BS-ARRAY-002 | L | `_sep` newlines |
| BS-ARRAY-003 | L | trailing `_sep` |
| BS-ARRAY-004 | S | `dim_statement` |
| BS-ARRAY-005 | N | `dim_statement` |
| BS-ARRAY-007 | S | `index_expression` (`index`+) |
| BS-AA-001 | S | `associative_array_literal`, `associative_array_entry` |
| BS-AA-002 | S | `associative_array_entry` with a `string` key |
| BS-AA-003 | L | `_sep` newlines |
| BS-AA-004 | L | trailing `_sep` |
| BS-ERR-001 | S | `try_statement`, `catch_clause` |
| BS-ERR-002 | S | nested `try_statement` |
| BS-ERR-004 | S | `throw_statement` |
| BS-ERR-005 | L | contextual `kw()` tokens |
| BS-COND-001 | S | `const_directive` |
| BS-COND-002 | S | `if_directive` |
| BS-COND-003 | S | `else_if_directive`, `else_directive` |
| BS-COND-004 | S | `error_directive`, `error_message` |
| BS-COND-005 | L | directive tokens |
| BS-COND-006 | S | `if_directive` as a `statement` |
| BS-COND-007 | S | `if_directive` with `inactive_text` (PASS) or KL-001 (FAIL) |
| BS-COND-008 | L | directive tokens and line terminators |

`invalid`, `unresolved` and `out-of-scope` rows need no shape. Requirements
without a planned shape: 0 (counts in the next line are checked
mechanically).

Mapped: 129 (S 78, N 24, L 27).
