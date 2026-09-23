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

module.exports = grammar({
  name: 'brightscript',

  // BS-LEX-002, 003: space and tab only. Newlines are tokens (grammar-design §2).
  extras: $ => [/[ \t]/, $.comment],

  rules: {
    // BS-LEX-008 (grammar-design §2).
    source_file: $ => repeat($._terminator),

    // BS-LEX-005, 006, 010.
    _terminator: $ => choice($._newline, ':'),
    _newline: _ => /\r?\n/,

    // BS-LEX-012–014: `'` or whole-word REM, to the end of the line.
    comment: _ => token(choice(
      /'[^\r\n]*/,
      /[rR][eE][mM]([ \t][^\r\n]*)?/,
    )),
  },
});
