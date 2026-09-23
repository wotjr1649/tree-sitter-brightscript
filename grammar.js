/**
 * @file Tree-sitter grammar for Roku BrightScript.
 * @license MIT
 *
 * Canonical design: docs/specs/grammar-design.md. Requirements (BS-*):
 * docs/specs/language-conformance.md. Planned public tree:
 * docs/specs/tree-schema.md.
 */

/// <reference types="tree-sitter-cli/dsl" />
// @ts-check

/** Regex source matching `word` in any letter case. */
function ci(word) {
  return word.replace(/[a-z]/gi, c => `[${c.toLowerCase()}${c.toUpperCase()}]`);
}

/** Case-insensitive keyword, aliased to its lower-case anonymous name (BS-LEX-001). */
function kw(word) {
  return alias(new RegExp(ci(word)), word);
}

module.exports = grammar({
  name: 'brightscript',

  // BS-LEX-002, 003: space and tab only. Newlines are tokens (grammar-design §2).
  extras: $ => [/[ \t]/, $.comment],

  // BS-LEX-026: keyword boundaries (grammar-design §3, §4).
  word: $ => $.identifier,

  rules: {
    // BS-LEX-008 (grammar-design §2).
    source_file: $ => repeat($._terminator),

    // BS-LEX-005, 006, 010.
    _terminator: $ => choice($._newline, ':'),
    _newline: _ => /\r?\n/,

    // BS-LEX-012–014: `'` or whole-word REM, to the end of the line. Declared
    // before `identifier`: for exactly `rem` both tokens match three characters
    // and the earlier token wins (REM mechanism 1, grammar-design §3).
    comment: _ => token(choice(
      /'[^\r\n]*/,
      /[rR][eE][mM]([ \t][^\r\n]*)?/,
    )),

    // BS-TYPE-001: one rule for parameter and return types.
    type: _ => choice(
      kw('integer'), kw('float'), kw('double'), kw('boolean'), kw('string'),
      kw('object'), kw('dynamic'), kw('function'), kw('void'),
    ),

    // --------------------------------------------------- literals (§3)
    // BS-LIT-003, 005-012: decimal (fraction, exponent `e`/`d`, suffix) and hex.
    // A digit run followed by `.` and a letter is `number` then `.` (BS-LIT-014).
    number: _ => token(choice(
      /(\d+(\.\d+)?|\.\d+)([eEdD][+-]?\d+)?[%!#&]?/,
      /&[hH][0-9a-fA-F]+&?/,
    )),

    // BS-LIT-015-017: one line; `""` is the only escape.
    string: _ => /"([^"\r\n]|"")*"/,

    // BS-LIT-001, 002, 019.
    true: _ => new RegExp(ci('true')),
    false: _ => new RegExp(ci('false')),
    invalid: _ => new RegExp(ci('invalid')),
    source_literal: _ => new RegExp(ci('line_num')),

    // BS-LEX-015, 017, 018: the designator is part of the identifier. Defined
    // last: an equal-length match goes to the earlier token, so every keyword
    // token wins its tie with `identifier` (grammar-design §4).
    identifier: _ => /[A-Za-z_][A-Za-z0-9_]*[$%!#&]?/,
  },
});
