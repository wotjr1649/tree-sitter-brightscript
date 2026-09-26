/**
 * @file Tree-sitter grammar for Roku BrightScript.
 * @license MIT
 *
 * Canonical design: docs/specs/grammar-design.md. Requirements (BS-*):
 * docs/specs/language-conformance.md. Planned public tree:
 * docs/specs/tree-schema.md. The external scanner (src/scanner.c) acts only
 * during error recovery (ADR-0008).
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
  // A called member (`a.b(1)`) is one call_expression, not a call of a member.
  METHOD: 11,
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

/** Directive word: `#` immediately followed by the word (BS-COND-005, 008). */
function directive(word, precedence = 0) {
  return alias(token(prec(precedence, new RegExp(`#${ci(word)}`))), `#${word}`);
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

  // ADR-0008: produced only by src/scanner.c during error recovery, never in a
  // valid parse. No rule uses `_recovery_sentinel`, so it is valid only in the
  // error state; `_raw_token_marker` is never produced. Order = scanner enum.
  externals: $ => [$._recovery_run, $._recovery_newline, $._recovery_sentinel, $._raw_token_marker],

  supertypes: $ => [$.statement, $.expression],

  inline: $ => [
    $._assignment_target, $._stmt_chain, $._stmt_callee, $._cc_condition,
    $._line, $._line_end, $._try_line, $._print_item, $._print_expression, $._sep,
  ],

  rules: {
    // ---------------------------------------------------------------- lines
    // BS-LEX-005, 008-011, BS-STMT-033 (grammar-design §2, §7): the last
    // statement needs no terminator. `_error_token_forms` never occurs (its
    // first token is never produced, ADR-0008); it only keeps raw token names.
    source_file: $ => seq(repeat($._line), optional($.statement), optional($._error_token_forms)),

    _line: $ => choice(seq($.statement, $._line_end), $._line_end),

    // A line ends with a terminator; during error recovery also with a
    // recovery line break, valid only here and in `_try_line`, not after a
    // block header and not inside brackets (ADR-0008).
    _line_end: $ => choice($._terminator, $._recovery_newline),

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
    block: $ => choice($._terminator, seq($._block_head, repeat($._line))),

    // The terminator and the first line as one parse-stack entry of an open
    // block, which bounds the end-of-input work on deeply nested unclosed
    // blocks (S07-M01, grammar-design §7).
    _block_head: $ => seq($._terminator, choice(seq($.statement, $._line_end), $._line_end)),

    // ------------------------------------------------------------ statements
    statement: $ => choice(
      $.assignment_statement,
      $.update_statement,
      alias($._stmt_call, $.call_expression),
      alias($._stmt_method_call, $.call_expression),
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
      $.throw_statement,
      $.try_statement,
      $.function_declaration,
      $.const_directive,
      $.if_directive,
      $.error_directive,
    ),

    // Statement-level chains (grammar-design §6): an identifier head, then
    // `.`, index access and `(` calls only (BS-STMT-001, 005, BS-EXP-008-010).
    _stmt_chain: $ => choice(
      $.identifier,
      alias($._stmt_member, $.member_expression),
      alias($._stmt_index, $.index_expression),
      alias($._stmt_call, $.call_expression),
      alias($._stmt_method_call, $.call_expression),
    ),

    _stmt_member: $ => seq(field('object', $._stmt_chain), '.', field('property', $.identifier)),

    _stmt_index: $ => seq(
      field('object', $._stmt_chain),
      alias($.open_bracket, '['), commaSep1(field('index', $.expression)), ']',
    ),

    _stmt_call: $ => seq(
      field('function', $._stmt_callee),
      field('arguments', alias($._stmt_arguments, $.argument_list)),
    ),

    // A called member is one call_expression (object, property, arguments).
    _stmt_callee: $ => choice(
      $.identifier,
      alias($._stmt_index, $.index_expression),
      alias($._stmt_call, $.call_expression),
      alias($._stmt_method_call, $.call_expression),
    ),

    _stmt_method_call: $ => seq(
      field('object', $._stmt_chain),
      '.',
      field('property', $.identifier),
      field('arguments', alias($._stmt_arguments, $.argument_list)),
    ),

    _stmt_arguments: $ => seq(alias($.open_parenthesis, '('), commaSep($.expression), ')'),

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
      alias($._stmt_method_call, $.call_expression),
      $.print_statement,
      $.return_statement,
      $.exit_statement,
      $.continue_statement,
      $.stop_statement,
      $.goto_statement,
      $.end_statement,
      $.throw_statement,
      $.dim_statement,
      alias($._single_line_if, $.if_statement),
    ),

    // BS-STMT-012, 013, 015, 036: each loop closes only with its own
    // terminator; bare NEXT ends the innermost FOR or FOR EACH.
    for_statement: $ => seq(
      $._for_header,
      field('body', $.block),
      choice(endKw('for'), kw('next')),
    ),

    for_each_statement: $ => seq(
      $._for_each_header,
      field('body', $.block),
      choice(endKw('for'), kw('next')),
    ),

    // BS-STMT-016, 017, 020: NEXT does not close a WHILE.
    while_statement: $ => seq(
      $._while_header,
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
    print_statement: $ => seq(choice(kw('print'), '?'), optional($._print_items)),

    // A balanced repetition (A5-01): a hidden rule whose body is a repetition
    // is its own binary tree. The error-recovery scanner keeps malformed item
    // runs from growing the recovery stack (B4-01, ADR-0008). Items name the
    // expression kinds directly, without an `expression` wrapper node per item.
    _print_items: $ => repeat1($._print_item),

    _print_item: $ => prec(PREC.LIST, choice($._print_expression, ',', ';')),

    _print_expression: $ => choice(
      $.identifier, $.number, $.string, $.true, $.false, $.invalid, $.source_literal,
      $.array_literal, $.associative_array_literal, $.parenthesized_expression,
      $.anonymous_function, $.unary_expression, $.binary_expression, $.call_expression,
      $.member_expression, $.index_expression, $.attribute_expression,
    ),

    // BS-ARRAY-004, 005: brackets or parentheses, one declarator.
    dim_statement: $ => seq(
      kw('dim'),
      field('name', $.identifier),
      choice(
        seq(alias($.open_bracket, '['), commaSep1(field('dimension', $.expression)), ']'),
        seq(alias($.open_parenthesis, '('), commaSep1(field('dimension', $.expression)), ')'),
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
      $.anonymous_function,
      $.unary_expression,
      $.binary_expression,
      $.call_expression,
      $.member_expression,
      $.index_expression,
      $.attribute_expression,
    ),

    // Not inlined: inlined, error recovery on runs of unclosed calls or indexes
    // grew quadratically in time and memory (grammar-design §5). POSTFIX
    // precedence keeps `print a [1]` an index expression (§14).
    _postfix_operand: $ => prec(PREC.POSTFIX, choice(
      $.identifier,
      $.parenthesized_expression,
      $.call_expression,
      $.member_expression,
      $.index_expression,
      $.attribute_expression,
    )),

    // BS-EXP-002.
    parenthesized_expression: $ => seq(alias($.open_parenthesis, '('), $.expression, ')'),

    // BS-EXP-003-007, 021: one postfix level applied left to right; the
    // optional forms share the node types (BS-LEX-029).
    call_expression: $ => choice(
      prec(PREC.POSTFIX, seq(
        field('function', $._callee),
        field('arguments', $.argument_list),
      )),
      // A called member (`a.b(1)`, `a?.b(1)`): the called name and the
      // argument list are siblings, which keeps queries on chains linear (S07-M03).
      prec(PREC.METHOD, seq(
        field('object', choice($._postfix_operand, $.number, $.string)),
        choice('.', '?.'),
        field('property', $.identifier),
        field('arguments', $.argument_list),
      )),
    ),

    _callee: $ => prec(PREC.POSTFIX, choice(
      $.identifier,
      $.parenthesized_expression,
      $.call_expression,
      $.index_expression,
      $.attribute_expression,
    )),

    argument_list: $ => seq(choice(alias($.open_parenthesis, '('), '?('), commaSep($.expression), ')'),

    member_expression: $ => prec(PREC.POSTFIX, seq(
      field('object', choice($._postfix_operand, $.number, $.string)),
      choice('.', '?.'),
      field('property', $.identifier),
    )),

    index_expression: $ => prec(PREC.POSTFIX, seq(
      field('object', $._postfix_operand),
      choice(alias($.open_bracket, '['), '?['),
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
      prec(PREC.UNARY, seq(
        field('operator', choice(alias($.minus_sign, '-'), alias($.plus_sign, '+'))),
        field('operand', $.expression),
      )),
      prec(PREC.NOT, seq(field('operator', alias($.not_operator, 'not')), field('operand', $.expression))),
    ),

    // The left operand of `^` as its own rule with POSTFIX precedence: the
    // tree and associativity are unchanged, but error recovery on runs of
    // malformed `^` no longer keeps a deep merged stack whose end-of-input
    // acceptance needs quadratic memory (grammar-design §5).
    _pow_left: $ => prec(PREC.POSTFIX, $.expression),

    // BS-EXP-011, 013-017, 019, 020.
    binary_expression: $ => choice(
      prec.right(PREC.EXPONENT, seq(
        field('left', $._pow_left), field('operator', '^'), field('right', $.expression),
      )),
      ...[
        [PREC.MULTIPLICATIVE, choice('*', '/', kw('mod'), '\\')],
        [PREC.ADDITIVE, choice(alias($.plus_sign, '+'), alias($.minus_sign, '-'))],
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
      alias($.open_bracket, '['),
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

    // ------------------------------------------------- error handling (§10)
    // BS-ERR-001-005: CATCH is required and takes one identifier.
    try_statement: $ => seq(
      alias($.try_keyword, 'try'),
      field('body', alias($._try_body, $.block)),
      field('handler', $.catch_clause),
      choice(endKw('try'), kw('endtry')),
    ),

    // A separate line rule keeps `catch` a keyword only directly in a TRY
    // body (grammar-design §4).
    _try_body: $ => seq($._terminator, repeat($._try_line)),

    _try_line: $ => choice(seq($.statement, $._line_end), $._line_end),

    catch_clause: $ => seq(kw('catch'), field('variable', $.identifier), field('body', $.block)),

    throw_statement: $ => seq(kw('throw'), field('value', $.expression)),

    // ----------------------------------------------------- functions (§8)
    // BS-FUNC-001-003, 005, 006: FUNCTION and SUB share the node; each closes
    // only with its own terminator (BS-STMT-036).
    function_declaration: $ => choice(
      seq(
        kw('function'),
        field('name', $.identifier),
        field('parameters', $.parameter_list),
        optional(seq(kw('as'), field('return_type', $.type))),
        field('body', $.block),
        choice(endKw('function'), kw('endfunction')),
      ),
      seq(
        kw('sub'),
        field('name', $.identifier),
        field('parameters', $.parameter_list),
        field('body', $.block),
        choice(endKw('sub'), kw('endsub')),
      ),
    ),

    // BS-FUNC-009-011.
    anonymous_function: $ => choice(
      seq(
        $._anonymous_function_header,
        field('body', $.block),
        choice(endKw('function'), kw('endfunction')),
      ),
      seq(
        kw('sub'),
        field('parameters', $.parameter_list),
        field('body', $.block),
        choice(endKw('sub'), kw('endsub')),
      ),
    ),

    // Headers of blocks that can stay open: one parse-stack entry each, which
    // bounds the end-of-input work on deeply nested unclosed blocks (S07-M01).
    _for_header: $ => seq(
      kw('for'),
      field('counter', $.identifier),
      '=',
      field('start', $.expression),
      kw('to'),
      field('end', $.expression),
      optional(seq(kw('step'), field('step', $.expression))),
    ),

    _for_each_header: $ => seq(
      kw('for'),
      kw('each'),
      field('item', $.identifier),
      kw('in'),
      field('collection', $.expression),
    ),

    _while_header: $ => seq(kw('while'), field('condition', $.expression)),

    _anonymous_function_header: $ => seq(
      kw('function'),
      field('parameters', $.parameter_list),
      optional(seq(kw('as'), field('return_type', $.type))),
    ),

    // A line break is allowed after a comma only (BS-FUNC-006).
    parameter_list: $ => seq(
      alias($.open_parenthesis, '('),
      optional(seq($.parameter, repeat(seq(',', repeat($._newline), $.parameter)))),
      ')',
    ),

    parameter: $ => seq(
      field('name', $.identifier),
      optional(seq('=', field('default', $.expression))),
      optional(seq(kw('as'), field('type', $.type))),
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

    // ------------------------------------- conditional compilation (§11)
    // BS-COND-001-006, 008, 012, 013: directives are statements; conditions
    // are never evaluated and every branch body is an ordinary block.
    const_directive: $ => seq(
      directive('const'),
      field('name', $.identifier),
      '=',
      field('value', choice($.identifier, $.true, $.false)),
    ),

    // BS-COND-007: a literal `false` branch is opaque `inactive_text`
    // (ADR-0004 spike, design V1; grammar-design §11).
    if_directive: $ => seq(
      directive('if', 1),
      choice(
        seq(field('condition', $._cc_condition), field('consequence', $.block)),
        seq(field('condition', $.false), field('consequence', $.inactive_text)),
      ),
      repeat(field('alternative', $.else_if_directive)),
      optional(field('alternative', $.else_directive)),
      directive('end', 1),
      kw('if'),
    ),

    else_if_directive: $ => seq(
      directive('else', 1),
      kw('if'),
      choice(
        seq(field('condition', $._cc_condition), field('consequence', $.block)),
        seq(field('condition', $.false), field('consequence', $.inactive_text)),
      ),
    ),

    else_directive: $ => seq(directive('else', 1), field('body', $.block)),

    error_directive: $ => seq(directive('error'), optional(field('message', $.error_message))),

    // BS-COND-004: free text to the end of the line, apostrophes included.
    error_message: _ => token(prec(1, /[^ \t\r\n][^\r\n]*/)),

    _cc_condition: $ => choice($.identifier, $.true),

    // Region lines are hidden `_inactive_line` tokens. Lines starting with `'`
    // or whole-word REM match `comment` at equal length and precedence, and
    // `comment` is declared first, so they stay `comment` children. Nested
    // `#if` blocks are balanced by `_inactive_if`; `#if`, `#else` and `#end`
    // have lexical precedence 1 so they are recognised inside the region.
    inactive_text: $ => seq($._newline, repeat($._inactive_item)),

    _inactive_item: $ => choice($._inactive_line, $._newline, $._inactive_if),

    // A `#` line is text unless it starts with the whole word `#if`, `#else`
    // or `#end` (`#elseif` and `#endif` included): the second alternative never
    // matches those words as a prefix, and a longer word (`#ifdef`, `#elsewhere`,
    // `#endregion`) is text through the third, whose precedence 2 beats the
    // completed directive word (grammar-design §11).
    _inactive_line: _ => token(choice(
      prec(0, /[^ \t\r\n#][^\r\n]*/),
      prec(0, /#([^iIeE\r\n][^\r\n]*|[iI]([^fF\r\n][^\r\n]*)?|[eE]([^lLnN\r\n][^\r\n]*|[lL]([^sS\r\n][^\r\n]*|[sS]([^eE\r\n][^\r\n]*)?)?|[nN]([^dD\r\n][^\r\n]*)?)?)?/),
      prec(2, /#([iI][fF][A-Za-z0-9_]|([eE][lL][sS][eE]|[eE][nN][dD])([A-HJ-Za-hj-z0-9_]|[iI]([^fF\r\n]|[fF][A-Za-z0-9_])))[^\r\n]*/),
    )),

    _inactive_if: $ => seq(
      directive('if', 1), optional($._inactive_line), $._newline,
      repeat($._inactive_item),
      repeat(seq(directive('else', 1), optional($._inactive_line), $._newline, repeat($._inactive_item))),
      directive('end', 1), kw('if'),
    ),

    // ADR-0008 error-only raw forms of tokens that can stay on the parse stack
    // in long runs with no named node between them. Productions use them under
    // their anonymous names; `_error_token_forms` uses them unaliased, so the
    // raw names survive and appear only inside ERROR nodes (tree-schema.md).
    _error_token_forms: $ => seq($._raw_token_marker, choice(
      $.open_parenthesis, $.open_bracket, $.minus_sign, $.plus_sign, $.not_operator, $.try_keyword,
    )),

    open_parenthesis: _ => '(',
    open_bracket: _ => '[',
    minus_sign: _ => '-',
    plus_sign: _ => '+',
    not_operator: _ => new RegExp(ci('not')),
    try_keyword: _ => new RegExp(ci('try')),

    // BS-LEX-015, 017, 018: the designator is part of the identifier. Defined
    // last: an equal-length match goes to the earlier token, so every keyword
    // token wins its tie with `identifier` (grammar-design §4).
    identifier: _ => /[A-Za-z_][A-Za-z0-9_]*[$%!#&]?/,
  },
});
