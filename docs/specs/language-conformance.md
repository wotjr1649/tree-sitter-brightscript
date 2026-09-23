# Language conformance registry

The single place where BrightScript language requirements are defined and
traced. Grammar rules, fixtures and release claims refer to the IDs below.

Status: **no requirements promoted yet.** Promotion from the local research
inventory starts in Session 02. This document fixes the format so that
promotion does not re-decide it.

## Traceability chain

Level 1/2 evidence → requirement (`BS-*`) → grammar rule → positive fixture →
negative or recovery fixture (where the acceptance policy allows one) → status.

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
from `_ref` (`LEX-01`, `AMB-20`, …) are never used as IDs.

## Record fields

| Field | Content |
|---|---|
| ID | `BS-<AREA>-<NNN>` |
| Requirement | Paraphrased, testable statement |
| Evidence | Level 1 page + section + snapshot ID; Level 2 record if any; Level 4 references if used |
| Since | Roku OS version, `baseline` (no version stated) or `unknown` |
| Status | see below |
| Grammar | rule name(s) |
| Positive fixtures | corpus test names |
| Negative / recovery fixtures | corpus test names, or `n/a` with reason |
| Coverage | `none`, `partial`, `covered` |
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

## Fixture naming

Corpus test names start with the requirement ID they exercise, for example
`BS-STMT-004: FOR loop with STEP`. A fixture may cite several IDs.

## Registry

Empty until Session 02.
