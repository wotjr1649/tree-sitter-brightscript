/**
 * @file Job-object supervisor of the release qualification lane (Windows).
 * @license MIT
 *
 * supervisor <report.json> <child.out> <commit_cap_bytes> <watchdog_ms> <output_cap_bytes> <image> <command_line>
 * Runs one child suspended inside a private job with process and job memory
 * limits, kill-on-close and die-on-unhandled-exception, resumes it, enforces
 * the watchdog and the output cap, and reports one JSON object. Promoted from
 * artifacts/session-05-2 tools/supervisor.c (sha256 15573ee1...), unchanged below.
 */
#define _WIN32_WINNT 0x0601
#include <windows.h>
#include <psapi.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <wchar.h>

/* Local diagnostic supervisor. Only its CreateProcess handle and private job are controlled. */
static double milliseconds(void) {
  LARGE_INTEGER count, frequency;
  QueryPerformanceCounter(&count);
  QueryPerformanceFrequency(&frequency);
  return 1000.0 * count.QuadPart / frequency.QuadPart;
}

static void json_wide(FILE *out, const wchar_t *value) {
  char buffer[32768];
  int n = WideCharToMultiByte(CP_UTF8, 0, value, -1, buffer, sizeof buffer, NULL, NULL);
  if (!n) { fputs("null", out); return; }
  fputc('"', out);
  for (int i = 0; i < n - 1; ++i) {
    unsigned char ch = buffer[i];
    if (ch == '\\' || ch == '"') fputc('\\', out);
    if (ch < 32) fprintf(out, "\\u%04x", ch); else fputc(ch, out);
  }
  fputc('"', out);
}

