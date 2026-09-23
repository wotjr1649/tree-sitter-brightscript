# Known regressions

Concrete defects observed in earlier BrightScript grammars (Level 5 evidence,
[source-policy.md](../provenance/source-policy.md)) that this grammar must not
repeat. Each entry names the check that keeps it from recurring. Entries are
never deleted; a legacy-only entry stays as history.

The legacy grammar is `ajdelcimmuto/tree-sitter-brightscript`; identities are
in [upstream-sources.md](../provenance/upstream-sources.md). It was inspected
read-only; nothing was copied.

| ID | Symptom | Evidence | Guarding check | Could recur here |
|---|---|---|---|---|
| KR-001 | Committed generated parser did not match the grammar and queries: a shipped query referenced node `m`, which the committed `src/parser.c` did not contain | legacy `253fdfaa` (170 symbols, no `m`), fixed only by regeneration in `0c534d56` | V0 drift check over every generated file; V4 query compilation against the committed parser | yes — guarded by V0 and V4 |
| KR-002 | Newlines treated as whitespace, so line structure (statement ends, single-line IF extent) is lost | legacy `grammar.js` @ `0c534d56`: `extras` contains a newline pattern and `\s` | fixtures `BS-LEX-005: one statement per line`, `BS-STMT-007: colon-separated statements in a single-line branch`, `BS-STMT-008: THEN followed by a comment starts a block IF`; grammar-design §2 forbids newlines in extras | yes — if `\s` is added to extras |
| KR-003 | `NOT` bound tighter than comparisons (`not a = b` parsed as `(not a) = b`) | legacy `grammar.js` @ `0c534d56`: logical-not precedence above comparison precedence | fixture `BS-EXP-018: NOT below comparison and above AND` | yes — guarded by W04 |
| KR-004 | `AND` and `OR` at one level (`a or b and c` parsed as `(a or b) and c`) | legacy `grammar.js` @ `0c534d56`: one logical rule for both operators | fixture `BS-EXP-019: AND binds tighter than OR` | yes — guarded by W04 |
| KR-005 | Any block terminator closed any block (`function … end if` accepted) | legacy `grammar.js` @ `0c534d56`: one shared terminator choice used by every block | fixtures `BS-STMT-036: nested blocks close with their own terminators`, `BS-STMT-036: END IF closing a FOR body` | yes — if terminators are shared |
| KR-006 | Documented syntax missing: `:` separators, labels, `DIM`, hex and suffixed numbers, type designators | legacy `grammar.js` @ `0c534d56` (ADR-0001 context) | fixtures of BS-LEX-010, BS-LEX-017, BS-LEX-027, BS-ARRAY-004, BS-LIT-005, BS-LIT-011, BS-LIT-012 | no — each is a documented requirement with fixtures |
