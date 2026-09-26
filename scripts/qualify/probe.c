/**
 * @file Native measurement harness of the release qualification lane
 * (docs/validation/validation.md, "Release qualification lane").
 * @license MIT
 *
 * Linked statically with the stock Tree-sitter runtime and this grammar's
 * parser and scanner; run only under scripts/qualify/supervisor.c.
 * Built twice: plain, and with -DMEASURE_ALLOC (a counting allocator through
 * the public ts_set_allocator hook; its timings are never used as timings).
 *
 *   probe RUN <op> <input> <query> <budget_ms>
 *       op: PARSE | LIFECYCLE | QUERY_ONLY | NAV_CURSOR | NAV_FIELD | NAV_INDEX
 *       budget_ms > 0 installs a progress callback that asks to cancel once
 *       the budget has elapsed; 0 installs one that never cancels.
 *   probe DUMP <input>          preorder CST: N depth type field start end flags
 *   probe DUMPLIST <list>       DUMP for every path in the list file
 *   probe CAPTURES <input> <query>
 *   probe INCREMENTAL <base> <edits> <repair 0|1> <selftest 0|1|2>
 *   probe RESUME <input> <target> <chunk> <trigger>
 *   probe TWO <a> <b>
 *
 * Output is one JSON object per line; a run that reaches its end prints
 * {"final":true,...}. Only public API calls are used.
 */
#include <windows.h>
#include <psapi.h>
#include <stdarg.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <tree_sitter/api.h>

const TSLanguage *tree_sitter_brightscript(void);

static LARGE_INTEGER frequency;
static double clock_ms(void) {
  LARGE_INTEGER c;
  QueryPerformanceCounter(&c);
  return c.QuadPart * 1000.0 / frequency.QuadPart;
}

/* ------------------------------------------------------------- allocator */
static uint64_t live_bytes, peak_bytes, total_bytes, allocations;
static int parse_active;
static double parse_start, budget_ms;
static double budget_cross_ms = -1;
static uint64_t live_at_budget, peak_after_budget;

#ifdef MEASURE_ALLOC
typedef union { size_t size; max_align_t alignment; } Header;
static void account(void) {
  if (live_bytes > peak_bytes) peak_bytes = live_bytes;
  if (parse_active && budget_ms > 0) {
    if (budget_cross_ms < 0 && clock_ms() - parse_start >= budget_ms) {
      budget_cross_ms = clock_ms() - parse_start;
      live_at_budget = live_bytes;
      peak_after_budget = live_bytes;
    }
    if (budget_cross_ms >= 0 && live_bytes > peak_after_budget) peak_after_budget = live_bytes;
  }
}
static void *counting_malloc(size_t size) {
  if (size > SIZE_MAX - sizeof(Header)) abort();
  Header *h = malloc(sizeof(Header) + size);
  if (!h) { puts("{\"event\":\"allocator_refused\"}"); exit(86); }
  h->size = size;
  live_bytes += size; total_bytes += size; allocations++;
  account();
  return h + 1;
}
static void counting_free(void *p) {
  if (!p) return;
  Header *h = (Header *)p - 1;
  live_bytes -= h->size;
  free(h);
}
static void *counting_calloc(size_t n, size_t size) {
  if (size && n > SIZE_MAX / size) abort();
  void *p = counting_malloc(n * size);
  memset(p, 0, n * size);
  return p;
}
static void *counting_realloc(void *p, size_t size) {
  if (!p) return counting_malloc(size);
  if (!size) { counting_free(p); return NULL; }
  if (size > SIZE_MAX - sizeof(Header)) abort();
  Header *old = (Header *)p - 1;
  size_t before = old->size;
  Header *h = realloc(old, sizeof(Header) + size);
  if (!h) { puts("{\"event\":\"allocator_refused\"}"); exit(86); }
  h->size = size;
  live_bytes = live_bytes - before + size; total_bytes += size; allocations++;
  account();
  return h + 1;
}
#endif

