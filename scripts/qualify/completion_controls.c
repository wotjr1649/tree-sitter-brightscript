/* Private state-transition tests. Phase markers exist only in the test copy. */
static unsigned control_checkpoint_phase;
#include "completion-parser-controls.c"
#define main retained_probe_main
#include "probe.c"
#undef main
#include "completion_guard.h"

const TSLanguage *tree_sitter_checkpoint_control(void);

typedef struct {
  TSParser *parser;
  int target_phase, target_zero;
  unsigned seen[2][2], calls, at_cancel;
  bool fired;
} Checkpoint;

static bool checkpoint_callback(TSParseState *state) {
  Checkpoint *check = state->payload;
  check->calls++;
  unsigned phase = control_checkpoint_phase;
  control_checkpoint_phase = 0;
  if (!phase) return false;
  assert(phase <= 2 && check->parser->finished_tree.ptr);
  assert(ts_parser__can_cancel_completion(check->parser));
  unsigned zero = ts_stack_version_count(check->parser->stack) == 0;
  assert(state->current_byte_offset == check->parser->lexer.current_position.bytes);
  assert(state->has_error == check->parser->has_error);
  check->seen[phase - 1][zero]++;
  if (check->target_phase == -1 ||
      (check->target_phase == (int)phase && check->target_zero == (int)zero)) {
    assert(!check->fired);
    check->fired = true;
    check->at_cancel = check->calls;
    return true;
  }
  return false;
}

static TSParser *make_parser(const TSLanguage *language, bool ranged) {
  TSParser *p = ts_parser_new();
  assert(ts_parser_set_language(p, language));
  if (ranged) {
    TSRange ranges[] = {{{1,0},{2,0},7,11},{{3,0},{4,0},18,22}};
    assert(ts_parser_set_included_ranges(p, ranges, 2));
  }
  return p;
}

static TSTree *parse_control(TSParser *p, Input *input, Checkpoint *check) {
  control_checkpoint_phase = 0;
  return ts_parser_parse_with_options(p,NULL,(TSInput){input,read_input,TSInputEncodingUTF8,NULL},
      (TSParseOptions){check,check ? checkpoint_callback : NULL});
}

static void check_eligibility(const TSLanguage *language) {
  TSParser *p=make_parser(language,false);
  Input input={(char *)"x=1\n",4,0};
  TSTree *tree=parse_control(p,&input,NULL);
  assert(tree && !ts_parser__can_cancel_completion(p));
  ts_subtree_retain(tree->root);
  p->finished_tree=tree->root;
  assert(!ts_parser__can_cancel_completion(p)); /* active base version */
  ts_stack_pause(p->stack,0,NULL_SUBTREE);
  assert(!ts_parser__can_cancel_completion(p)); /* paused alternative */
  ts_stack_copy_version(p->stack,0);
  ts_stack_halt(p->stack,0);
  assert(!ts_parser__can_cancel_completion(p)); /* halted + paused */
  ts_stack_halt(p->stack,1);
  assert(ts_parser__can_cancel_completion(p));
  ts_stack_remove_version(p->stack,1);
  assert(ts_parser__can_cancel_completion(p));
  ts_stack_remove_version(p->stack,0);
  assert(ts_parser__can_cancel_completion(p) && ts_parser_has_outstanding_parse(p));
  ts_parser_delete(p);
  ts_tree_delete(tree);
  finish_case();
}

static void compare_tree(TSTree *tree, Buf *expected) {
  assert(tree);
  Buf actual = {0};
  dump_to(tree,&actual);
  assert(same(&actual,expected));
  free(actual.p);
}

