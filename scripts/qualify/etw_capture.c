/* Bounded diagnostic collector. Only numeric CSwitch/ReadyThread payloads are
 * retained; no ETL, process/command-line, environment, stack or system-config
 * recording. Live use is restricted by run.py to the authorized hosted job.
 * Microsoft schemas: /windows/win32/etw/cswitch and /readythread. */
#define _WIN32_WINNT 0x0601
#include <windows.h>
#include <evntrace.h>
#include <evntcons.h>
#include <objbase.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <stddef.h>
#include <string.h>
#include <wchar.h>

#define EVENT_LIMIT 1000000u
#define FLAGS (EVENT_TRACE_FLAG_CSWITCH | EVENT_TRACE_FLAG_DISPATCHER | EVENT_TRACE_FLAG_NO_SYSCONFIG)
static const wchar_t session_name[] = L"BrightScript v014 latency diagnosis";
static const GUID thread_guid = {0x3d6fa8d1,0xfe05,0x11d0,{0x9d,0xda,0x00,0xc0,0x4f,0xd7,0xba,0x7c}};
typedef struct { uint64_t tick; uint32_t next, previous; uint16_t cpu; uint8_t kind, state; uint32_t reserved; } Row;
_Static_assert(sizeof(Row) == 24, "fixed numeric trace format");
typedef struct { EVENT_TRACE_PROPERTIES p; wchar_t name[128]; } Properties;
static Row *rows;
static ULONG row_count, ignored;
static volatile LONG malformed, overflow;
static unsigned rejected_opcode, rejected_version, rejected_length, rejected_reason;
static TRACEHANDLE consumer = INVALID_PROCESSTRACE_HANDLE;
static ULONG consume_status;

static void properties(Properties *v, const GUID *guid) {
  memset(v, 0, sizeof *v);
  v->p.Wnode.BufferSize = sizeof *v;
  v->p.Wnode.Flags = WNODE_FLAG_TRACED_GUID;
  v->p.Wnode.ClientContext = 1; /* QPC, consumed without timestamp conversion. */
  if (guid) v->p.Wnode.Guid = *guid;
  v->p.LoggerNameOffset = offsetof(Properties, name);
  v->p.BufferSize = 64;
  v->p.MinimumBuffers = v->p.MaximumBuffers = 256; /* 16 MiB; rows add <24 MiB. */
  v->p.FlushTimer = 1;
  v->p.LogFileMode = EVENT_TRACE_REAL_TIME_MODE | EVENT_TRACE_SYSTEM_LOGGER_MODE | EVENT_TRACE_NO_PER_PROCESSOR_BUFFERING;
  v->p.EnableFlags = FLAGS;
}

/* Thread_V2 plus the observed CSwitch v5/28-byte shape only. Microsoft's
 * PerfView d1ad99bb87ac8b0a2230f193edf95d9238cca05c CSwitchTraceData uses
 * offsets 0/4/14 for these fields in versions >2 as well. The v5 tail is
 * neither interpreted nor copied. Unknown versions/lengths fail closed. */
static int decode(const EVENT_RECORD *e, Row *r) {
  if (memcmp(&e->EventHeader.ProviderId, &thread_guid, sizeof(GUID))) return 0;
  unsigned op = e->EventHeader.EventDescriptor.Opcode;
  if (op != 36 && op != 50) return 0;
  unsigned version = e->EventHeader.EventDescriptor.Version;
  if (version != 2 && !(op == 36 && version == 5)) return -1;
  if (e->UserDataLength != (op == 36 ? (version == 5 ? 28 : 24) : 8)) return -2;
  if (!e->UserData) return -3;
  if (e->EventHeader.TimeStamp.QuadPart <= 0) return -4;
  const unsigned char *p = e->UserData;
  memset(r, 0, sizeof *r);
  r->tick = (uint64_t)e->EventHeader.TimeStamp.QuadPart;
  r->cpu = e->BufferContext.ProcessorIndex;
  r->kind = (uint8_t)op;
  memcpy(&r->next, p, 4);
  if (op == 36) {
    memcpy(&r->previous, p + 4, 4);
    r->state = p[14];
    if (r->state > 9) return -5;
  }
  return 1;
}