/* ------------------------------------------------------------------ files */
static char *read_file(const char *path, uint32_t *size) {
  FILE *f = fopen(path, "rb");
  if (!f || fseek(f, 0, SEEK_END)) exit(80);
  long n = ftell(f);
  if (n < 0 || n > 8 * 1024 * 1024 || fseek(f, 0, SEEK_SET)) exit(81);
  char *p = malloc((size_t)n + 1);
  if (!p || fread(p, 1, (size_t)n, f) != (size_t)n || fclose(f)) exit(82);
  p[n] = 0;
  *size = (uint32_t)n;
  return p;
}

static TSParser *new_parser(void) {
  TSParser *p = ts_parser_new();
  if (!p || !ts_parser_set_language(p, tree_sitter_brightscript())) exit(83);
  return p;
}

static void memory_now(SIZE_T *ws, SIZE_T *commit) {
  PROCESS_MEMORY_COUNTERS_EX c;
  c.cb = sizeof c;
  if (GetProcessMemoryInfo(GetCurrentProcess(), (PROCESS_MEMORY_COUNTERS *)&c, sizeof c)) {
    *ws = c.WorkingSetSize;
    *commit = c.PrivateUsage;
  }
}

/* ----------------------------------------------------------------- digests */
typedef struct { uint64_t h; } Fnv;
static void fnv_bytes(Fnv *f, const void *p, size_t n) {
  const unsigned char *b = p;
  for (size_t i = 0; i < n; i++) { f->h ^= b[i]; f->h *= 1099511628211ULL; }
}
static void fnv_u32(Fnv *f, uint32_t v) { fnv_bytes(f, &v, sizeof v); }
static void fnv_str(Fnv *f, const char *s) { if (s) fnv_bytes(f, s, strlen(s)); fnv_bytes(f, "", 1); }

/* A growable text buffer for dumps that are compared, not printed. */
typedef struct { char *p; size_t n, cap; } Buf;
static void buf_put(Buf *b, const char *fmt, ...) {
  char tmp[1024];
  va_list a;
  va_start(a, fmt);
  int n = vsnprintf(tmp, sizeof tmp, fmt, a);
  va_end(a);
  if (n < 0) exit(90);
  if (b->n + (size_t)n + 1 > b->cap) {
    b->cap = (b->n + (size_t)n + 1) * 2;
    b->p = realloc(b->p, b->cap);
    if (!b->p) exit(90);
  }
  memcpy(b->p + b->n, tmp, (size_t)n);
  b->n += (size_t)n;
  b->p[b->n] = 0;
}

static unsigned node_flags(TSNode n) {
  return (unsigned)ts_node_is_named(n) | ((unsigned)ts_node_is_missing(n) << 1) | ((unsigned)ts_node_is_error(n) << 2) |
         ((unsigned)ts_node_is_extra(n) << 3) | ((unsigned)ts_node_has_error(n) << 4);
}

/* Full preorder dump through one cursor (no parent lookups, so no depth-squared work). */
static void dump_tree(TSTree *tree, Buf *b, FILE *out, uint64_t *count, uint32_t *max_depth) {
  TSTreeCursor c = ts_tree_cursor_new(ts_tree_root_node(tree));
  uint32_t depth = 0;
  for (;;) {
    TSNode n = ts_tree_cursor_current_node(&c);
    const char *f = ts_tree_cursor_current_field_name(&c);
    TSPoint s = ts_node_start_point(n), e = ts_node_end_point(n);
    if (b) buf_put(b, "N\t%u\t%s\t%s\t%u\t%u\t%u:%u\t%u:%u\t%u\n", depth, ts_node_type(n), f ? f : "-",
                   ts_node_start_byte(n), ts_node_end_byte(n), s.row, s.column, e.row, e.column, node_flags(n));
    if (out) fprintf(out, "N\t%u\t%s\t%s\t%u\t%u\t%u\n", depth, ts_node_type(n), f ? f : "-",
                     ts_node_start_byte(n), ts_node_end_byte(n), node_flags(n));
    (*count)++;
    if (depth > *max_depth) *max_depth = depth;
    if (ts_tree_cursor_goto_first_child(&c)) { depth++; continue; }
    while (!ts_tree_cursor_goto_next_sibling(&c)) {
      if (!ts_tree_cursor_goto_parent(&c)) { ts_tree_cursor_delete(&c); return; }
      depth--;
    }
  }
}