static unsigned check_case(const char *name, const TSLanguage *language, const char *text, bool ranged,
                           unsigned covered[2][2]) {
  Input input = {(char *)text,(uint32_t)strlen(text),3};
  TSParser *p = make_parser(language,ranged);
  TSTree *tree = parse_control(p,&input,NULL);
  assert(tree && !ts_parser_has_outstanding_parse(p));
  Buf expected = {0};
  dump_to(tree,&expected);
  ts_tree_delete(tree);
  Checkpoint observe = {.parser=p};
  tree = parse_control(p,&input,&observe);
  compare_tree(tree,&expected);
  assert(!ts_parser_has_outstanding_parse(p));
  ts_tree_delete(tree);
  ts_parser_delete(p);
  finish_case();
  unsigned checks = 0;
  for (unsigned phase=1;phase<=2;phase++) {
    for (unsigned zero=0;zero<=1;zero++) {
      covered[phase-1][zero] += observe.seen[phase-1][zero];
      if (!observe.seen[phase-1][zero]) continue;
      for (unsigned action=0;action<4;action++) {
        p=make_parser(language,ranged);
        Checkpoint check={.parser=p,.target_phase=(int)phase,.target_zero=(int)zero};
        tree=parse_control(p,&input,&check);
        assert(!tree && check.fired && check.calls==check.at_cancel);
        assert(p->finished_tree.ptr && ts_parser_has_outstanding_parse(p));
        assert((ts_stack_version_count(p->stack)==0)==(bool)zero);
        if (action==2) {
          ts_parser_delete(p);
        } else {
          if (action==1) {
            ts_parser_reset(p);
            assert(!p->finished_tree.ptr && !ts_parser_has_outstanding_parse(p));
          }
          if (action==3) {
            for (unsigned repeat=0;repeat<2;repeat++) {
              check=(Checkpoint){.parser=p,.target_phase=-1};
              tree=parse_control(p,&input,&check);
              assert(!tree && check.fired && check.calls==check.at_cancel && p->finished_tree.ptr);
              assert(ts_parser_has_outstanding_parse(p));
            }
          }
          check=(Checkpoint){.parser=p};
          tree=parse_control(p,&input,&check);
          compare_tree(tree,&expected);
          assert(!ts_parser_has_outstanding_parse(p));
          ts_tree_delete(tree);
          ts_parser_delete(p);
        }
        finish_case();
        checks++;
      }
    }
  }
  printf("CHECKPOINT_CASE %s controls=%u pre=%u/%u post=%u/%u\n",name,checks,
      observe.seen[0][0],observe.seen[0][1],observe.seen[1][0],observe.seen[1][1]);
  free(expected.p);
  return checks;
}

int main(int argc, char **argv) {
  setvbuf(stdout,NULL,_IONBF,0);
  guard_initialize();
  ts_set_allocator(guard_malloc,guard_calloc,guard_realloc,guard_free);
  if (argc == 2) {
    volatile unsigned char *p=guard_malloc(16);
    guard_free((void *)p);
    if (!strcmp(argv[1], "uaf")) { puts("CONTROL_UAF_ARMED"); return *p; }
    if (!strcmp(argv[1], "double-free")) { puts("CONTROL_DOUBLE_FREE_ARMED"); guard_free((void *)p); }
    return 91;
  }
  assert(argc == 1);
  unsigned covered[2][2]={{0}},total=0;
  const TSLanguage *bright=tree_sitter_brightscript(),*toy=tree_sitter_checkpoint_control();
  check_eligibility(bright);
  check_eligibility(toy);
  total+=check_case("scanner-valid",bright,"sub main()\nx=1\nprint x\nend sub\n",false,covered);
  total+=check_case("scanner-recovery",bright,"x = function()\nx = function()\nx = function()\n",false,covered);
  total+=check_case("no-scanner-valid",toy,"x=1\ny=2\nz=3\n",false,covered);
  total+=check_case("no-scanner-recovery",toy,"x=1\ny=",false,covered);
  total+=check_case("no-scanner-ranges",toy,"ignore\nx=1\nignore\nx=2\n",true,covered);
  char deeper[129 * 15 + 1] = {0};
  for (unsigned i=0;i<129;i++) strcat(deeper,"x = function()\n");
  total+=check_case("scanner-deeper-recovery",bright,deeper,false,covered);
  assert(covered[0][0] && covered[1][0] && covered[1][1]);
  ts_set_allocator(NULL,NULL,NULL,NULL);
  printf("CHECKPOINT_CONTROLS_PASS %u state transitions; guarded allocator live=0\n",total);
  return 0;
}
