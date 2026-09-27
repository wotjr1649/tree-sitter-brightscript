/* POSIX controls for the native qualification supervisor. MIT license. */
#define _DEFAULT_SOURCE
#define _DARWIN_C_SOURCE
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/types.h>
#include <unistd.h>

int main(int argc, char **argv) {
  if (argc != 2) return 64;
  setvbuf(stdout, NULL, _IONBF, 0);
  if (!strcmp(argv[1], "normal")) { puts("NORMAL_COMPLETED"); return 0; }
  if (!strcmp(argv[1], "sleep")) { puts("SLEEP_BEGIN"); sleep(2); return 0; }
  if (!strcmp(argv[1], "memory")) {
    /* Reserve virtual address space without faulting pages into the runner. */
    for (int i = 0; i < 64; ++i) {
      void *p = mmap(NULL, 128 * 1024 * 1024, PROT_READ | PROT_WRITE,
                     MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
      if (p == MAP_FAILED) { printf("ALLOCATION_DENIED %d %d\n", i, errno); return 73; }
    }
    puts("MEMORY_GUARD_DID_NOT_LIMIT"); return 74;
  }
  if (!strcmp(argv[1], "output")) {
    char b[4096]; memset(b, 'x', sizeof b);
    for (int i = 0; i < 512; ++i) if (fwrite(b, 1, sizeof b, stdout) != sizeof b) return 75;
    return 0;
  }
  if (!strcmp(argv[1], "descendant")) {
    pid_t child = fork();
    if (child < 0) return 76;
    if (!child) { sleep(5); return 0; }
    printf("DESCENDANT %ld\n", (long)child);
    return 0;
  }
  if (!strcmp(argv[1], "private-env")) {
    const char *names[] = {"HOME", "TMPDIR", "XDG_CACHE_HOME", "XDG_CONFIG_HOME",
                           "XDG_STATE_HOME", "TREE_SITTER_LIBDIR", "TREE_SITTER_DIR"};
    for (unsigned i = 0; i < sizeof names / sizeof *names; ++i) {
      const char *value = getenv(names[i]);
      if (!value || !strstr(value, "tsq-private")) return 80;
    }
    if (getenv("S05_PRIVATE_CANARY")) return 81;
    puts("PRIVATE_ENV_COMPLETED"); return 0;
  }
  return 64;
}