static int same(const Buf *a, const Buf *b) { return a->n == b->n && !memcmp(a->p, b->p, a->n); }

/* ---------------------------------------------------------------- RUN op */
static double first_callback = -1, last_callback = -1, request_ms = -1, max_gap = 0;
static uint64_t callbacks;
static bool progress(TSParseState *state) {
  (void)state;
  double t = clock_ms() - parse_start;
  if (first_callback < 0) first_callback = t;
  else if (t - last_callback > max_gap) max_gap = t - last_callback;
  last_callback = t;
  callbacks++;
  if (budget_ms > 0 && t >= budget_ms) {
    if (request_ms < 0) request_ms = t;
    return true;
  }
  return false;
}

typedef struct { const char *text; uint32_t length, chunk; } Input;
static const char *read_input(void *payload, uint32_t offset, TSPoint point, uint32_t *n) {
  (void)point;
  const Input *in = payload;
  *n = offset < in->length ? in->length - offset : 0;
  if (in->chunk && *n > in->chunk) *n = in->chunk;
  return *n ? in->text + offset : "";
}

static int run(const char *op, const char *input_path, const char *query_path, double budget) {
  uint32_t length;
  char *source = read_file(input_path, &length);
  Input input = {source, length, 0};
  budget_ms = budget;
  TSParser *parser = new_parser();
  SIZE_T ws_idle = 0, commit_idle = 0, ws_return = 0, commit_return = 0;
  memory_now(&ws_idle, &commit_idle);
  printf("{\"event\":\"idle\",\"working_set_bytes\":%llu,\"commit_bytes\":%llu}\n",
         (unsigned long long)ws_idle, (unsigned long long)commit_idle);
  fflush(stdout);

  TSParseOptions options = {NULL, progress};
  parse_active = 1;
  parse_start = clock_ms();
  TSTree *tree = ts_parser_parse_with_options(parser, NULL, (TSInput){&input, read_input, TSInputEncodingUTF8, NULL}, options);
  double parse_ms = clock_ms() - parse_start;
  parse_active = 0;
  uint64_t live_at_return = live_bytes;
  memory_now(&ws_return, &commit_return);
  double head = first_callback >= 0 ? first_callback : parse_ms;
  double tail = last_callback >= 0 ? parse_ms - last_callback : parse_ms;
  double edges = max_gap;
  if (head > edges) edges = head;
  if (tail > edges) edges = tail;
  printf("{\"event\":\"parse\",\"parse_ms\":%.6f,\"cancelled\":%s,\"callbacks\":%llu,\"head_gap_ms\":%.6f,"
         "\"max_gap_ms\":%.6f,\"tail_gap_ms\":%.6f,\"max_gap_incl_edges_ms\":%.6f,\"budget_ms\":%.6f,"
         "\"request_ms\":%.6f,\"budget_cross_ms\":%.6f,\"live_at_budget\":%llu,\"peak_after_budget\":%llu,"
         "\"live_at_return\":%llu,\"working_set_at_return\":%llu,\"commit_at_return\":%llu}\n",
         parse_ms, tree ? "false" : "true", (unsigned long long)callbacks, head, max_gap, tail, edges, budget,
         request_ms, budget_cross_ms, (unsigned long long)live_at_budget, (unsigned long long)peak_after_budget,
         (unsigned long long)live_at_return, (unsigned long long)ws_return, (unsigned long long)commit_return);
  fflush(stdout);

  int has_error = -1;
  uint64_t nodes = 0, errors = 0, missing = 0, captures = 0, zero_width = 0, nav_visits = 0, nav_fields = 0,
           nav_children = 0;
  uint32_t max_depth = 0;
  double query_compile_ms = -1, query_ms = -1, nav_ms = -1;
  int exceeded = 0;
  Fnv capture_digest = {14695981039346656037ULL}, tree_digest = {14695981039346656037ULL};
  if (tree) {
    TSNode root = ts_tree_root_node(tree);
    has_error = ts_node_has_error(root);
    if (!strcmp(op, "QUERY_ONLY") || !strcmp(op, "LIFECYCLE")) {
      uint32_t qlen, error_offset;
      TSQueryError error_type;
      char *qsrc = read_file(query_path, &qlen);
      double t = clock_ms();
      TSQuery *query = ts_query_new(tree_sitter_brightscript(), qsrc, qlen, &error_offset, &error_type);
      query_compile_ms = clock_ms() - t;
      if (!query) { printf("{\"event\":\"query_error\",\"type\":%u,\"offset\":%u}\n", error_type, error_offset); return 84; }
      TSQueryCursor *cursor = ts_query_cursor_new();
      t = clock_ms();
      ts_query_cursor_exec(cursor, query, root);
      TSQueryMatch match;
      uint32_t index;
      while (ts_query_cursor_next_capture(cursor, &match, &index)) {
        TSQueryCapture c = match.captures[index];
        uint32_t name_length;
        const char *name = ts_query_capture_name_for_id(query, c.index, &name_length);
        /* Role identity: capture name, span and node type; pattern numbers differ between query versions. */
        fnv_bytes(&capture_digest, name, name_length);
        fnv_u32(&capture_digest, ts_node_start_byte(c.node));
        fnv_u32(&capture_digest, ts_node_end_byte(c.node));
        fnv_str(&capture_digest, ts_node_type(c.node));
        captures++;
        zero_width += ts_node_start_byte(c.node) == ts_node_end_byte(c.node);
      }
      query_ms = clock_ms() - t;
      exceeded = ts_query_cursor_did_exceed_match_limit(cursor);
      printf("{\"event\":\"query\",\"compile_ms\":%.6f,\"query_ms\":%.6f,\"captures\":%llu,\"zero_width_captures\":%llu,"
             "\"match_limit\":%u,\"exceeded\":%s,\"digest\":\"%016llx\"}\n",
             query_compile_ms, query_ms, (unsigned long long)captures, (unsigned long long)zero_width,
             ts_query_cursor_match_limit(cursor), exceeded ? "true" : "false", (unsigned long long)capture_digest.h);
      ts_query_cursor_delete(cursor);
      ts_query_delete(query);
      free(qsrc);
    }
    if (!strcmp(op, "LIFECYCLE") || !strcmp(op, "NAV_CURSOR") || !strcmp(op, "NAV_FIELD")) {
      int fields = strcmp(op, "NAV_CURSOR") != 0;
      TSTreeCursor c = ts_tree_cursor_new(root);
      uint32_t depth = 0;
      double t = clock_ms();
      for (;;) {
        TSNode n = ts_tree_cursor_current_node(&c);
        nav_visits++;
        errors += ts_node_is_error(n);
        missing += ts_node_is_missing(n);
        if (depth > max_depth) max_depth = depth;
        fnv_u32(&tree_digest, depth);
        fnv_str(&tree_digest, ts_node_type(n));
        fnv_u32(&tree_digest, ts_node_start_byte(n));
        fnv_u32(&tree_digest, ts_node_end_byte(n));
        fnv_u32(&tree_digest, node_flags(n));
        if (fields) { fnv_str(&tree_digest, ts_tree_cursor_current_field_name(&c)); nav_fields++; }
        if (ts_tree_cursor_goto_first_child(&c)) { depth++; continue; }
        int done = 0;
        while (!ts_tree_cursor_goto_next_sibling(&c)) {
          if (!ts_tree_cursor_goto_parent(&c)) { done = 1; break; }
          depth--;
        }
        if (done) break;
      }
      nav_ms = clock_ms() - t;
      ts_tree_cursor_delete(&c);
      nodes = nav_visits;
    }
    if (!strcmp(op, "NAV_INDEX")) {
      TSNode print = ts_node_named_child(root, 0);
      if (ts_node_is_null(print) || strcmp(ts_node_type(print), "print_statement")) return 87;
      uint32_t count = ts_node_child_count(print);
      double t = clock_ms();
      for (uint32_t i = 0; i < count; i++) {
        TSNode n = ts_node_child(print, i);
        fnv_str(&tree_digest, ts_node_type(n));
        fnv_u32(&tree_digest, ts_node_start_byte(n));
        fnv_u32(&tree_digest, ts_node_end_byte(n));
        nav_children++;
      }
      nav_ms = clock_ms() - t;
      if (nav_children != count) return 92;
    }
    if (nav_ms >= 0)
      printf("{\"event\":\"navigation\",\"op\":\"%s\",\"navigation_ms\":%.6f,\"visits\":%llu,\"field_calls\":%llu,"
             "\"child_calls\":%llu,\"digest\":\"%016llx\"}\n", op, nav_ms, (unsigned long long)nav_visits,
             (unsigned long long)nav_fields, (unsigned long long)nav_children, (unsigned long long)tree_digest.h);
  }
  double t = clock_ms();
  if (tree) ts_tree_delete(tree);
  double tree_delete_ms = clock_ms() - t;
  t = clock_ms();
  ts_parser_delete(parser);
  double parser_delete_ms = clock_ms() - t;
  printf("{\"event\":\"cleanup\",\"tree_delete_ms\":%.6f,\"parser_delete_ms\":%.6f,\"allocator_live_after\":%llu}\n",
         tree ? tree_delete_ms : -1.0, parser_delete_ms, (unsigned long long)live_bytes);
  printf("{\"final\":true,\"op\":\"%s\",\"bytes\":%u,\"parse_ms\":%.6f,\"cancelled\":%s,\"has_error\":%d,\"nodes\":%llu,"
         "\"errors\":%llu,\"missing\":%llu,\"max_depth\":%u,\"query_ms\":%.6f,\"captures\":%llu,\"navigation_ms\":%.6f,"
         "\"tree_delete_ms\":%.6f,\"parser_delete_ms\":%.6f,\"allocator_peak_live\":%llu,\"allocator_total\":%llu,"
         "\"allocations\":%llu,\"allocator_live_after\":%llu,\"match_limit_exceeded\":%s,\"max_gap_incl_edges_ms\":%.6f}\n",
         op, length, parse_ms, tree ? "false" : "true", has_error, (unsigned long long)nodes, (unsigned long long)errors,
         (unsigned long long)missing, max_depth, query_ms, (unsigned long long)captures, nav_ms,
         tree ? tree_delete_ms : -1.0, parser_delete_ms, (unsigned long long)peak_bytes, (unsigned long long)total_bytes,
         (unsigned long long)allocations, (unsigned long long)live_bytes, exceeded ? "true" : "false", edges);
  free(source);
  return 0;
}

