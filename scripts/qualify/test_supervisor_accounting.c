/* Pure state-classification checks; these do not substitute for native Job tests. */
#define wmain supervisor_main
#include "supervisor.c"
#undef wmain
#include <assert.h>

int main(void) {
  assert(accounting_state(1, 1, FALSE) == ACCOUNTING_ROOT_PENDING);
  assert(accounting_state(1, 1, TRUE) == ACCOUNTING_ROOT_PENDING);
  assert(accounting_state(0, 1, TRUE) == ACCOUNTING_EMPTY);
  assert(accounting_state(0, 1, FALSE) == ACCOUNTING_EMPTY);
  assert(accounting_state(1, 2, FALSE) == ACCOUNTING_DESCENDANTS);
  assert(accounting_state(1, 2, TRUE) == ACCOUNTING_DESCENDANTS);
  assert(accounting_state(0, 2, TRUE) == ACCOUNTING_DESCENDANTS);
  assert(accounting_state(0, 2, FALSE) == ACCOUNTING_EMPTY);
  assert(accounting_state(0, 0, TRUE) == ACCOUNTING_INVALID);
  assert(accounting_state(2, 1, TRUE) == ACCOUNTING_INVALID);
  puts("ACCOUNTING_STATE_PASS 10");
  return 0;
}
