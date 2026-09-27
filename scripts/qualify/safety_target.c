/* Finite native lifecycle replay and libFuzzer target. Test-only, MIT.
 * All runtime/parser/scanner units are instrumented. Arbitrary bytes need not
 * be valid BrightScript. A complete valid repair must equal a fresh parse.
 */
#include <windows.h>
#include <tree_sitter/api.h>
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

extern const TSLanguage *tree_sitter_brightscript(void);
static TSQuery *query;
static uint64_t calls, captures, nodes, cancelled;
static const char repair[] = "sub Main()\n print 1\nend sub\n";
static const char *corpus_dir;

static void finish(void) {
  if (query) ts_query_delete(query);
  printf("TSQ_SUMMARY calls=%llu captures=%llu nodes=%llu cancelled=%llu\n",
    (unsigned long long)calls, (unsigned long long)captures,
    (unsigned long long)nodes, (unsigned long long)cancelled);
}
static char *file(const char *path, uint32_t *size) {
  FILE *f = fopen(path, "rb");
  if (!f || fseek(f, 0, SEEK_END)) abort();
  long n = ftell(f);
  if (n < 0 || n > 65536 || fseek(f, 0, SEEK_SET)) abort();
  char *b = malloc((size_t)n + 1);
  if (!b || fread(b, 1, (size_t)n, f) != (size_t)n) abort();
  fclose(f); b[n] = 0; *size = (uint32_t)n;
  return b;
}
int LLVMFuzzerInitialize(int *argc, char ***argv) {
  (void)argc; (void)argv;
  char image[32768];
  HMODULE asan = GetModuleHandleA("libclang_rt.asan_dynamic-x86_64.dll");
  const char *expected = getenv("TSQ_ASAN_DLL");
  assert(asan && expected && GetModuleFileNameA(asan, image, sizeof image));
  assert(!_stricmp(image, expected));
  printf("TSQ_ASAN_IMAGE %s\n", image);
  const char *path = getenv("TSQ_QUERY");
  if (!path) abort();
  uint32_t n, offset; TSQueryError error;
  char *text = file(path, &n);
  query = ts_query_new(tree_sitter_brightscript(), text, n, &offset, &error);
  free(text);
  if (!query || error != TSQueryErrorNone) abort();
  corpus_dir = getenv("TSQ_FUZZ_CORPUS");
  atexit(finish);
  return 0;
}
static void corpus_budget(void) {
  if (!corpus_dir) return;
  char pattern[32768];
  if (snprintf(pattern, sizeof pattern, "%s\\*", corpus_dir) >= (int)sizeof pattern) abort();
  WIN32_FIND_DATAA info;
  HANDLE h = FindFirstFileA(pattern, &info);
  if (h == INVALID_HANDLE_VALUE) abort();
  uint64_t bytes = 0;
  do {
    if (info.dwFileAttributes & FILE_ATTRIBUTE_REPARSE_POINT) abort();
    if (!(info.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY))
      bytes += ((uint64_t)info.nFileSizeHigh << 32) | info.nFileSizeLow;
  } while (FindNextFileA(h, &info));
  FindClose(h);
  /* One next discovery is at most max_len. Stop before it can exceed 32 MiB. */
  if (bytes > 32 * 1024 * 1024 - 65536) {
    fputs("TSQ_CORPUS_LIMIT\n", stderr);
    exit(86);
  }
}
static TSParser *parser(void) {
  TSParser *p = ts_parser_new();
  assert(p && ts_parser_set_language(p, tree_sitter_brightscript()));
  return p;
}
static int next(TSTreeCursor *c) {
  if (ts_tree_cursor_goto_first_child(c)) return 1;
  while (!ts_tree_cursor_goto_next_sibling(c))
    if (!ts_tree_cursor_goto_parent(c)) return 0;
  return 1;
}
static void bounds(TSTree *tree, uint32_t size) {
  assert(tree);
  TSTreeCursor c = ts_tree_cursor_new(ts_tree_root_node(tree));
  do {
    TSNode n = ts_tree_cursor_current_node(&c);
    assert(ts_node_start_byte(n) <= ts_node_end_byte(n) && ts_node_end_byte(n) <= size);
    nodes++;
  } while (next(&c));
  ts_tree_cursor_delete(&c);
}
static void equal(TSTree *a, TSTree *b) {
  TSTreeCursor x = ts_tree_cursor_new(ts_tree_root_node(a)), y = ts_tree_cursor_new(ts_tree_root_node(b));
  for (;;) {
    TSNode n = ts_tree_cursor_current_node(&x), m = ts_tree_cursor_current_node(&y);
    assert(ts_node_symbol(n) == ts_node_symbol(m));
    assert(ts_node_start_byte(n) == ts_node_start_byte(m) && ts_node_end_byte(n) == ts_node_end_byte(m));
    assert(ts_node_is_named(n) == ts_node_is_named(m) && ts_node_is_missing(n) == ts_node_is_missing(m));
    assert(ts_node_is_extra(n) == ts_node_is_extra(m) && ts_node_has_error(n) == ts_node_has_error(m));
    assert(ts_tree_cursor_current_depth(&x) == ts_tree_cursor_current_depth(&y));
    assert(ts_tree_cursor_current_field_id(&x) == ts_tree_cursor_current_field_id(&y));
    int nx = next(&x), ny = next(&y);
    assert(nx == ny);
    if (!nx) break;
  }
  ts_tree_cursor_delete(&x); ts_tree_cursor_delete(&y);
}
static TSPoint end_point(const uint8_t *data, size_t size) {
  TSPoint p = {0, 0};
  for (size_t i = 0; i < size; i++)
    if (data[i] == '\n') { p.row++; p.column = 0; } else p.column++;
  return p;
}
typedef struct { const uint8_t *data; uint32_t size; } Input;
static const char *read_input(void *payload, uint32_t offset, TSPoint position, uint32_t *n) {
  (void)position;
  Input *in = payload;
  *n = offset < in->size ? in->size - offset : 0;
  return *n ? (const char *)in->data + offset : "";
}
static bool cancel_once(TSParseState *state) {
  (*(unsigned *)state->payload)++;
  return true;
}
int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size) {
  if (size > 65536) abort();
  corpus_budget(); calls++;
  TSParser *p = parser(), *q = parser();
  TSTree *original = ts_parser_parse_string(p, NULL, (const char *)data, (uint32_t)size);
  bounds(original, (uint32_t)size);
  TSQueryCursor *cursor = ts_query_cursor_new();
  assert(cursor);
  ts_query_cursor_set_match_limit(cursor, UINT32_MAX);
  ts_query_cursor_exec(cursor, query, ts_tree_root_node(original));
  TSQueryMatch match; uint32_t index;
  while (ts_query_cursor_next_capture(cursor, &match, &index)) {
    assert(index < match.capture_count);
    TSNode n = match.captures[index].node;
    assert(ts_node_start_byte(n) <= ts_node_end_byte(n) && ts_node_end_byte(n) <= size);
    captures++;
  }
  assert(!ts_query_cursor_did_exceed_match_limit(cursor));
  ts_query_cursor_delete(cursor);

  TSTree *copy = ts_tree_copy(original);
  TSInputEdit e = {0, (uint32_t)size, sizeof(repair)-1, {0,0},
                  end_point(data,size), end_point((const uint8_t *)repair,sizeof(repair)-1)};
  ts_tree_edit(copy, &e);
  TSTree *fixed = ts_parser_parse_string(p, copy, repair, sizeof(repair)-1);
  TSTree *fresh = ts_parser_parse_string(q, NULL, repair, sizeof(repair)-1);
  assert(fixed && fresh && !ts_node_has_error(ts_tree_root_node(fixed)));
  equal(fixed, fresh);
  ts_tree_delete(copy); ts_tree_delete(fixed);

  Input in = {data, (uint32_t)size};
  for (int reset = 0; reset < 2; reset++) {
    ts_parser_reset(p);
    unsigned callbacks = 0;
    TSTree *first = ts_parser_parse_with_options(p, NULL,
      (TSInput){&in, read_input, TSInputEncodingUTF8, NULL},
      (TSParseOptions){&callbacks, cancel_once});
    if (!first) {
      assert(callbacks > 0); cancelled++;
      if (reset) {
        ts_parser_reset(p);
        first = ts_parser_parse_string(p, NULL, repair, sizeof(repair)-1);
        assert(first); equal(first, fresh);
      } else {
        first = ts_parser_parse_with_options(p, NULL,
          (TSInput){&in, read_input, TSInputEncodingUTF8, NULL}, (TSParseOptions){0});
        bounds(first, (uint32_t)size);
        if (!ts_node_has_error(ts_tree_root_node(original))) equal(first, original);
      }
    }
    assert(first);
    ts_tree_delete(first);
  }
  TSTree *independent = ts_parser_parse_string(q, NULL, (const char *)data, (uint32_t)size);
  bounds(independent, (uint32_t)size);
  if (!ts_node_has_error(ts_tree_root_node(original))) equal(original, independent);
  ts_tree_delete(independent); ts_tree_delete(original); ts_tree_delete(fresh);
  ts_parser_delete(p); ts_parser_delete(q);
  return 0;
}
#ifdef TSQ_REPLAY
int main(int argc, char **argv) {
  if (argc != 2) return 64;
  LLVMFuzzerInitialize(&argc, &argv);
  uint32_t n; char *data = file(argv[1], &n);
  LLVMFuzzerTestOneInput((uint8_t *)data, n);
  free(data);
  puts("REPLAY_COMPLETE");
  return 0;
}
#endif
