/**
 * @file Error-recovery scanner for the BrightScript grammar (ADR-0008).
 * @license MIT
 *
 * It returns a token only while the parser is recovering from an error, which
 * it recognises by the validity of RECOVERY_SENTINEL: no grammar rule uses that
 * token, so the runtime marks it valid only in its error state. A valid parse
 * never receives a token from here. The scanner keeps no state.
 */

#include "tree_sitter/parser.h"

/* Order = `externals` in grammar.js. */
enum TokenType {
  RECOVERY_RUN,      /* the rest of the line, as one token */
  RECOVERY_NEWLINE,  /* a line break, valid only where a line of statements ends */
  RECOVERY_SENTINEL, /* never produced; valid only in the error state */
  RAW_TOKEN_MARKER,  /* never produced; keeps raw token names (grammar.js) */
};

void *tree_sitter_brightscript_external_scanner_create(void) { return NULL; }

void tree_sitter_brightscript_external_scanner_destroy(void *payload) { (void)payload; }

unsigned tree_sitter_brightscript_external_scanner_serialize(void *payload, char *buffer) {
  (void)payload;
  (void)buffer;
  return 0;
}

void tree_sitter_brightscript_external_scanner_deserialize(void *payload, const char *buffer, unsigned length) {
  (void)payload;
  (void)buffer;
  (void)length;
}

bool tree_sitter_brightscript_external_scanner_scan(void *payload, TSLexer *lexer, const bool *valid_symbols) {
  (void)payload;
  if (!valid_symbols[RECOVERY_SENTINEL]) return false;

  while (lexer->lookahead == ' ' || lexer->lookahead == '\t') lexer->advance(lexer, true);
  if (lexer->eof(lexer)) return false;

  bool consumed = false;

  /* A line break: LF or CR LF. A lone CR is not a line break (BS-LEX-007). */
  if (lexer->lookahead == '\n' || lexer->lookahead == '\r') {
    bool cr = lexer->lookahead == '\r';
    lexer->advance(lexer, false);
    if (!cr || lexer->lookahead == '\n') {
      if (cr) lexer->advance(lexer, false);
      lexer->mark_end(lexer);
      lexer->result_symbol = RECOVERY_NEWLINE;
      return true;
    }
    consumed = true; /* the lone CR starts a run */
  }

  /* A run: up to a line break, a `'` comment outside a string literal, or the
     end of input. Every iteration consumes one character or stops. */
  bool in_string = false;
  for (;;) {
    if (lexer->eof(lexer) || lexer->lookahead == '\n') break;
    if (lexer->lookahead == '\r') {
      lexer->mark_end(lexer);
      lexer->advance(lexer, false);
      if (lexer->lookahead == '\n') {
        lexer->result_symbol = RECOVERY_RUN;
        return true; /* ends before the CR LF */
      }
      consumed = true;
      continue;
    }
    if (!in_string && lexer->lookahead == '\'') break;
    if (lexer->lookahead == '"') in_string = !in_string;
    lexer->advance(lexer, false);
    consumed = true;
  }
  if (!consumed) return false;
  lexer->mark_end(lexer);
  lexer->result_symbol = RECOVERY_RUN;
  return true;
}