int wmain(int argc, wchar_t **argv) {
  if (argc != 8) return 64;
  SIZE_T cap = _wcstoui64(argv[3], NULL, 10);
  DWORD deadline = wcstoul(argv[4], NULL, 10);
  uint64_t output_cap = _wcstoui64(argv[5], NULL, 10);
  if (cap < 16 * 1024 * 1024 || cap > 1024ULL * 1024 * 1024 ||
      deadline < 10 || deadline > 15000 || !output_cap || output_cap > 8 * 1024 * 1024) return 64;

  HANDLE job = NULL, port = NULL, read_pipe = NULL, write_pipe = NULL, input = NULL;
  PROCESS_INFORMATION process = {0};
  STARTUPINFOEXW startup = {0};
  JOBOBJECT_EXTENDED_LIMIT_INFORMATION limits = {0};
  JOBOBJECT_BASIC_ACCOUNTING_INFORMATION accounting = {0};
  PROCESS_MEMORY_COUNTERS_EX memory = {0};
  FILETIME created = {0}, exited = {0}, kernel = {0}, user = {0};
  FILE *raw = NULL, *report = NULL;
  BOOL assigned = FALSE, resumed = FALSE, ended = FALSE, truncated = FALSE, memory_event = FALSE;
  BOOL attributes_initialized = FALSE;
  DWORD failure = 0, exit_code = STILL_ACTIVE, total_processes = 0;
  const char *reason = "COMPLETED";
  uint64_t stored = 0, observed = 0;
  double begin = milliseconds(), end = begin;
  wchar_t image[32768] = L"";
  SIZE_T attribute_size = 0;
  SECURITY_ATTRIBUTES sa = {sizeof(sa), NULL, TRUE};
  SetErrorMode(SEM_FAILCRITICALERRORS | SEM_NOGPFAULTERRORBOX | SEM_NOOPENFILEERRORBOX);
#define REQUIRE(call) do { if (!(call)) { failure = GetLastError(); if (!failure) failure = ERROR_INVALID_DATA; reason = "HARNESS_FAILURE"; goto cleanup; } } while (0)

  report = _wfopen(argv[1], L"wbx");
  if (!report) return 65;
  raw = _wfopen(argv[2], L"wbx");
  if (!raw) { failure = ERROR_WRITE_FAULT; reason = "HARNESS_FAILURE"; goto cleanup; }
  job = CreateJobObjectW(NULL, NULL);
  REQUIRE(job);
  limits.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_PROCESS_MEMORY |
      JOB_OBJECT_LIMIT_JOB_MEMORY | JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE |
      JOB_OBJECT_LIMIT_DIE_ON_UNHANDLED_EXCEPTION;
  limits.ProcessMemoryLimit = cap;
  limits.JobMemoryLimit = cap;
  REQUIRE(SetInformationJobObject(job, JobObjectExtendedLimitInformation, &limits, sizeof limits));
  port = CreateIoCompletionPort(INVALID_HANDLE_VALUE, NULL, 0, 1);
  REQUIRE(port);
  JOBOBJECT_ASSOCIATE_COMPLETION_PORT association = {job, port};
  REQUIRE(SetInformationJobObject(job, JobObjectAssociateCompletionPortInformation, &association, sizeof association));
  REQUIRE(CreatePipe(&read_pipe, &write_pipe, &sa, 0));
  REQUIRE(SetHandleInformation(read_pipe, HANDLE_FLAG_INHERIT, 0));
  input = CreateFileW(L"NUL", GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_WRITE, &sa, OPEN_EXISTING, 0, NULL);
  REQUIRE(input != INVALID_HANDLE_VALUE);
  startup.StartupInfo.cb = sizeof startup;
  startup.StartupInfo.dwFlags = STARTF_USESTDHANDLES;
  startup.StartupInfo.hStdInput = input;
  startup.StartupInfo.hStdOutput = write_pipe;
  startup.StartupInfo.hStdError = write_pipe;
  InitializeProcThreadAttributeList(NULL, 1, 0, &attribute_size);
  startup.lpAttributeList = HeapAlloc(GetProcessHeap(), 0, attribute_size);
  REQUIRE(startup.lpAttributeList);
  REQUIRE(InitializeProcThreadAttributeList(startup.lpAttributeList, 1, 0, &attribute_size));
  attributes_initialized = TRUE;
  HANDLE inherited[] = {input, write_pipe};
  REQUIRE(UpdateProcThreadAttribute(startup.lpAttributeList, 0, PROC_THREAD_ATTRIBUTE_HANDLE_LIST,
                                   inherited, sizeof inherited, NULL, NULL));
  REQUIRE(CreateProcessW(argv[6], argv[7], NULL, NULL, TRUE,
      CREATE_SUSPENDED | DETACHED_PROCESS | EXTENDED_STARTUPINFO_PRESENT,
      NULL, NULL, &startup.StartupInfo, &process));
  REQUIRE(GetProcessTimes(process.hProcess, &created, &exited, &kernel, &user));
  DWORD image_size = sizeof image / sizeof *image;
  REQUIRE(QueryFullProcessImageNameW(process.hProcess, 0, image, &image_size));
  REQUIRE(AssignProcessToJobObject(job, process.hProcess));
  assigned = TRUE;
  BOOL in_job = FALSE;
  REQUIRE(IsProcessInJob(process.hProcess, job, &in_job) && in_job);
  CloseHandle(write_pipe); write_pipe = NULL;
  begin = milliseconds();
  REQUIRE(ResumeThread(process.hThread) != (DWORD)-1);
  resumed = TRUE;

  for (;;) {
    /* Read at most one chunk per iteration so an output flood cannot starve the watchdog. */
    DWORD available = 0;
    if (PeekNamedPipe(read_pipe, NULL, 0, NULL, &available, NULL) && available) {
      char buffer[16384]; DWORD got = 0;
      REQUIRE(ReadFile(read_pipe, buffer, available < sizeof buffer ? available : sizeof buffer, &got, NULL));
      observed += got;
      size_t keep = stored < output_cap ? (size_t)(output_cap - stored) : 0;
      if (keep > got) keep = got;
      if (keep && fwrite(buffer, 1, keep, raw) != keep) {
        failure = ERROR_WRITE_FAULT; reason = "HARNESS_FAILURE"; goto cleanup;
      }
      stored += keep;
      if (observed > output_cap) {
        truncated = TRUE; reason = "OUTPUT_LIMIT_REACHED"; goto cleanup;
      }
    }
    DWORD message; ULONG_PTR key; LPOVERLAPPED detail;
    while (GetQueuedCompletionStatus(port, &message, &key, &detail, 0)) {
      if (message == JOB_OBJECT_MSG_PROCESS_MEMORY_LIMIT || message == JOB_OBJECT_MSG_JOB_MEMORY_LIMIT)
        memory_event = TRUE;
    }
    DWORD wait = WaitForSingleObject(process.hProcess, 0);
    if (wait == WAIT_FAILED) { failure = GetLastError(); reason = "HARNESS_FAILURE"; goto cleanup; }
    if (wait == WAIT_OBJECT_0) {
      ended = TRUE;
      REQUIRE(QueryInformationJobObject(job, JobObjectBasicAccountingInformation, &accounting, sizeof accounting, NULL));
      total_processes = accounting.TotalProcesses;
      if (accounting.ActiveProcesses) { reason = "DESCENDANTS_TERMINATED"; goto cleanup; }
      if (PeekNamedPipe(read_pipe, NULL, 0, NULL, &available, NULL) && available) continue;
      break;
    }
    if (milliseconds() - begin >= deadline) { reason = "WATCHDOG_TERMINATED"; goto cleanup; }
    Sleep(1);
  }

cleanup:
  if (process.hProcess) {
    if (assigned && (strcmp(reason, "COMPLETED") || !ended)) {
      if (!TerminateJobObject(job, 0xE0502001)) { failure = GetLastError(); reason = "HARNESS_FAILURE"; }
    } else if (!assigned) {
      /* A failed job assignment never resumes the owned suspended process. */
      if (!TerminateProcess(process.hProcess, 0xE0502002)) { failure = GetLastError(); reason = "HARNESS_FAILURE"; }
    }
    if (WaitForSingleObject(process.hProcess, 3000) != WAIT_OBJECT_0) {
      failure = ERROR_TIMEOUT; reason = "UNKNOWN_PROCESS_STATE";
    } else {
      ended = TRUE;
      if (!GetExitCodeProcess(process.hProcess, &exit_code)) { failure = GetLastError(); reason = "HARNESS_FAILURE"; }
      memory.cb = sizeof memory;
      if (!GetProcessMemoryInfo(process.hProcess, (PROCESS_MEMORY_COUNTERS *)&memory, sizeof memory)) {
        failure = GetLastError(); reason = "HARNESS_FAILURE";
      }
    }
  }
  if (assigned) {
    double cleanup_deadline = milliseconds() + 3000;
    do {
      if (!QueryInformationJobObject(job, JobObjectBasicAccountingInformation, &accounting, sizeof accounting, NULL)) {
        failure = GetLastError(); reason = "HARNESS_FAILURE"; break;
      }
      total_processes = accounting.TotalProcesses;
      if (!accounting.ActiveProcesses) break;
      Sleep(1);
    } while (milliseconds() < cleanup_deadline);
    if (accounting.ActiveProcesses) { failure = ERROR_TIMEOUT; reason = "UNKNOWN_PROCESS_STATE"; }
    if (!QueryInformationJobObject(job, JobObjectExtendedLimitInformation, &limits, sizeof limits, NULL)) {
      failure = GetLastError(); reason = "HARNESS_FAILURE";
    }
  }
  end = milliseconds();
  /* All owned processes have stopped; retain any final buffered phase markers within the same cap. */
  if (raw && read_pipe && assigned && !accounting.ActiveProcesses) {
    DWORD available = 0;
    while (PeekNamedPipe(read_pipe, NULL, 0, NULL, &available, NULL) && available) {
      char buffer[16384]; DWORD got = 0;
      if (!ReadFile(read_pipe, buffer, available < sizeof buffer ? available : sizeof buffer, &got, NULL)) {
        failure = GetLastError(); reason = "HARNESS_FAILURE"; break;
      }
      observed += got;
      size_t keep = stored < output_cap ? (size_t)(output_cap - stored) : 0;
      if (keep > got) keep = got;
      if (keep && fwrite(buffer, 1, keep, raw) != keep) { failure = ERROR_WRITE_FAULT; reason = "HARNESS_FAILURE"; break; }
      stored += keep;
      if (observed > output_cap) { truncated = TRUE; if (!failure) reason = "OUTPUT_LIMIT_REACHED"; break; }
    }
  }
  if (raw) { if (fclose(raw)) { failure = ERROR_WRITE_FAULT; reason = "HARNESS_FAILURE"; } }
  if (report) {
    uint64_t creation = ((uint64_t)created.dwHighDateTime << 32) | created.dwLowDateTime;
    fprintf(report, "{\"schema_version\":1,\"pid\":%lu,\"parent_pid\":%lu,\"creation_filetime\":%llu,"
      "\"job_handle\":%llu,\"assigned_before_resume\":%s,\"resumed\":%s,\"exit_confirmed\":%s,"
      "\"exit_code_raw\":%lu,\"termination_reason\":\"%s\",\"win32_error\":%lu,"
      "\"memory_limit_event\":%s,\"output_truncated\":%s,\"output_stored_bytes\":%llu,"
      "\"output_observed_bytes\":%llu,\"wall_ms\":%.3f,\"peak_working_set_bytes\":%llu,"
      "\"peak_commit_bytes\":%llu,\"job_peak_commit_bytes\":%llu,\"active_processes\":%lu,"
      "\"total_processes\":%lu,\"configured_process_memory_limit_bytes\":%llu,"
      "\"configured_job_memory_limit_bytes\":%llu,\"limit_flags\":%lu,\"image_path\":",
      process.dwProcessId, GetCurrentProcessId(), (unsigned long long)creation,
      (unsigned long long)(uintptr_t)job, assigned ? "true" : "false", resumed ? "true" : "false",
      ended ? "true" : "false", exit_code, reason, failure, memory_event ? "true" : "false",
      truncated ? "true" : "false", (unsigned long long)stored, (unsigned long long)observed, end - begin,
      (unsigned long long)memory.PeakWorkingSetSize, (unsigned long long)limits.PeakProcessMemoryUsed,
      (unsigned long long)limits.PeakJobMemoryUsed, accounting.ActiveProcesses, total_processes,
      (unsigned long long)limits.ProcessMemoryLimit, (unsigned long long)limits.JobMemoryLimit,
      limits.BasicLimitInformation.LimitFlags);
    json_wide(report, image);
    fputs("}\n", report);
    if (fclose(report)) failure = ERROR_WRITE_FAULT;
  }
  if (process.hThread) CloseHandle(process.hThread);
  if (process.hProcess) CloseHandle(process.hProcess);
  if (write_pipe) CloseHandle(write_pipe);
  if (read_pipe) CloseHandle(read_pipe);
  if (input && input != INVALID_HANDLE_VALUE) CloseHandle(input);
  if (startup.lpAttributeList) { if (attributes_initialized) DeleteProcThreadAttributeList(startup.lpAttributeList); HeapFree(GetProcessHeap(), 0, startup.lpAttributeList); }
  if (port) CloseHandle(port);
  if (job) CloseHandle(job);
  return failure ? 70 : 0;
}