/* --------------------------------------------------------- DUMP, CAPTURES */
static int dump_file(TSParser *parser, const char *path) {
  uint32_t length;
  char *text = read_file(path, &length);
  Fnv f = {14695981039346656037ULL};
  fnv_bytes(&f, text, length);
  printf("F\t%s\t%u\t%016llx\n", path, length, (unsigned long long)f.h);
  TSTree *tree = ts_parser_parse_string(parser, NULL, text, length);
  if (!tree) { puts("PARSE_FAILED"); return 88; }
  uint64_t count = 0;
  uint32_t depth = 0;
  dump_tree(tree, NULL, stdout, &count, &depth);
  printf("END\t%llu\t%u\n", (unsigned long long)count, depth);
  ts_tree_delete(tree);
  ts_parser_reset(parser);
  free(text);
  return 0;
}

static int captures(const char *input_path, const char *query_path) {
  uint32_t length, qlen, error_offset;
  TSQueryError error_type;
  char *text = read_file(input_path, &length), *qsrc = read_file(query_path, &qlen);
  TSParser *parser = new_parser();
  TSTree *tree = ts_parser_parse_string(parser, NULL, text, length);
  TSQuery *query = ts_query_new(tree_sitter_brightscript(), qsrc, qlen, &error_offset, &error_type);
  if (!tree || !query) return 84;
  TSQueryCursor *cursor = ts_query_cursor_new();
  ts_query_cursor_exec(cursor, query, ts_tree_root_node(tree));
  TSQueryMatch match;
  uint32_t index;
  while (ts_query_cursor_next_capture(cursor, &match, &index)) {
    TSQueryCapture c = match.captures[index];
    uint32_t n;
    const char *name = ts_query_capture_name_for_id(query, c.index, &n);
    printf("C\t%u\t%.*s\t%u\t%u\t%d\t%s\n", match.pattern_index, (int)n, name, ts_node_start_byte(c.node),
           ts_node_end_byte(c.node), ts_node_is_missing(c.node), ts_node_type(c.node));
  }
  printf("{\"final\":true,\"exceeded\":%s}\n", ts_query_cursor_did_exceed_match_limit(cursor) ? "true" : "false");
  ts_query_cursor_delete(cursor);
  ts_query_delete(query);
  ts_tree_delete(tree);
  ts_parser_delete(parser);
  return 0;
}

