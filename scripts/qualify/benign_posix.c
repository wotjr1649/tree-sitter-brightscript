/* POSIX controls for the native qualification supervisor. MIT license. */
#define _DEFAULT_SOURCE
#define _DARWIN_C_SOURCE
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/types.h>
#include <time.h>
#include <unistd.h>

int main(int argc, char **argv) {
  if (argc != 2) return 64;
  setvbuf(stdout, NULL, _IONBF, 0);
  if (!strcmp(argv[1], "normal")) { puts("NORMAL_COMPLETED"); return 0; }
  if (!strcmp(argv[1], "sleep")) { puts("SLEEP_BEGIN"); sleep(2); return 0; }
  if (!strcmp(argv[1], "memory")) {
#ifdef __APPLE__
    /* Fault pages in gradually so the parent's physical-footprint guard can observe them. */
    const struct timespec pause = {0, 2000000};
    for (int i = 0; i < 256; ++i) {
      volatile char *p = malloc(1024 * 1024);
      if (!p) { printf("ALLOCATION_DENIED %d %d\n", i, errno); return 73; }
      for (size_t j = 0; j < 1024 * 1024; j += 4096) p[j] = 1;
      nanosleep(&pause, NULL);
    }
#else
    /* Reserve virtual address space without faulting pages into the runner. */
    for (int i = 0; i < 64; ++i) {
      void *p = mmap(NULL, 128 * 1024 * 1024, PROT_READ | PROT_WRITE,
                     MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
      if (p == MAP_FAILED) { printf("ALLOCATION_DENIED %d %d\n", i, errno); return 73; }
    }
#endif
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
  if (!strcmp(argv[1], "descendant-closed")) {
    pid_t child = fork();
    if (child < 0) return 76;
    if (!child) { close(STDOUT_FILENO); close(STDERR_FILENO); sleep(5); return 0; }
    printf("DESCENDANT_CLOSED %ld\n", (long)child);
    return 0;
  }
#ifdef __APPLE__
  if (!strcmp(argv[1], "memory-child") || !strcmp(argv[1], "memory-child-orphan")) {
    int orphan = !strcmp(argv[1], "memory-child-orphan");
    pid_t child = fork();
    if (child < 0) return 76;
    if (!child) {
      const struct timespec pause = {0, 2000000};
      for (int i = 0; i < 256; ++i) {
        volatile char *p = malloc(1024 * 1024);
        if (!p) return 73;
        for (size_t j = 0; j < 1024 * 1024; j += 4096) p[j] = 1;
        if (orphan) puts("MEMORY_CHILD_ALIVE");
        nanosleep(&pause, NULL);
      }
      return 74;
    }
    puts("MEMORY_CHILD_BEGIN");
    if (orphan) return 0;
    sleep(5);
    return 0;
  }
#endif
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
