"""Offline ETW schema/interval/lifecycle controls; never activates local ETW."""
import copy
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

import etw_diagnostic as d
from run import etw_session


class EtwDiagnostic(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        (Path(__file__).resolve().parents[2] / ".work").mkdir(exist_ok=True)

    def test_registered_prefix(self):
        rows = d.prelude()
        self.assertEqual(len(rows), 5833)
        self.assertEqual(rows[-1], ["cand", "PARSE", "L-FOREACH-1MiB", 0, "rep3"])
        self.assertEqual(d.TARGETS, ["L-ANON-1MiB"] * 20 + ["V-FLAT-1MiB"] * 2
                         + ["V-LONGEXPR-1MiB"] * 2 + list(d.latency_diagnostic.WITNESSES))
        self.assertEqual(len(d.TARGETS), 26)

    def test_interval_and_mutants(self):
        # scheduled 10..20, ready 20..30, scheduled 30..40,
        # waiting 40..50, ready 50..60, scheduled 60..70.
        rows = [(20, 9, 7, 0, 36, 1, 0), (30, 7, 9, 0, 36, 1, 0),
                (40, 9, 7, 0, 36, 5, 0), (50, 7, 0, 1, 50, 0, 0), (60, 7, 9, 0, 36, 1, 0)]
        result = d.interval(rows, 7, 10, 70, 1000)
        self.assertEqual([result[k + "_ms"] for k in ("scheduled", "ready", "waiting", "unknown")], [30, 20, 10, 0])
        self.assertEqual(d.interval([], 7, 10, 70, 1000)["scheduled_ms"], 60)
        for bad in (rows[:-1], rows[1:], rows[:1] + rows, [rows[3]],
                    [(10, 9, 7, 0, 36, 1, 0), (70, 7, 9, 0, 36, 1, 0)],
                    [(10, 9, 7, 0, 36, 1, 0)], [(70, 7, 9, 0, 36, 1, 0)],
                    [(9, 9, 7, 0, 36, 1, 0), (71, 7, 9, 0, 36, 1, 0)],
                    [(11, 9, 7, 0, 36, 1, 0)], [(69, 7, 9, 0, 36, 1, 0)]):
            with self.assertRaises(ValueError):
                d.interval(bad, 7, 10, 70, 1000)

    def test_capture_rejects_loss_overflow_and_truncation(self):
        metadata = dict(ok=True, started=True, stopped=True, flags=0x10000810, error=0, start_status=0,
            malformed=0, overflow=0, consumer_status=0, events_lost=0, buffers_lost=0, buffer_kib=64,
            number_of_buffers=256, maximum_buffers=256, rows=1, qpc_start=1, qpc_end=100, qpc_frequency=1000)
        root = Path(__file__).resolve().parents[2] / ".work"
        with tempfile.TemporaryDirectory(dir=root) as temp:
            path = Path(temp) / "numeric.bin"
            path.write_bytes(d.ROW.pack(10, 7, 9, 0, 36, 1, 0))
            self.assertEqual(len(d.trace_rows(path, metadata)[0]), 1)
            for key, value in (("events_lost", 1), ("buffers_lost", 1), ("overflow", 1), ("malformed", 1),
                               ("maximum_buffers", 257), ("buffer_kib", 65), ("flags", 0), ("stopped", False),
                               ("rows", 2), ("rows", True), ("qpc_frequency", 0)):
                with self.subTest(key=key), self.assertRaises(ValueError):
                    d.trace_rows(path, dict(metadata, **{key: value}))

    def test_public_artifact_scope(self):
        import re
        text = (Path(__file__).resolve().parents[2] / ".github/workflows/native-characterization.yml").read_text()
        block = re.search(r"          path: \|\n((?:            [^\n]+\n)+)", text).group(1)
        self.assertEqual([x.strip() for x in block.splitlines()], [".work/native-characterization/" + name for name in (
            "identity.json", "runs.jsonl", "commands.jsonl", "etw-lifecycle.json", "etw-summary.json")])
        self.assertIn("  workflow_dispatch:", text)
        self.assertNotIn("  push:", text)
        self.assertIn("github.sha == inputs.expected_commit", text)
        self.assertIn("    if: inputs.experiment == 'etw' && github.run_attempt == 1", text)
        self.assertIn("    timeout-minutes: 30", text)
        self.assertEqual(text.count("uses: actions/upload-artifact@"), 2)

    def test_compatibility_has_one_session_and_no_parser(self):
        from types import SimpleNamespace
        import run
        root = Path(__file__).resolve().parents[2] / ".work"
        with tempfile.TemporaryDirectory(dir=root) as temp:
            lab = SimpleNamespace(out=Path(temp), cc=Path("unused-gcc"))
            collector = SimpleNamespace(supervisor=Path("unused-supervisor"))
            head = "a" * 40
            with patch.object(run.subprocess, "run", side_effect=[SimpleNamespace(stdout=head), SimpleNamespace(stdout="")]), \
                    patch.object(run.os, "environ", {"TSQ_ETW_EXPECTED_COMMIT": head}), \
                    patch.object(run, "sha", return_value="0" * 64), \
                    patch.object(run, "etw_collector", return_value=(collector, "unused.exe")), \
                    patch.object(run, "etw_session") as session:
                self.assertEqual(run.etw_compatibility(lab, []), 0)
                session.assert_called_once()
                args = session.call_args.args
                self.assertEqual(args[2:5], ("capture", [], Path(temp)))
                with patch.object(run.time, "sleep") as sleep:
                    args[5](0, lambda: True)
                    sleep.assert_called_once_with(1)
            identity = json.loads((Path(temp) / "identity.json").read_text())
            self.assertEqual(identity["scope"], dict(sessions=1, lifetime_seconds=60, buffer_bytes=64*2**20, parser_runs=0))
            self.assertFalse(identity["qualification"])

    def test_marker_identity_and_clock_rejections(self):
        case = next(iter(d.latency_diagnostic.WITNESSES))
        length = len(d.cases.generate(case))
        marker = dict(pid=10, tid=7, creation_filetime=1000, frequency=1000,
            parse_start=10, parse_end=70, cleanup_start=80, cleanup_end=90, gap_start=20, gap_end=50,
            gap_from_byte=0, gap_to_byte=length, parse_cpu_ms=30., cleanup_cpu_ms=10.)
        rec = {"completed": True, "build": "cand-etw", "case": case, "op": "PARSE", "budget": 0, "tag": "traced-0",
            "final": {"final": True, "op": "PARSE", "cancelled": False, "has_error": 1, "bytes": length,
                      "parse_ms": 60., "max_gap_incl_edges_ms": 30.},
            "report": {"pid": 10, "creation_filetime": 1000, "termination_reason": "COMPLETED", "exit_confirmed": True,
                       "exit_code_raw": 0, "active_processes": 0, "user_cpu_ms": 30., "kernel_cpu_ms": 10.},
            "events": {"etw_markers": marker, "cleanup": {"tree_delete_ms": 6., "parser_delete_ms": 4.},
                       "parse": {"cancelled": False, "budget_ms": 0, "request_ms": -1, "budget_cross_ms": -1,
                                 "callback_target": 0, "byte_target": 0, "live_at_budget": 0, "peak_after_budget": 0,
                                 "parse_ms": 60., "max_gap_incl_edges_ms": 30.}}}
        metadata = dict(qpc_start=1, qpc_end=100, qpc_frequency=1000)
        rows = [(5, 7, 9, 0, 36, 1, 0), (95, 9, 7, 0, 36, 4, 0)]
        self.assertEqual(d.observation(rec, rows, metadata, length)["phases"]["gap"]["wall_ms"], 30)
        for missing in ([], rows[:1], rows[1:]):
            with self.assertRaises(ValueError):
                d.observation(rec, missing, metadata, length)
        for key, value in (("pid", 11), ("creation_filetime", 1001), ("tid", 0), ("frequency", 1001),
                           ("parse_start", 0), ("parse_end", 69), ("cleanup_end", 101), ("gap_end", 71),
                           ("gap_from_byte", -1), ("parse_cpu_ms", float("nan"))):
            bad = copy.deepcopy(rec)
            bad["events"]["etw_markers"][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                d.observation(bad, rows, metadata, length)

    def test_lifecycle_cleanup_after_probe_or_collector_failure(self):
        root = Path(__file__).resolve().parents[2] / ".work"
        for defect in (None, "probe", "collector", "cleanup", "stop-write"):
            with tempfile.TemporaryDirectory(dir=root) as temp:
                class Collector:
                    out = Path(temp)
                    calls = []

                    def supervise(self, cid, argv, *args, **kwargs):
                        mode, folder = argv[1:]
                        self.calls.append(mode)
                        if mode == "capture":
                            (folder / "ownership.bin").write_bytes(b"0" * 16)
                            (folder / "ready.json").write_text("{}")
                            until = time.monotonic() + 1
                            while not (folder / "stop").exists() and time.monotonic() < until:
                                time.sleep(.001)
                            if defect == "collector":
                                raise RuntimeError("planted collector failure")
                            return {"termination_reason": "COMPLETED", "exit_code_raw": 0}, ""
                        return {"termination_reason": "COMPLETED", "exit_code_raw": 1 if defect == "cleanup" else 0}, \
                            "ETW_OWNED_SESSION_ABSENT"

                collector, receipts = Collector(), []

                def work(deadline, collector_active):
                    self.assertTrue(collector_active())
                    if defect == "probe":
                        raise RuntimeError("planted probe failure")

                write = Path.write_text

                def write_control(path, *args, **kwargs):
                    if defect == "stop-write" and path.name == "stop":
                        raise OSError("planted stop write failure")
                    return write(path, *args, **kwargs)

                with patch.object(Path, "write_text", write_control):
                    if defect:
                        with self.assertRaises((RuntimeError, OSError)):
                            etw_session(collector, "unused.exe", "capture", receipts, Path(temp), work)
                    else:
                        etw_session(collector, "unused.exe", "capture", receipts, Path(temp), work)
                self.assertEqual(collector.calls, ["capture", "stop-owned"])
                self.assertEqual(receipts[0]["pass"], defect is None)
                self.assertEqual(receipts[0]["absence_confirmed"], defect != "cleanup")
                if defect == "cleanup":
                    self.assertIsNone(receipts[0]["session_seconds_upper_bound"])
                self.assertEqual(json.loads((Path(temp) / "etw-lifecycle.json").read_text()), receipts)


if __name__ == "__main__":
    unittest.main()
