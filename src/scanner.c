/**
 * @file Error-recovery scanner for the BrightScript grammar (ADR-0008).
 * @license MIT
 *
 * It returns a token only while the parser is recovering from an error, which
 * it recognises by the validity of RECOVERY_SENTINEL: no grammar rule uses that
 * token, so the runtime marks it valid only in its error state. A valid parse
 * never receives a token from here. The one exception is the rest of an input
 * whose final line holds a long malformed run and has no line break: after
 * recovery moved back to a line end, the runtime lexes that rest again in a
 * normal state, and a flag of the run before it marks it as that line end.
 */

#include "tree_sitter/alloc.h"
#include "tree_sitter/parser.h"

/* Order = `externals` in grammar.js. */
enum TokenType {
  RECOVERY_RUN,      /* malformed text of one line, as one token */
  RECOVERY_NEWLINE,  /* a line break, valid only where a line or a block body may begin */
  RECOVERY_SENTINEL, /* never produced; valid only in the error state */
  RAW_TOKEN_MARKER,  /* never produced; keeps raw token names (grammar.js) */
};

/* The state: flags of the last token this scanner returned in a stack version. In runtime 0.27.0 a
   token that changes them cannot be skipped once recovery to an earlier state succeeded. No state
   accepts a run, and a line break changes them only after a long or whole-line run, where recovery
   is to leave the line; after a short run the line break is an ordinary one. */
enum {
  EOF_LINE_END = 1, /* a run stopped before the rest of the input, which ends the line */
  RUN = 2,          /* a long or whole-line run: the line break after it is a recovery line break */
  LONG = 4,         /* a run of MIN_RUN units or more */
  AFTER_LONG = 8,   /* the line break after a long run: the next line is one run */
  EOF_TAIL = 16,    /* a long run stopped at a keyword or a comment on the last line */
};

/* A malformed rest shorter than this, before a line that may begin a statement or at the end of
   input, is recovered token by token, as without this scanner: a cheap run there lets a recovery
   version skip the line break and take the next line into the malformed statement. */
enum { MIN_RUN = 16, TAIL_LOOKAHEAD = 256 };

typedef struct {
  unsigned char flags;
} State;

/* Without the state (an allocation failure) the scanner returns no token, as a grammar without it. */
void *tree_sitter_brightscript_external_scanner_create(void) { return ts_calloc(1, sizeof(State)); }

void tree_sitter_brightscript_external_scanner_destroy(void *payload) { ts_free(payload); }

unsigned tree_sitter_brightscript_external_scanner_serialize(void *payload, char *buffer) {
  State *state = payload;
  if (!state || !state->flags) return 0;
  buffer[0] = (char)state->flags;
  return 1;
}

void tree_sitter_brightscript_external_scanner_deserialize(void *payload, const char *buffer, unsigned length) {
  State *state = payload;
  if (state) state->flags = length == 1 ? (unsigned char)buffer[0] : 0;
}

static bool blank(int32_t c) { return c == ' ' || c == '\t'; }

static bool line_break(int32_t c) { return c == '\n' || c == '\r'; }

