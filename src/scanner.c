/**
 * @file Error-recovery scanner for the BrightScript grammar (ADR-0008).
 * @license MIT
 *
 * It returns a token only while the parser is recovering from an error, which
 * it recognises by the validity of RECOVERY_SENTINEL: no grammar rule uses that
 * token, so the runtime marks it valid only in its error state. A valid parse
 * never receives a token from here. The one exception is the last unit of an
 * input whose final line was malformed and has no line break: after recovery
 * moved back to a line end, the runtime lexes it again in a normal state, and
 * the state byte of the run before it marks it as that line end.
 */

#include "tree_sitter/alloc.h"
#include "tree_sitter/parser.h"

/* Order = `externals` in grammar.js. */
enum TokenType {
  RECOVERY_RUN,      /* malformed text up to the end of the line, as one token */
  RECOVERY_NEWLINE,  /* a line break, valid only where a line or a block body may begin */
  RECOVERY_SENTINEL, /* never produced; valid only in the error state */
  RAW_TOKEN_MARKER,  /* never produced; keeps raw token names (grammar.js) */
};

typedef struct {
  /* The run of this token stopped before the last unit of the input, which ends the line. */
  unsigned char eof_line_end;
} State;

void *tree_sitter_brightscript_external_scanner_create(void) { return ts_calloc(1, sizeof(State)); }

void tree_sitter_brightscript_external_scanner_destroy(void *payload) { ts_free(payload); }

unsigned tree_sitter_brightscript_external_scanner_serialize(void *payload, char *buffer) {
  State *state = payload;
  if (!state->eof_line_end) return 0;
  buffer[0] = 1;
  return 1;
}

void tree_sitter_brightscript_external_scanner_deserialize(void *payload, const char *buffer, unsigned length) {
  State *state = payload;
  state->eof_line_end = length == 1 && buffer[0] == 1;
}

static bool blank(int32_t c) { return c == ' ' || c == '\t'; }