/* ------------------------------------------------------------ INCREMENTAL */
static TSPoint point_at(const char *t, uint32_t offset) {
  TSPoint p = {0, 0};
  for (uint32_t i = 0; i < offset; i++) {
    if (t[i] == '\n') { p.row++; p.column = 0; } else p.column++;
  }
  return p;
}

static TSTree *apply_edit(TSParser *parser, TSTree *tree, char **text, uint32_t *length, uint32_t start,
                          uint32_t old_length, const char *inserted, uint32_t new_length) {
  if (start + old_length > *length) exit(91);
  uint32_t n = *length - old_length + new_length;
  char *next = malloc((size_t)n + 1);
  if (!next) exit(92);
  memcpy(next, *text, start);
  memcpy(next + start, inserted, new_length);
  memcpy(next + start + new_length, *text + start + old_length, *length - start - old_length);
  next[n] = 0;
  TSInputEdit e = {start, start + old_length, start + new_length, point_at(*text, start),
                   point_at(*text, start + old_length), point_at(next, start + new_length)};
  ts_tree_edit(tree, &e);
  TSTree *result = ts_parser_parse_string(parser, tree, next, n);
  if (!result) exit(93);
  ts_tree_delete(tree);
  free(*text);
  *text = next;
  *length = n;
  return result;
}

