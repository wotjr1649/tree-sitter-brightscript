/* Guarded allocator for completion controls only; never linked into a probe.
 * Released regions stay inaccessible until the bounded test case ends.
 */
#ifndef _WIN32
#include <sys/mman.h>
#include <unistd.h>
#endif

typedef struct { void *base, *ptr; size_t bytes, pages; bool live; } Allocation;
static Allocation guard_allocations[4096];
static unsigned allocation_count, live_count;
static size_t page_size;

static void guard_initialize(void) {
#ifdef _WIN32
  SetErrorMode(SEM_FAILCRITICALERRORS | SEM_NOGPFAULTERRORBOX | SEM_NOOPENFILEERRORBOX);
  SYSTEM_INFO info;
  GetSystemInfo(&info);
  page_size = info.dwPageSize;
#else
  long size = sysconf(_SC_PAGESIZE);
  assert(size > 0);
  page_size = (size_t)size;
  struct rlimit no_core = {0, 0};
  assert(setrlimit(RLIMIT_CORE, &no_core) == 0);
#endif
  assert(page_size && page_size % 16 == 0);
  _Static_assert(_Alignof(max_align_t) <= 16, "guarded malloc alignment");
}

static Allocation *lookup(void *ptr) {
  for (unsigned i = 0; i < allocation_count; i++) {
    if (guard_allocations[i].ptr == ptr) return &guard_allocations[i];
  }
  assert(false);
  return NULL;
}

static void *guard_malloc(size_t bytes) {
  assert(bytes < 1024 * 1024 && allocation_count < 4096);
  size_t aligned = ((bytes ? bytes : 1) + 15) & ~(size_t)15;
  size_t pages = (aligned + page_size - 1) / page_size * page_size;
#ifdef _WIN32
  void *base = VirtualAlloc(NULL, pages + page_size, MEM_RESERVE, PAGE_NOACCESS);
  assert(base && VirtualAlloc(base, pages, MEM_COMMIT, PAGE_READWRITE) == base);
#else
  void *base = mmap(NULL, pages + page_size, PROT_NONE, MAP_PRIVATE | MAP_ANON, -1, 0);
  assert(base != MAP_FAILED && mprotect(base, pages, PROT_READ | PROT_WRITE) == 0);
#endif
  void *ptr = (char *)base + pages - aligned;
  memset(ptr, 0xa5, bytes);
  guard_allocations[allocation_count++] = (Allocation){base, ptr, bytes, pages, true};
  live_count++;
  return ptr;
}

static void guard_free(void *ptr) {
  if (!ptr) return;
  Allocation *a = lookup(ptr);
  assert(a->live);
#ifdef _WIN32
  assert(VirtualFree(a->base, a->pages, MEM_DECOMMIT));
#else
  assert(mprotect(a->base, a->pages, PROT_NONE) == 0);
#endif
  a->live = false;
  live_count--;
}

static void *guard_calloc(size_t n, size_t size) {
  assert(!size || n <= SIZE_MAX / size);
  void *ptr = guard_malloc(n * size);
  memset(ptr, 0, n * size);
  return ptr;
}

static void *guard_realloc(void *ptr, size_t size) {
  if (!ptr) return guard_malloc(size);
  Allocation *a = lookup(ptr);
  assert(a->live);
  size_t old_size = a->bytes;
  void *next = guard_malloc(size);
  memcpy(next, ptr, size < old_size ? size : old_size);
  guard_free(ptr);
  return next;
}

static void finish_case(void) {
  assert(live_count == 0);
  for (unsigned i = 0; i < allocation_count; i++) {
    assert(!guard_allocations[i].live);
#ifdef _WIN32
    assert(VirtualFree(guard_allocations[i].base, 0, MEM_RELEASE));
#else
    assert(munmap(guard_allocations[i].base, guard_allocations[i].pages + page_size) == 0);
#endif
  }
  allocation_count = 0;
}
