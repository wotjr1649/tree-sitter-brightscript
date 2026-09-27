/* Test-only sanitizer/coverage controls; never linked into the grammar. MIT. */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#ifdef TSQ_FUZZ_CONTROL
static volatile unsigned observed;
int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size) {
  if (size > 0 && data[0] == 'a') observed++;
  if (size > 1 && data[0] == 'a' && data[1] == 'b') observed += 2;
  if (size > 2 && data[2] == 'c') observed += 3;
  return 0;
}
#else
int main(int argc, char **argv) {
  if (argc != 2) return 64;
  volatile unsigned char *p = malloc(8);
  if (!p) return 70;
  memset((void *)p, 7, 8);
  size_t index = !strcmp(argv[1], "oob") ? 16 : 1;
  printf("CONTROL %u\n", (unsigned)p[index]);
  free((void *)p);
  return 0;
}
#endif