static int hexval(char c) { return c >= 'a' ? c - 'a' + 10 : c - '0'; }

static int incremental(const char *base_path, const char *edits_path, int repair, int selftest) {
  uint32_t base_length, edits_length;
  char *base = read_file(base_path, &base_length), *edits = read_file(edits_path, &edits_length);
  enum { MAX_EDITS = 4096 };
  static uint32_t start[MAX_EDITS], old_length[MAX_EDITS], new_length[MAX_EDITS];
  static char *inserted[MAX_EDITS], *removed[MAX_EDITS];
  int count = 0;
  for (char *line = strtok(edits, "\n"); line; line = strtok(NULL, "\n")) {
    if (count >= MAX_EDITS) return 65;
    static char hex[140000];
    unsigned s, o;
    if (sscanf(line, "%u %u %139999s", &s, &o, hex) != 3) return 66;
    start[count] = s;
    old_length[count] = o;
    size_t h = strcmp(hex, "-") ? strlen(hex) : 0;
    new_length[count] = (uint32_t)(h / 2);
    inserted[count] = malloc(h / 2 + 1);
    for (size_t i = 0; i < h / 2; i++) inserted[count][i] = (char)(hexval(hex[2 * i]) * 16 + hexval(hex[2 * i + 1]));
    count++;
  }
  TSParser *parser = new_parser();
  char *text = malloc((size_t)base_length + 1);
  memcpy(text, base, (size_t)base_length + 1);
  uint32_t length = base_length;
  TSTree *original = ts_parser_parse_string(parser, NULL, text, length);
  Buf d_original = {0}, d_incremental = {0}, d_fresh = {0}, d_repaired = {0};
  uint64_t nodes = 0;
  uint32_t depth = 0;
  dump_tree(original, &d_original, NULL, &nodes, &depth);
  TSTree *tree = ts_tree_copy(original);
  double t = clock_ms();
  for (int i = 0; i < count; i++) {
    removed[i] = malloc((size_t)old_length[i] + 1);
    memcpy(removed[i], text + start[i], old_length[i]);
    tree = apply_edit(parser, tree, &text, &length, start[i], old_length[i], inserted[i], new_length[i]);
  }
  double incremental_ms = clock_ms() - t;
  t = clock_ms();
  TSTree *fresh = ts_parser_parse_string(parser, NULL, text, length);
  double fresh_ms = clock_ms() - t;
  nodes = 0;
  dump_tree(tree, &d_incremental, NULL, &nodes, &depth);
  uint64_t fresh_nodes = 0;
  dump_tree(fresh, &d_fresh, NULL, &fresh_nodes, &depth);
  if (selftest == 1 && d_fresh.n > 2) d_fresh.p[d_fresh.n / 2] ^= 1;
  int incremental_equal = same(&d_incremental, &d_fresh);
  int final_error = ts_node_has_error(ts_tree_root_node(tree));
  int repair_equal = -1;
  double repair_ms = -1;
  if (repair) {
    t = clock_ms();
    for (int i = count - 1; i >= 0; i--)
      tree = apply_edit(parser, tree, &text, &length, start[i], new_length[i], removed[i], old_length[i]);
    repair_ms = clock_ms() - t;
    uint64_t n2 = 0;
    dump_tree(tree, &d_repaired, NULL, &n2, &depth);
    if (selftest == 2 && d_original.n > 2) d_original.p[d_original.n / 2] ^= 1;
    repair_equal = length == base_length && !memcmp(text, base, base_length) && same(&d_repaired, &d_original);
  }
  printf("{\"final\":true,\"edits\":%d,\"incremental_equals_fresh\":%s,\"repair_equals_original\":%s,"
         "\"final_has_error\":%s,\"original_has_error\":%s,\"nodes_final\":%llu,\"incremental_ms\":%.6f,"
         "\"fresh_ms\":%.6f,\"repair_ms\":%.6f,\"selftest\":%d}\n",
         count, incremental_equal ? "true" : "false", repair_equal < 0 ? "null" : (repair_equal ? "true" : "false"),
         final_error ? "true" : "false", ts_node_has_error(ts_tree_root_node(original)) ? "true" : "false",
         (unsigned long long)nodes, incremental_ms, fresh_ms, repair_ms, selftest);
  ts_tree_delete(tree);
  ts_tree_delete(fresh);
  ts_tree_delete(original);
  ts_parser_delete(parser);
  return 0;
}

