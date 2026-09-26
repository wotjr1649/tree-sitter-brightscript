/**
 * @file Benign child for the supervisor self-test of the release qualification lane.
 * @license MIT
 *
 * benign normal|sleep|memory|output|descendant|private-env
 */
#define _WIN32_WINNT 0x0601
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(int argc, char **argv) {
  if (argc != 2) return 64;
  setvbuf(stdout, NULL, _IONBF, 0);
  if (!strcmp(argv[1], "normal")) { puts("NORMAL_COMPLETED"); return 0; }
  if (!strcmp(argv[1], "sleep")) { puts("SLEEP_BEGIN"); Sleep(2000); return 0; }
  if (!strcmp(argv[1], "memory")) {
    for (int i = 0; i < 96; ++i) {
      void *p = VirtualAlloc(NULL, 1024 * 1024, MEM_RESERVE | MEM_COMMIT, PAGE_READWRITE);
      if (!p) { printf("ALLOCATION_DENIED %d %lu\n", i, GetLastError()); return 73; }
      memset(p, 1, 1024 * 1024);
    }
    puts("MEMORY_GUARD_DID_NOT_LIMIT"); return 74;
  }
  if (!strcmp(argv[1], "output")) {
    char b[4096]; memset(b, 'x', sizeof b);
    for (int i = 0; i < 512; ++i) if (fwrite(b, 1, sizeof b, stdout) != sizeof b) return 75;
    return 0;
  }
  if (!strcmp(argv[1], "descendant")) {
    char executable[32768], command[32768];
    if (!GetModuleFileNameA(NULL, executable, sizeof executable)) return 76;
    if (snprintf(command, sizeof command, "\"%s\" sleep", executable) >= (int)sizeof command) return 77;
    STARTUPINFOA startup = {0}; PROCESS_INFORMATION child = {0};
    startup.cb = sizeof startup;
    if (!CreateProcessA(executable, command, NULL, NULL, FALSE, DETACHED_PROCESS, NULL, NULL, &startup, &child)) return 78;
    FILETIME c, e, k, u;
    if (!GetProcessTimes(child.hProcess, &c, &e, &k, &u)) return 79;
    printf("DESCENDANT %lu %llu\n", child.dwProcessId,
           ((unsigned long long)c.dwHighDateTime << 32) | c.dwLowDateTime);
    CloseHandle(child.hThread); CloseHandle(child.hProcess);
    return 0;
  }
  if (!strcmp(argv[1], "private-env")) {
    const char *names[] = {"HOME", "USERPROFILE", "APPDATA", "LOCALAPPDATA", "TEMP", "TMP",
        "XDG_CACHE_HOME", "XDG_CONFIG_HOME", "XDG_STATE_HOME", "TREE_SITTER_LIBDIR", "TREE_SITTER_DIR"};
    for (unsigned i = 0; i < sizeof names / sizeof *names; ++i) {
      const char *value = getenv(names[i]);
      if (!value || !strstr(value, "tsq-private")) return 80;
    }
    if (getenv("S05_PRIVATE_CANARY")) return 81;
    puts("PRIVATE_ENV_COMPLETED"); return 0;
  }
  return 64;
}
