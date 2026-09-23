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
  LIST: -1,
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

/** Two-word block terminator as one token, e.g. `end if` (grammar-design §3, BS-STMT-022). */
function endKw(word) {
  return alias(token(new RegExp(`${ci('end')}[ \\t]+${ci(word)}`)), `end ${word}`);
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

    // BS-STMT-035: a block starts with the terminator that ends its header.
    block: $ => seq($._terminator, repeat($._line)),

    // ------------------------------------------------------------ statements
    statement: $ => choice(
      $.assignment_statement,
      $.update_statement,
      alias($._stmt_call, $.call_expression),
      $.if_statement,
      $.for_statement,
      $.for_each_statement,
      $.while_statement,
      $.exit_statement,
      $.continue_statement,
      $.return_statement,
      $.print_statement,
      $.dim_statement,
      $.goto_statement,
      $.label_statement,
      $.end_statement,
      $.stop_statement,
      $.library_statement,
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

    // BS-STMT-007-011, BS-LEX-032 (grammar-design §6): after the condition and
    // optional THEN, a terminator (or a comment before it) selects the block
    // form and a statement start selects the single-line form.
    if_statement: $ => choice($._block_if, $._single_line_if),

    _block_if: $ => seq(
      kw('if'),
      field('condition', $.expression),
      optional(kw('then')),
      field('consequence', $.block),
      repeat(field('alternative', $.else_if_clause)),
      optional(field('alternative', $.else_clause)),
      choice(endKw('if'), kw('endif')),
    ),

    else_if_clause: $ => seq(
      choice(seq(kw('else'), kw('if')), kw('elseif')),
      field('condition', $.expression),
      optional(kw('then')),
      field('consequence', $.block),
    ),

    else_clause: $ => seq(kw('else'), field('body', $.block)),

    // Right precedence: `:` and ELSE continue the innermost single-line IF.
    _single_line_if: $ => prec.right(PREC.LIST, seq(
      kw('if'),
      field('condition', $.expression),
      optional(kw('then')),
      field('consequence', alias($._inline_block, $.block)),
      optional(field('alternative', alias($._inline_else, $.else_clause))),
    )),

    _inline_else: $ => seq(kw('else'), field('body', alias($._inline_block, $.block))),

    _inline_block: $ => prec.right(PREC.LIST, seq(
      $._inline_statement,
      repeat(seq(repeat1(':'), $._inline_statement)),
    )),

    _inline_statement: $ => choice(
      $.assignment_statement,
      $.update_statement,
      alias($._stmt_call, $.call_expression),
      $.print_statement,
      $.return_statement,
      $.exit_statement,
      $.continue_statement,
      $.stop_statement,
      $.goto_statement,
      $.end_statement,
      $.dim_statement,
      alias($._single_line_if, $.if_statement),
    ),

    // BS-STMT-012, 013, 015, 036: each loop closes only with its own
    // terminator; bare NEXT ends the innermost FOR or FOR EACH.
    for_statement: $ => seq(
      kw('for'),
      field('counter', $.identifier),
      '=',
      field('start', $.expression),
      kw('to'),
      field('end', $.expression),
      optional(seq(kw('step'), field('step', $.expression))),
      field('body', $.block),
      choice(endKw('for'), kw('next')),
    ),

    for_each_statement: $ => seq(
      kw('for'),
      kw('each'),
      field('item', $.identifier),
      kw('in'),
      field('collection', $.expression),
      field('body', $.block),
      choice(endKw('for'), kw('next')),
    ),

    // BS-STMT-016, 017, 020: NEXT does not close a WHILE.
    while_statement: $ => seq(
      kw('while'),
      field('condition', $.expression),
      field('body', $.block),
      choice(endKw('while'), kw('endwhile')),
    ),

    // BS-STMT-018-020, 037.
    exit_statement: $ => choice(seq(kw('exit'), choice(kw('for'), kw('while'))), kw('exitwhile')),

    continue_statement: $ => seq(kw('continue'), choice(kw('for'), kw('while'))),

    // BS-STMT-023.
    return_statement: $ => seq(kw('return'), optional(field('value', $.expression))),

    // BS-STMT-024-026, 039, BS-LEX-031, 035: an item extends as far as the
    // expression grammar allows (LIST precedence is below every operator).
    print_statement: $ => seq(choice(kw('print'), '?'), repeat($._print_item)),

    _print_item: $ => prec(PREC.LIST, choice($.expression, ',', ';')),

    // BS-ARRAY-004, 005: brackets or parentheses, one declarator.
    dim_statement: $ => seq(
      kw('dim'),
      field('name', $.identifier),
      choice(
        seq('[', commaSep1(field('dimension', $.expression)), ']'),
        seq('(', commaSep1(field('dimension', $.expression)), ')'),
      ),
    ),

    // BS-STMT-027, BS-LEX-027, 028: a label is a whole statement.
    goto_statement: $ => seq(kw('goto'), field('label', $.identifier)),

    label_statement: $ => seq(field('name', $.identifier), ':'),

    // BS-STMT-029, 030: `end` alone; the `end X` terminators are single tokens.
    end_statement: _ => kw('end'),

    stop_statement: _ => kw('stop'),

    // BS-STMT-031, 032.
    library_statement: $ => seq(kw('library'), field('path', $.string)),

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
