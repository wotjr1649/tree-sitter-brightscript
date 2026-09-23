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

// grammar-design §5 (internal mapping of the official precedence table).
const PREC = {
  OR: 1,
  AND: 2,
  NOT: 3,
  COMPARE: 4,
  SHIFT: 5,
  ADDITIVE: 6,
  MULTIPLICATIVE: 7,
  UNARY: 8,
  EXPONENT: 9,
  POSTFIX: 10,
};

/** Regex source matching `word` in any letter case. */
function ci(word) {
  return word.replace(/[a-z]/gi, c => `[${c.toLowerCase()}${c.toUpperCase()}]`);
}

/** Case-insensitive keyword, aliased to its lower-case anonymous name (BS-LEX-001). */
function kw(word) {
  return alias(new RegExp(ci(word)), word);
}

function commaSep1(rule) {
  return seq(rule, repeat(seq(',', rule)));
}

function commaSep(rule) {
  return optional(commaSep1(rule));
}

module.exports = grammar({
  name: 'brightscript',

  // BS-LEX-002, 003: space and tab only. Newlines are tokens (grammar-design §2).
  extras: $ => [/[ \t]/, $.comment],

  // BS-LEX-026: keyword boundaries (grammar-design §3, §4).
  word: $ => $.identifier,

  supertypes: $ => [$.statement, $.expression],

  inline: $ => [$._postfix_operand, $._assignment_target, $._stmt_chain],

  rules: {
    // ---------------------------------------------------------------- lines
    // BS-LEX-005, 008-011, BS-STMT-033 (grammar-design §2, §7): the last
    // statement needs no terminator.
    source_file: $ => seq(repeat($._line), optional($.statement)),

    _line: $ => choice(seq($.statement, $._terminator), $._terminator),

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

    // ------------------------------------------------------------ statements
    statement: $ => choice(
      $.assignment_statement,
      $.update_statement,
      alias($._stmt_call, $.call_expression),
      $.dim_statement,
    ),

    // Statement-level chains (grammar-design §6): an identifier head, then
    // `.`, index access and `(` calls only (BS-STMT-001, 005, BS-EXP-008-010).
    _stmt_chain: $ => choice(
      $.identifier,
      alias($._stmt_member, $.member_expression),
      alias($._stmt_index, $.index_expression),
      alias($._stmt_call, $.call_expression),
    ),

    _stmt_member: $ => seq(field('object', $._stmt_chain), '.', field('property', $.identifier)),

    _stmt_index: $ => seq(
      field('object', $._stmt_chain),
      '[', commaSep1(field('index', $.expression)), ']',
    ),

    _stmt_call: $ => seq(
      field('function', $._stmt_chain),
      field('arguments', alias($._stmt_arguments, $.argument_list)),
    ),

    _stmt_arguments: $ => seq('(', commaSep($.expression), ')'),

    _assignment_target: $ => choice(
      $.identifier,
      alias($._stmt_member, $.member_expression),
      alias($._stmt_index, $.index_expression),
    ),

    // BS-STMT-001, 002, BS-EXP-020: `=` here is assignment; inside an
    // expression it is comparison.
    assignment_statement: $ => seq(
      field('left', $._assignment_target),
      field('operator', choice('=', '+=', '-=', '*=', '/=', '\\=', '<<=', '>>=')),
      field('right', $.expression),
    ),

    // BS-STMT-003, 004.
    update_statement: $ => seq(
      field('operand', $._assignment_target),
      field('operator', choice('++', '--')),
    ),

    // BS-ARRAY-004, 005: brackets or parentheses, one declarator.
    dim_statement: $ => seq(
      kw('dim'),
      field('name', $.identifier),
      choice(
        seq('[', commaSep1(field('dimension', $.expression)), ']'),
        seq('(', commaSep1(field('dimension', $.expression)), ')'),
      ),
    ),

    // ---------------------------------------------------- expressions (§5)
    expression: $ => choice(
      $.identifier,
      $.number,
      $.string,
      $.true,
      $.false,
      $.invalid,
      $.source_literal,
      $.array_literal,
      $.associative_array_literal,
      $.parenthesized_expression,
      $.unary_expression,
      $.binary_expression,
      $.call_expression,
      $.member_expression,
      $.index_expression,
      $.attribute_expression,
    ),

    _postfix_operand: $ => choice(
      $.identifier,
      $.parenthesized_expression,
      $.call_expression,
      $.member_expression,
      $.index_expression,
      $.attribute_expression,
    ),

    // BS-EXP-002.
    parenthesized_expression: $ => seq('(', $.expression, ')'),

    // BS-EXP-003-007, 021: one postfix level applied left to right; the
    // optional forms share the node types (BS-LEX-029).
    call_expression: $ => prec(PREC.POSTFIX, seq(
      field('function', $._postfix_operand),
      field('arguments', $.argument_list),
    )),

    argument_list: $ => seq(choice('(', '?('), commaSep($.expression), ')'),

    member_expression: $ => prec(PREC.POSTFIX, seq(
      field('object', choice($._postfix_operand, $.number, $.string)),
      choice('.', '?.'),
      field('property', $.identifier),
    )),

    index_expression: $ => prec(PREC.POSTFIX, seq(
      field('object', $._postfix_operand),
      choice('[', '?['),
      commaSep1(field('index', $.expression)),
      ']',
    )),

    attribute_expression: $ => prec(PREC.POSTFIX, seq(
      field('object', $._postfix_operand),
      choice('@', '?@'),
      field('attribute', $.identifier),
    )),

    // BS-EXP-012, 018, 027, BS-LIT-004: a prefix operator binds its operand at
    // its own level, also as the right operand of a tighter operator.
    unary_expression: $ => choice(
      prec(PREC.UNARY, seq(field('operator', choice('-', '+')), field('operand', $.expression))),
      prec(PREC.NOT, seq(field('operator', kw('not')), field('operand', $.expression))),
    ),

    // BS-EXP-011, 013-017, 019, 020.
    binary_expression: $ => choice(
      prec.right(PREC.EXPONENT, seq(
        field('left', $.expression), field('operator', '^'), field('right', $.expression),
      )),
      ...[
        [PREC.MULTIPLICATIVE, choice('*', '/', kw('mod'), '\\')],
        [PREC.ADDITIVE, choice('+', '-')],
        [PREC.SHIFT, choice('<<', '>>')],
        [PREC.COMPARE, choice('=', '<>', '<', '>', '<=', '>=')],
        [PREC.AND, kw('and')],
        [PREC.OR, kw('or')],
      ].map(([p, operator]) => prec.left(p, seq(
        field('left', $.expression), field('operator', operator), field('right', $.expression),
      ))),
    ),

    // ------------------------------------------------ collections (§9)
    // BS-ARRAY-001-003: line breaks after `[`, between elements (with or
    // without commas) and before `]`; a trailing separator is tolerated.
    array_literal: $ => seq(
      '[',
      repeat($._newline),
      optional(seq($.expression, repeat(seq($._sep, $.expression)), optional($._sep))),
      ']',
    ),

    // BS-AA-001-004: the same separator rules for entries.
    associative_array_literal: $ => seq(
      '{',
      repeat($._newline),
      optional(seq(
        $.associative_array_entry,
        repeat(seq($._sep, $.associative_array_entry)),
        optional($._sep),
      )),
      '}',
    ),

    _sep: $ => choice(seq(',', repeat($._newline)), repeat1($._newline)),

    // BS-AA-001, 002, BS-LEX-024: keyword words are identifier keys by
    // context-aware lexing.
    associative_array_entry: $ => seq(
      field('key', choice($.identifier, $.string)),
      ':',
      field('value', $.expression),
    ),

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
