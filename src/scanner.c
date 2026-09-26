/**
 * @file Error-recovery scanner for the BrightScript grammar (ADR-0008).
 * @license MIT
 *
 * It returns a token only while the parser is recovering from an error, which
 * it recognises by the validity of RECOVERY_SENTINEL: no grammar rule uses that
 * token, so the runtime marks it valid only in its error state's lex mode. The
 * runtime also tries that mode when a normal state finds no token (a lone CR,
 * for example); a token returned there is accepted only where the grammar
 * accepts it, so the scanner returns no line end for a lone CR. A valid parse
 * never receives a token from here. The one exception is the line end after a
 * long malformed run: when recovery moved back to an earlier state, the
 * runtime lexes that line end again in a normal state, and the state flag of
 * the run marks it as a recovery line end there.
 */

#include "tree_sitter/alloc.h"
#include "tree_sitter/parser.h"

/* Order = `externals` in grammar.js. */
enum TokenType {
  RECOVERY_RUN,      /* malformed text of one line, as one token */
  RECOVERY_NEWLINE,  /* a line end, valid only where a line or a block body may begin */
  RECOVERY_SENTINEL, /* never produced; valid only in the error state */
  RAW_TOKEN_MARKER,  /* never produced; keeps raw token names (grammar.js) */
};

/* The state, flags of the last token this scanner returned in a stack version. RUN: a long run on
   this line, kept by the shorter runs after it and cleared by the recovery line end of the line.
   TAIL: a long run on this line stopped before a block keyword, where recovery can resume on the
   same line; its line break is then an ordinary one, and TAIL matters only at the end of input.
   EOF_DONE: the empty line end at the end of input was returned. In runtime 0.27.0 a token that
   changes the state cannot be skipped once recovery to an earlier state succeeded, and an empty
   token is kept in recovery only if it changes the state. No state accepts a run; a line break
   changes the state only after a long run, where recovery is to leave the line. */
enum { RUN = 1, EOF_DONE = 2, TAIL = 4 };

/* A malformed rest shorter than this is recovered token by token, as without this scanner, before
   a line that may begin a statement (a cheap run there lets a recovery version skip the line break
   and take the next line into the malformed statement), when it begins with a closing bracket
   (recovery can then return into the literal it closes) and at the end of input, unless a long
   run precedes it on its line. A rest that stops before a block keyword is a run however short. */
enum { MIN_RUN = 16 };

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

/* A recovery line end: LF or CR LF (a lone CR is no line break of the grammar, BS-LEX-007, and no
   line end here), or at the end of input an empty token, which the runtime keeps because it
   changes the state. */
static bool line_end(TSLexer *lexer, State *state) {
  if (!lexer->eof(lexer)) {
    bool cr = lexer->lookahead == '\r';
    lexer->advance(lexer, false);
    if (cr) {
      if (lexer->lookahead != '\n') return false;
      lexer->advance(lexer, false);
    }
  }
  state->flags = lexer->eof(lexer) ? EOF_DONE : 0;
  lexer->mark_end(lexer);
  lexer->result_symbol = RECOVERY_NEWLINE;
  return true;
}

static bool run(TSLexer *lexer, State *state, unsigned units, unsigned char prev) {
  lexer->result_symbol = RECOVERY_RUN;
  state->flags = (unsigned char)((units >= MIN_RUN ? RUN : prev & RUN) | (prev & TAIL));
  return true;
}

/* A run that stops before a keyword that closes or continues a block: recovery can resume at the
   keyword on this line, so the line break after it is an ordinary one (RUN is cleared); after a
   long run the end of input is still a recovery line end (TAIL). */
static bool stop(TSLexer *lexer, State *state, unsigned units, unsigned char prev) {
  lexer->result_symbol = RECOVERY_RUN;
  state->flags = (units >= MIN_RUN || (prev & (RUN | TAIL))) ? TAIL : 0;
  return true;
}

bool tree_sitter_brightscript_external_scanner_scan(void *payload, TSLexer *lexer, const bool *valid_symbols) {
  State *state = payload;
  if (!state) return false;
  unsigned char prev = state->flags;
  bool recovering = valid_symbols[RECOVERY_SENTINEL];
  if (!recovering && !((prev & (RUN | TAIL)) && valid_symbols[RECOVERY_NEWLINE])) return false;

  while (blank(lexer->lookahead)) lexer->advance(lexer, true);

  /* After a long run the line end is a recovery line end, also when recovery moved back to an
     earlier state and the runtime lexes it again in a normal state. At any other line break the
     scanner returns nothing and the runtime lexes the ordinary line break, as without it. At the
     end of input the empty line end is returned once per stack version, in recovery after a long
     run or not, so that recovery can leave the constructs the input leaves open. */
  if (lexer->eof(lexer) || line_break(lexer->lookahead)) {
    if ((prev & RUN) || (lexer->eof(lexer) && (prev & TAIL))) return line_end(lexer, state);
    if (recovering && lexer->eof(lexer) && !(prev & EOF_DONE)) return line_end(lexer, state);
    return false;
  }
  if (!recovering) return false;

  /* A run: up to a line break, a `'` comment outside a string literal, a keyword that closes or
     continues a block (or a `:` or `#` before one), or the end of input. The token end is marked
     before each unit, so that a run can stop before a keyword. Every iteration consumes at least
     one character or returns; a run is never empty. */
  bool in_string = false;
  bool after_word = false;
  unsigned units = 0;
  bool closing = lexer->lookahead == ')' || lexer->lookahead == ']' || lexer->lookahead == '}';
  for (;;) {
    if (lexer->eof(lexer)) {
      if (units < MIN_RUN && !(prev & RUN)) return false;
      lexer->mark_end(lexer);
      return run(lexer, state, units, prev);
    }
    int32_t c = lexer->lookahead;
    if (line_break(c)) break;
    if (blank(c)) {
      lexer->advance(lexer, false);
      after_word = false;
      continue;
    }
    lexer->mark_end(lexer);
    if (!in_string && c == '\'') break;
    if (!in_string && (c == ':' || c == '#')) {
      unsigned before = units;
      lexer->advance(lexer, false);
      units++;
      after_word = false;
      while (blank(lexer->lookahead)) lexer->advance(lexer, false);
      if (!lexer->eof(lexer) && word_start(lexer->lookahead)) {
        if (closer_word(lexer)) {
          if (before == 0) return false;
          return stop(lexer, state, before, prev); /* ends before the `:` or `#` */
        }
        units++;
        after_word = true;
      }
      continue;
    }
    if (!in_string && !after_word && word_start(c)) {
      if (closer_word(lexer)) {
        if (units == 0) return false;
        return stop(lexer, state, units, prev); /* ends before the keyword */
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
  if (units < MIN_RUN && (closing || statement_follows(lexer))) return false;
  return run(lexer, state, units, prev);
}