static bool word_char(int32_t c) {
  return (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9') || c == '_' || c >= 0x80;
}

static bool word_start(int32_t c) { return word_char(c) && !(c >= '0' && c <= '9'); }

static bool statement_start(int32_t c) {
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

/* Called where a run stopped at a line break or a `'` comment: reads ahead past the rest of the
   line and blank lines; true if the next line begins like a statement or a comment. */
static bool statement_follows(TSLexer *lexer) {
  while (!lexer->eof(lexer) && !line_break(lexer->lookahead)) lexer->advance(lexer, false);
  if (lexer->eof(lexer)) return false;
  lexer->advance(lexer, false);
  while (blank(lexer->lookahead) || line_break(lexer->lookahead)) lexer->advance(lexer, false);
  return !lexer->eof(lexer) && statement_start(lexer->lookahead);
}

/* True if the end of input comes within `limit` characters without a line break. */
static bool end_follows(TSLexer *lexer, unsigned limit) {
  for (unsigned i = 0; i < limit; i++) {
    if (lexer->eof(lexer)) return true;
    if (line_break(lexer->lookahead)) return false;
    lexer->advance(lexer, false);
  }
  return lexer->eof(lexer);
}

/* The rest of the input, if it holds no line break, as the line end of a long last line. */
static bool rest_as_line_end(TSLexer *lexer, State *state) {
  while (blank(lexer->lookahead)) lexer->advance(lexer, true);
  if (lexer->eof(lexer)) return false;
  while (!lexer->eof(lexer)) {
    if (line_break(lexer->lookahead)) return false;
    lexer->advance(lexer, false);
  }
  lexer->mark_end(lexer);
  lexer->result_symbol = RECOVERY_NEWLINE;
  state->flags = EOF_LINE_END;
  return true;
}

static bool run(TSLexer *lexer, State *state, unsigned units, unsigned char flags) {
  lexer->result_symbol = RECOVERY_RUN;
  state->flags = (unsigned char)(flags | (units >= MIN_RUN ? RUN | LONG : 0));
  return true;
}

bool tree_sitter_brightscript_external_scanner_scan(void *payload, TSLexer *lexer, const bool *valid_symbols) {
  State *state = payload;
  if (!state) return false;
  unsigned char prev = state->flags;
  if (!valid_symbols[RECOVERY_SENTINEL]) {
    /* After recovery at the end of input moved back to a line end, the runtime lexes the rest
       again in a normal state; it is the line end there too. */
    if ((prev & EOF_LINE_END) && valid_symbols[RECOVERY_NEWLINE]) return rest_as_line_end(lexer, state);
    return false;
  }
  if (prev & EOF_LINE_END) return rest_as_line_end(lexer, state);

  while (blank(lexer->lookahead)) lexer->advance(lexer, true);
  if (lexer->eof(lexer)) return false;

  /* A line break (LF, CR LF or a lone CR) is a recovery line break after a long or whole-line run;
     otherwise the runtime lexes it as an ordinary line break, as without this scanner. A lone CR
     is no line break of the grammar (BS-LEX-007), so in recovery it is always one here. */
  if (line_break(lexer->lookahead)) {
    bool cr = lexer->lookahead == '\r';
    lexer->advance(lexer, false);
    bool crlf = cr && lexer->lookahead == '\n';
    if (crlf) lexer->advance(lexer, false);
    if (!(prev & RUN) && (!cr || crlf)) return false;
    lexer->mark_end(lexer);
    lexer->result_symbol = RECOVERY_NEWLINE;
    state->flags = (prev & LONG) ? AFTER_LONG : 0;
    return true;
  }

  /* A run: up to a line break, a `'` comment outside a string literal, a keyword that closes or
     continues a block (or a `:` or `#` before one), or the end of input. The token end is marked
     before each unit (before a `:` or `#` and the word after it), so at the end of input a run stops
     before its last unit, which then ends the line. Every iteration consumes at least one character
     or returns. After the line break of a long run, and after a long run that stopped on the last
     line, the whole line is one run. */
  bool whole_line = prev & (AFTER_LONG | EOF_TAIL);
  bool in_string = false;
  bool after_word = false;
  unsigned units = 0;
  for (;;) {
    if (lexer->eof(lexer)) {
      if (units == 0) return false;
      if (units == 1 && (prev & EOF_TAIL)) {
        lexer->mark_end(lexer);
        lexer->result_symbol = RECOVERY_NEWLINE;
        state->flags = EOF_LINE_END;
        return true;
      }
      if (units < MIN_RUN && !whole_line) return false;
      return run(lexer, state, units, EOF_LINE_END); /* ends before its last unit */
    }
    int32_t c = lexer->lookahead;
    if (line_break(c)) break;
    if (blank(c)) {
      lexer->advance(lexer, false);
      after_word = false;
      continue;
    }
    lexer->mark_end(lexer);
    if (!in_string && !whole_line && c == '\'') {
      if (units >= MIN_RUN && end_follows(lexer, (unsigned)-1)) return run(lexer, state, units, EOF_TAIL);
      break;
    }
    if (!in_string && !whole_line && (c == ':' || c == '#')) {
      unsigned before = units;
      lexer->advance(lexer, false);
      units++;
      after_word = false;
      while (blank(lexer->lookahead)) lexer->advance(lexer, false);
      if (!lexer->eof(lexer) && word_start(lexer->lookahead)) {
        if (closer_word(lexer)) {
          if (before == 0) return false;
          bool tail = before >= MIN_RUN && end_follows(lexer, TAIL_LOOKAHEAD);
          return run(lexer, state, before, tail ? EOF_TAIL : 0); /* ends before the `:` or `#` */
        }
        units++;
        after_word = true;
      }
      continue;
    }
    if (!in_string && !whole_line && !after_word && word_start(c)) {
      if (closer_word(lexer)) {
        if (units == 0) return false;
        bool tail = units >= MIN_RUN && end_follows(lexer, TAIL_LOOKAHEAD);
        return run(lexer, state, units, tail ? EOF_TAIL : 0); /* ends before the keyword */
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
  if (units < MIN_RUN && !whole_line && statement_follows(lexer)) return false;
  return run(lexer, state, whole_line ? 0 : units, whole_line ? RUN : 0);
}