/* ----------------------------------------------------------------- RESUME */
typedef struct { unsigned count, trigger; int fired; } Counter;
static bool count_callback(TSParseState *state) {
  Counter *c = state->payload;
  c->count++;
  if (c->trigger && c->count == c->trigger) { c->fired = 1; return true; }
  return false;
}

static TSTree *parse_with(TSParser *parser, Input *in, Counter *counter) {
  TSParseOptions options = {counter, counter ? count_callback : NULL};
  return ts_parser_parse_with_options(parser, NULL, (TSInput){in, read_input, TSInputEncodingUTF8, NULL}, options);
}

static void dump_to(TSTree *tree, Buf *b) {
  uint64_t n = 0;
  uint32_t d = 0;
  b->n = 0;
  dump_tree(tree, b, NULL, &n, &d);
}

static int resume(const char *path, const char *target_path, uint32_t chunk, unsigned trigger) {
  uint32_t length, target_length;
  char *text = read_file(path, &length), *target = read_file(target_path, &target_length);
  Input whole = {text, length, 0}, chunked = {text, length, chunk}, other = {target, target_length, chunk};
  Buf fresh = {0}, fresh_chunked = {0}, fresh_target = {0}, got = {0};
  TSParser *p = new_parser();
  TSTree *t = ts_parser_parse_string(p, NULL, text, length);
  dump_to(t, &fresh);
  ts_tree_delete(t);
  t = parse_with(p, &chunked, NULL);
  dump_to(t, &fresh_chunked);
  ts_tree_delete(t);
  t = parse_with(p, &other, NULL);
  dump_to(t, &fresh_target);
  ts_tree_delete(t);
  ts_parser_delete(p);
  printf("{\"event\":\"fresh\",\"chunked_equals_whole\":%s,\"chunk\":%u}\n", same(&fresh, &fresh_chunked) ? "true" : "false",
         chunk);
  (void)whole;
  /* D1 resume the same source; D2 reset then the same source; D3 reset then another source. */
  for (int d = 1; d <= 3; d++) {
    p = new_parser();
    Counter c = {0, trigger, 0};
    TSTree *first = parse_with(p, &chunked, &c);
    int cancelled = first == NULL && c.fired;
    if (!cancelled) {
      printf("{\"event\":\"resume\",\"case\":\"D%d\",\"cancel_observed\":false,\"callbacks\":%u}\n", d, c.count);
      if (first) ts_tree_delete(first);
      ts_parser_delete(p);
      continue;
    }
    if (d >= 2) ts_parser_reset(p);
    Counter none = {0, 0, 0};
    t = parse_with(p, d == 3 ? &other : &chunked, &none);
    if (!t) return 88;
    dump_to(t, &got);
    int equal = same(&got, d == 3 ? &fresh_target : &fresh_chunked);
    printf("{\"event\":\"resume\",\"case\":\"D%d\",\"cancel_observed\":true,\"callbacks\":%u,\"equals_fresh\":%s}\n", d,
           c.count, equal ? "true" : "false");
    ts_tree_delete(t);
    ts_parser_delete(p);
  }
  puts("{\"final\":true}");
  return 0;
}