static void WINAPI event_record(EVENT_RECORD *e) {
  Row r;
  int ok = decode(e, &r);
  if (ok < 0) {
    if (!malformed) {
      rejected_opcode = e->EventHeader.EventDescriptor.Opcode;
      rejected_version = e->EventHeader.EventDescriptor.Version;
      rejected_length = e->UserDataLength;
      rejected_reason = (unsigned)-ok;
    }
    InterlockedExchange(&malformed, 1);
    return;
  }
  if (!ok) { ignored++; return; }
  if (row_count == EVENT_LIMIT) { InterlockedExchange(&overflow, 1); return; }
  rows[row_count++] = r;
}

static DWORD WINAPI consume(void *unused) {
  (void)unused;
  consume_status = ProcessTrace(&consumer, 1, NULL, NULL);
  return 0;
}

static int filename(wchar_t *out, size_t count, const wchar_t *dir, const wchar_t *name) {
  int n = swprintf(out, count, L"%ls/%ls", dir, name);
  return n > 0 && (size_t)n < count;
}

static int stop_owned(const GUID *guid, Properties *v) {
  properties(v, NULL);
  ULONG code = ControlTraceW(0, session_name, &v->p, EVENT_TRACE_CONTROL_QUERY);
  if (code == ERROR_WMI_INSTANCE_NOT_FOUND) return 0;
  if (code || memcmp(&v->p.Wnode.Guid, guid, sizeof *guid)) return 1;
  return ControlTraceW(0, session_name, &v->p, EVENT_TRACE_CONTROL_STOP) != ERROR_SUCCESS;
}

static int cleanup(const wchar_t *dir) {
  wchar_t path[32768]; GUID guid; Properties v;
  if (!filename(path, 32768, dir, L"ownership.bin")) return 64;
  FILE *f = _wfopen(path, L"rb");
  if (!f) return 65;
  int ok = fread(&guid, sizeof guid, 1, f) == 1 && fgetc(f) == EOF;
  fclose(f);
  if (!ok || stop_owned(&guid, &v)) return 66;
  properties(&v, NULL);
  ULONG code = ControlTraceW(0, session_name, &v.p, EVENT_TRACE_CONTROL_QUERY);
  if (code != ERROR_WMI_INSTANCE_NOT_FOUND) return 67;
  puts("ETW_OWNED_SESSION_ABSENT");
  return 0;
}

static int selftest(void) {
  EVENT_RECORD e = {0}; unsigned char bytes[28] = {0}; Row r;
  e.EventHeader.ProviderId = thread_guid;
  e.EventHeader.TimeStamp.QuadPart = 123;
  e.EventHeader.EventDescriptor.Version = 2;
  e.EventHeader.EventDescriptor.Opcode = 36;
  e.UserData = bytes; e.UserDataLength = 24;
  bytes[0] = 3; bytes[4] = 5; bytes[14] = 2;
  if (decode(&e, &r) != 1 || r.next != 3 || r.previous != 5 || r.state != 2 || r.kind != 36) return 1;
  e.UserDataLength = 23; if (decode(&e, &r) != -2) return 2;
  e.UserDataLength = 24; bytes[14] = 255; if (decode(&e, &r) != -5) return 3;
  e.EventHeader.EventDescriptor.Opcode = 50; e.UserDataLength = 8;
  if (decode(&e, &r) != 1 || r.next != 3 || r.previous || r.state || r.kind != 50) return 4;
  e.UserDataLength = 7; if (decode(&e, &r) != -2) return 5;
  e.UserDataLength = 8; e.EventHeader.EventDescriptor.Version = 1; if (decode(&e, &r) != -1) return 6;
  e.EventHeader.EventDescriptor.Version = 255; if (decode(&e, &r) != -1) return 10;
  e.EventHeader.EventDescriptor.Version = 2; e.UserDataLength = 9; if (decode(&e, &r) != -2) return 11;
  e.EventHeader.EventDescriptor.Opcode = 36; e.UserDataLength = 25; if (decode(&e, &r) != -2) return 12;
  e.UserDataLength = 24; e.UserData = NULL; if (decode(&e, &r) != -3) return 13;
  e.UserData = bytes; e.EventHeader.TimeStamp.QuadPart = 0; if (decode(&e, &r) != -4) return 14;
  e.EventHeader.TimeStamp.QuadPart = 123; e.EventHeader.EventDescriptor.Version = 5;
  e.UserDataLength = 28; bytes[14] = 2; memset(bytes + 24, 0xee, 4);
  if (decode(&e, &r) != 1 || r.next != 3 || r.previous != 5 || r.state != 2 || r.reserved) return 16;
  e.UserDataLength = 27; if (decode(&e, &r) != -2) return 17;
  e.UserDataLength = 29; if (decode(&e, &r) != -2) return 18;
  e.UserDataLength = 28; e.EventHeader.EventDescriptor.Version = 6; if (decode(&e, &r) != -1) return 19;
  e.EventHeader.EventDescriptor.Version = 5; e.EventHeader.EventDescriptor.Opcode = 50;
  e.UserDataLength = 8; if (decode(&e, &r) != -1) return 20;
  e.EventHeader.EventDescriptor.Opcode = 36; e.UserDataLength = 24;
  e.EventHeader.TimeStamp.QuadPart = 123; e.EventHeader.EventDescriptor.Version = 255;
  event_record(&e);
  if (malformed != 1 || rejected_reason != 1 || rejected_opcode != 36 || rejected_version != 255 ||
      rejected_length != 24 || row_count != 0) return 15;
  e.EventHeader.EventDescriptor.Opcode = 1; if (decode(&e, &r)) return 7;
  e.EventHeader.ProviderId.Data1++; if (decode(&e, &r)) return 8;
  Properties p; properties(&p, NULL);
  if (p.p.EnableFlags != 0x10000810 || p.p.BufferSize * p.p.MaximumBuffers != 16384 || p.p.LogFileNameOffset) return 9;
  puts("ETW_OFFLINE_SELFTEST_PASS");
  return 0;
}

