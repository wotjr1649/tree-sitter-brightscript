"""Witness data rejection controls; no parser-performance claim."""
import copy
import unittest
from pathlib import Path
import tempfile

import latency_diagnostic as d


class WitnessRecords(unittest.TestCase):
    def test_registration_and_rejections(self):
        case = next(iter(d.WITNESSES))
        length = len(d.gates.cases.generate(case))
        rec = {"completed": True, "build": "cand", "case": case, "op": "PARSE", "budget": 0,
               "final": {"final": True, "op": "PARSE", "cancelled": False, "has_error": 1,
                         "bytes": length, "parse_ms": 1., "max_gap_incl_edges_ms": .5},
               "report": {"termination_reason": "COMPLETED", "exit_confirmed": True, "exit_code_raw": 0,
                          "active_processes": 0, "user_cpu_ms": 0., "kernel_cpu_ms": 0.},
               "events": {"parse": {"cancelled": False, "budget_ms": 0, "request_ms": -1,
                         "budget_cross_ms": -1, "callback_target": 0, "byte_target": 0,
                         "live_at_budget": 0, "peak_after_budget": 0, "parse_ms": 1.,
                         "max_gap_incl_edges_ms": .5}}}
        self.assertTrue(d.witness_record(rec, case, length))
        for path, value in [(('op',), 'QUERY_ONLY'), (('budget',), True), (('case',), 'other'),
            (('final','op'),'QUERY_ONLY'), (('final','cancelled'),True), (('final','bytes'),length+1),
            (('final','has_error'),0), (('final','parse_ms'),2.), (('final','max_gap_incl_edges_ms'),.6),
            (('final','parse_ms'),True), (('events','parse','callback_target'),False),
            (('events','parse','parse_ms'),float('nan')), (('events','parse','cancelled'),True),
            (('events','parse','budget_ms'),100), (('events','parse','live_at_budget'),1),
            (('events','parse','budget_ms'),False),
            (('report','termination_reason'),'DESCENDANTS_TERMINATED'), (('report','exit_confirmed'),False),
            (('report','exit_code_raw'),1), (('report','active_processes'),1),
            (('report','user_cpu_ms'),float('nan')), (('report','kernel_cpu_ms'),-1)]:
            bad = copy.deepcopy(rec)
            target = bad
            for key in path[:-1]: target = target[key]
            target[path[-1]] = value
            with self.subTest(path=path): self.assertFalse(d.witness_record(bad, case, length))
        bad = copy.deepcopy(rec)
        bad['events']['parse']['max_gap_incl_edges_ms'] = bad['final']['max_gap_incl_edges_ms'] = 2.
        self.assertFalse(d.witness_record(bad, case, length))
        work = Path(__file__).resolve().parents[2] / ".work"
        work.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="latency-records-", dir=work) as temp:
            class Inputs:
                def input(self, name): return Path(temp) / name
            r = Inputs()
            for name in d.WITNESSES: r.input(name).write_bytes(d.gates.cases.generate(name))
            self.assertEqual(set(d.witness_inputs(r)), set(d.WITNESSES))
            r.input(case).write_bytes(b'changed')
            with self.assertRaises(ValueError): d.witness_inputs(r)


if __name__ == '__main__':
    unittest.main()