static bool word_char(int32_t c) {
  return (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9') || c == '_' || c >= 0x80;
}

static bool word_start(int32_t c) { return word_char(c) && !(c >= '0' && c <= '9'); }

/* An operator that cannot begin a valid line; `+` and `-` begin one only as the sign of an
   element on a continuation line inside brackets. */
static bool operator_start(int32_t c) {
  return c == '+' || c == '-' || c == '*' || c == '/' || c == '\\' || c == '^' || c == '=' || c == '<' ||
         c == '>' || c == ';' || c == '@';
}

/* A short malformed rest of a line before a line that may begin a statement is recovered token by
   token, as without this scanner: a cheap run there lets a recovery version skip the line break and
   take the next line into the malformed statement. */
enum { MIN_RUN = 16 };

/* Called at the end of a run (a line break or a `'` comment): reads ahead past the rest of the line
   and blank lines; true if the next line begins like a statement or a comment. */
static bool statement_follows(TSLexer *lexer) {
  for (;;) {
    while (!lexer->eof(lexer) && lexer->lookahead != '\n') lexer->advance(lexer, false);
    if (lexer->eof(lexer)) return false;
    lexer->advance(lexer, false);
    while (blank(lexer->lookahead) || lexer->lookahead == '\r') lexer->advance(lexer, false);
    if (lexer->eof(lexer)) return false;
    if (lexer->lookahead != '\n') break;
  }
  int32_t c = lexer->lookahead;
  return (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || c == '_' || c >= 0x80 || c == '?' || c == '#' ||
         c == '\'' || c == '"' || c == '(';
}

/* Reads a word; true if it is a keyword that closes or continues a block. */
static bool closer_word(TSLexer *lexer) {
  static const char *const words[] = {"end",   "endif", "endfor", "endwhile", "endsub", "endfunction",
                                      "endtry", "next", "else",   "elseif",   "catch"};
  char text[12];
  unsigned n = 0;
  bool fits = true;
  while (word_char(lexer->lookahead) && !lexer->eof(lexer)) {
    int32_t c = lexer->lookahead;
    if (n < sizeof text - 1 && c < 0x80) {
      text[n++] = (char)(c >= 'A' && c <= 'Z' ? c + 32 : c);
    } else {
      fits = false;
    }
    lexer->advance(lexer, false);
  }
  if (!fits) return false;
  text[n] = 0;
  for (unsigned i = 0; i < sizeof words / sizeof words[0]; i++) {
    unsigned j = 0;
    while (words[i][j] && words[i][j] == text[j]) j++;
    if (!words[i][j] && !text[j]) return true;
  }
  return false;
}

/* The last unit of the input (a word or one character) with the blanks around it, as a line end. */
static bool final_line_end(TSLexer *lexer) {
  while (blank(lexer->lookahead)) lexer->advance(lexer, true);
  if (lexer->eof(lexer)) return false;
  if (word_char(lexer->lookahead)) {
    while (word_char(lexer->lookahead) && !lexer->eof(lexer)) lexer->advance(lexer, false);
  } else {
    lexer->advance(lexer, false);
  }
  while (blank(lexer->lookahead)) lexer->advance(lexer, false);
  if (!lexer->eof(lexer)) return false;
  lexer->mark_end(lexer);
  lexer->result_symbol = RECOVERY_NEWLINE;
  return true;
}

bool tree_sitter_brightscript_external_scanner_scan(void *payload, TSLexer *lexer, const bool *valid_symbols) {
  State *state = payload;
  if (!valid_symbols[RECOVERY_SENTINEL]) {
    if (state->eof_line_end && valid_symbols[RECOVERY_NEWLINE]) return final_line_end(lexer);
    return false;
  }
  state->eof_line_end = 0;

  bool line_start = lexer->get_column(lexer) == 0;
  while (blank(lexer->lookahead)) lexer->advance(lexer, true);
  if (lexer->eof(lexer)) return false;

  /* A line break: LF or CR LF. A lone CR is not a line break (BS-LEX-007); it starts a run. */
  unsigned units = 0; /* words and single non-blank characters in the run */
  if (lexer->lookahead == '\n' || lexer->lookahead == '\r') {
    bool cr = lexer->lookahead == '\r';
    lexer->advance(lexer, false);
    if (!cr || lexer->lookahead == '\n') {
      if (cr) lexer->advance(lexer, false);
      lexer->mark_end(lexer);
      lexer->result_symbol = RECOVERY_NEWLINE;
      return true;
    }
    units = 1;
  }

  /* At the start of a line, a version still in error lexes the line token by token, so skipping
     a valid line after an error costs as much as without this scanner; a line that begins with an
     operator continues the malformed text and is one run. */
  if (line_start && units == 0 && !operator_start(lexer->lookahead)) return false;

  /* A run: up to a line break, a `'` comment outside a string literal, a keyword that closes or
     continues a block (or a `:` before one), or the end of input. The token end is marked before
     each unit, so at the end of input the run stops before its last unit, which then ends the
     line. Every iteration consumes at least one character or returns. */
  bool in_string = false;
  bool after_word = false;
  for (;;) {
    if (lexer->eof(lexer)) {
      if (units == 0) return false;
      if (units == 1) {
        lexer->mark_end(lexer);
        lexer->result_symbol = RECOVERY_NEWLINE;
      } else {
        lexer->result_symbol = RECOVERY_RUN;
      }
      state->eof_line_end = 1;
      return true;
    }
    int32_t c = lexer->lookahead;
    if (c == '\n') break;
    if (!in_string && c == '\'') break;
    if (c == '\r') {
      lexer->mark_end(lexer);
      lexer->advance(lexer, false);
      if (lexer->lookahead == '\n') {
        if (units < MIN_RUN && statement_follows(lexer)) return false;
        lexer->result_symbol = RECOVERY_RUN;
        return true; /* ends before the CR LF */
      }
      units++;
      after_word = false;
      continue;
    }
    if (blank(c)) {
      lexer->advance(lexer, false);
      after_word = false;
      continue;
    }
    lexer->mark_end(lexer);
    if (!in_string && c == ':') {
      unsigned before = units;
      lexer->advance(lexer, false);
      units++;
      after_word = false;
      while (blank(lexer->lookahead)) lexer->advance(lexer, false);
      if (!lexer->eof(lexer) && word_start(lexer->lookahead)) {
        if (closer_word(lexer)) {
          if (before == 0) return false;
          lexer->result_symbol = RECOVERY_RUN; /* ends before the `:` */
          return true;
        }
        units++;
        after_word = true;
      }
      continue;
    }
    if (!in_string && !after_word && word_start(c)) {
      if (closer_word(lexer)) {
        if (units == 0) return false;
        lexer->result_symbol = RECOVERY_RUN; /* ends before the keyword */
        return true;
      }
      units++;
      after_word = true;
      continue;
    }
    if (c == '"') in_string = !in_string;
    after_word = word_char(c);
    lexer->advance(lexer, false);
    units++;
  }
  if (units == 0) return false;
  lexer->mark_end(lexer);
  if (units < MIN_RUN && statement_follows(lexer)) return false;
  lexer->result_symbol = RECOVERY_RUN;
  return true;
}