static int capture(const wchar_t *dir, int control) {
  GUID guid; Properties p, stopped;
  TRACEHANDLE controller = 0;
  HANDLE thread = NULL;
  wchar_t path[32768], ready[32768], stop[32768];
  LARGE_INTEGER start = {0}, end = {0}, frequency;
  int error = 0, started = 0, stop_ok = 0;
  ULONG status = 0;
  if (CoCreateGuid(&guid) != S_OK || !QueryPerformanceFrequency(&frequency)) return 70;
  if (!filename(path, 32768, dir, L"ownership.bin") || !filename(ready, 32768, dir, L"ready.json") ||
      !filename(stop, 32768, dir, L"stop")) return 71;
  FILE *f = _wfopen(path, L"wbx");
  if (!f) return 72;
  int written = fwrite(&guid, sizeof guid, 1, f) == 1;
  if (fclose(f) || !written) return 73;
  rows = calloc(EVENT_LIMIT, sizeof *rows);
  if (!rows) return 74;
  properties(&p, &guid);
  status = StartTraceW(&controller, session_name, &p.p);
  if (status) { error = 75; goto done; }
  started = 1;
  QueryPerformanceCounter(&start);
  if (p.p.BufferSize > 64 || p.p.MinimumBuffers > 256 || p.p.MaximumBuffers > 256 ||
      p.p.NumberOfBuffers > 256 || p.p.EnableFlags != FLAGS) { error = 76; goto done; }
  EVENT_TRACE_LOGFILEW log = {0};
  log.LoggerName = (LPWSTR)session_name;
  log.ProcessTraceMode = PROCESS_TRACE_MODE_REAL_TIME | PROCESS_TRACE_MODE_EVENT_RECORD | PROCESS_TRACE_MODE_RAW_TIMESTAMP;
  log.EventRecordCallback = event_record;
  consumer = OpenTraceW(&log);
  if (consumer == INVALID_PROCESSTRACE_HANDLE) { status = GetLastError(); error = 77; goto done; }
  thread = CreateThread(NULL, 0, consume, NULL, 0, NULL);
  if (!thread) { status = GetLastError(); error = 78; goto done; }
  if (!filename(path, 32768, dir, L"ready.tmp")) { error = 79; goto done; }
  f = _wfopen(path, L"wbx");
  if (!f) { error = 80; goto done; }
  fprintf(f, "{\"qpc_start\":%llu,\"qpc_frequency\":%llu}\n", (unsigned long long)start.QuadPart,
          (unsigned long long)frequency.QuadPart);
  if (fclose(f) || !MoveFileExW(path, ready, 0)) { error = 81; goto done; }
  /* Hosted negative controls deliberately leave our session for parent cleanup. */
  if (control == 1) ExitProcess(92);
  if (control == 2) for (;;) Sleep(100);
  for (;;) {
    QueryPerformanceCounter(&end);
    if (GetFileAttributesW(stop) != INVALID_FILE_ATTRIBUTES) break;
    if ((end.QuadPart - start.QuadPart) / (double)frequency.QuadPart >= 30 || malformed || overflow ||
        WaitForSingleObject(thread, 0) != WAIT_TIMEOUT) { error = 82; break; }
    Sleep(10);
  }
done:
  if (started) {
    stop_ok = !stop_owned(&guid, &stopped);
    QueryPerformanceCounter(&end);
    if (!stop_ok) error = 83;
  } else memset(&stopped, 0, sizeof stopped);
  if (thread && WaitForSingleObject(thread, 5000) != WAIT_OBJECT_0) {
    if (consumer != INVALID_PROCESSTRACE_HANDLE) CloseTrace(consumer);
    /* Process exit ends only our consumer thread; the parent verifies the owned session is absent. */
    return 84;
  }
  if (consumer != INVALID_PROCESSTRACE_HANDLE) CloseTrace(consumer);
  if (thread) CloseHandle(thread);
  if (consume_status || malformed || overflow || stopped.p.EventsLost || stopped.p.LogBuffersLost ||
      stopped.p.RealTimeBuffersLost || (started && (end.QuadPart-start.QuadPart)/(double)frequency.QuadPart > 35)) error = 85;
  if (!filename(path, 32768, dir, L"numeric-private.bin")) return 86;
  f = _wfopen(path, L"wbx");
  if (!f) return 87;
  written = fwrite(rows, sizeof *rows, row_count, f) == row_count;
  if (fclose(f) || !written) error = 88;
  free(rows);
  if (!filename(path, 32768, dir, L"capture.json")) return 89;
  f = _wfopen(path, L"wbx");
  if (!f) return 90;
  fprintf(f, "{\"ok\":%s,\"error\":%d,\"start_status\":%lu,\"started\":%s,\"stopped\":%s,"
      "\"rows\":%lu,\"ignored\":%lu,\"malformed\":%ld,\"overflow\":%ld,\"consumer_status\":%lu,"
      "\"events_lost\":%lu,\"buffers_lost\":%lu,\"qpc_start\":%llu,\"qpc_end\":%llu,\"qpc_frequency\":%llu,"
      "\"rejected_opcode\":%u,\"rejected_version\":%u,\"rejected_length\":%u,\"rejected_reason\":%u,"
      "\"flags\":%lu,\"buffer_kib\":%lu,\"maximum_buffers\":%lu,\"number_of_buffers\":%lu}\n",
      !error && row_count ? "true" : "false", error, status, started ? "true" : "false", stop_ok ? "true" : "false",
      row_count, ignored, malformed, overflow, consume_status, stopped.p.EventsLost,
      stopped.p.LogBuffersLost + stopped.p.RealTimeBuffersLost, (unsigned long long)start.QuadPart,
      (unsigned long long)end.QuadPart, (unsigned long long)frequency.QuadPart,
      rejected_opcode, rejected_version, rejected_length, rejected_reason, p.p.EnableFlags,
      stopped.p.BufferSize, stopped.p.MaximumBuffers, stopped.p.NumberOfBuffers);
  if (fclose(f)) return 91;
  printf("ETW_CAPTURE_%s rows=%lu error=%d\n", !error && row_count ? "COMPLETE" : "INCOMPLETE", row_count, error);
  return error || !row_count ? 1 : 0;
}

int wmain(int argc, wchar_t **argv) {
  if (argc == 2 && !wcscmp(argv[1], L"--selftest")) return selftest();
  if (argc != 3) return 64;
  if (!wcscmp(argv[1], L"assert-absent")) {
    Properties v; properties(&v, NULL);
    if (ControlTraceW(0, session_name, &v.p, EVENT_TRACE_CONTROL_QUERY) != ERROR_WMI_INSTANCE_NOT_FOUND) return 67;
    puts("ETW_OWNED_SESSION_ABSENT");
    return 0;
  }
  if (!wcscmp(argv[1], L"capture")) return capture(argv[2], 0);
  if (!wcscmp(argv[1], L"crash-control")) return capture(argv[2], 1);
  if (!wcscmp(argv[1], L"stall-control")) return capture(argv[2], 2);
  if (!wcscmp(argv[1], L"stop-owned")) return cleanup(argv[2]);
  return 64;
}