/* -------------------------------------------------------------------- TWO */
static int two(const char *a_path, const char *b_path) {
  uint32_t n, m;
  char *a = read_file(a_path, &n), *b = read_file(b_path, &m);
  TSParser *p = new_parser(), *q = new_parser();
  TSTree *x = ts_parser_parse_string(p, NULL, a, n);
  Buf before = {0}, after = {0};
  dump_to(x, &before);
  TSTree *y = ts_parser_parse_string(q, NULL, b, m);
  ts_parser_reset(q);
  dump_to(x, &after);
  int ok = same(&before, &after);
  ts_tree_delete(y);
  ts_parser_delete(q);
  ts_tree_delete(x);
  ts_parser_delete(p);
  printf("{\"final\":true,\"two_parser_independent\":%s}\n", ok ? "true" : "false");
  return ok ? 0 : 89;
}

int main(int argc, char **argv) {
  QueryPerformanceFrequency(&frequency);
  setvbuf(stdout, NULL, _IONBF, 0);
#ifdef MEASURE_ALLOC
  ts_set_allocator(counting_malloc, counting_calloc, counting_realloc, counting_free);
#endif
  if (argc == 6 && !strcmp(argv[1], "RUN")) return run(argv[2], argv[3], argv[4], atof(argv[5]));
  if (argc == 3 && !strcmp(argv[1], "DUMP")) {
    static char buffer[1 << 16];
    setvbuf(stdout, buffer, _IOFBF, sizeof buffer);
    TSParser *p = new_parser();
    int rc = dump_file(p, argv[2]);
    ts_parser_delete(p);
    printf("DUMP_DONE\t%d\n", rc);
    fflush(stdout);
    return rc;
  }
  if (argc == 3 && !strcmp(argv[1], "DUMPLIST")) {
    static char buffer[1 << 16];
    setvbuf(stdout, buffer, _IOFBF, sizeof buffer);
    uint32_t n;
    char *list = read_file(argv[2], &n);
    TSParser *p = new_parser();
    int rc = 0;
    for (char *line = strtok(list, "\r\n"); line && !rc; line = strtok(NULL, "\r\n")) rc = dump_file(p, line);
    ts_parser_delete(p);
    printf("DUMP_DONE\t%d\n", rc);
    fflush(stdout);
    return rc;
  }
  if (argc == 4 && !strcmp(argv[1], "CAPTURES")) return captures(argv[2], argv[3]);
  if (argc == 6 && !strcmp(argv[1], "INCREMENTAL")) return incremental(argv[2], argv[3], atoi(argv[4]), atoi(argv[5]));
  if (argc == 6 && !strcmp(argv[1], "RESUME"))
    return resume(argv[2], argv[3], (uint32_t)atoi(argv[4]), (unsigned)atoi(argv[5]));
  if (argc == 4 && !strcmp(argv[1], "TWO")) return two(argv[2], argv[3]);
  fputs("usage: see the header of scripts/qualify/probe.c\n", stderr);
  return 64;
}
