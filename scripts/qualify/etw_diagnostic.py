"""Offline interpretation of the fixed Windows diagnostic; never a release gate.

Only derived durations are published. CSwitch 'scheduled' time can include
interrupts and VM pauses; it is not equivalent to CPU execution time.
"""
import hashlib
import json
import re
import struct
from pathlib import Path

import cases
import gates
import latency_diagnostic

PREFIX_SHA = "34c946cf775ee671d6b1c8fed0c474d82b887588f04a7bfc3a88c8e57dd5483d"
TARGETS = ["L-ANON-1MiB"] * 20
TARGETS += [f"{name}-1MiB" for name in ("V-FLAT", "V-LONGEXPR") for _ in range(2)]
TARGETS += list(latency_diagnostic.WITNESSES)
ROW = struct.Struct("<QIIHBBI")


def prelude():
    data = (Path(__file__).parent / "etw-prelude.json").read_bytes()
    if hashlib.sha256(data).hexdigest() != PREFIX_SHA:
        raise ValueError("ETW prelude identity mismatch")
    plan = json.loads(data)
    rows = plan["runs"]
    if len(rows) != 5833:
        raise ValueError("ETW prelude count mismatch")
    for build, op, case, budget, tag in rows:
        if (build not in ("cand", "cand-alloc", "aa-left", "aa-right", "bp", "slow")
                or op not in ("PARSE", "LIFECYCLE", "QUERY_ONLY", "NAV_CURSOR", "NAV_FIELD", "NAV_INDEX",
                              "CANCEL_FIRST", "CANCEL_HALF")
                or not isinstance(case, str) or re.fullmatch(r"[A-Za-z0-9-]{1,96}", case) is None
                or type(budget) is not int or not 0 <= budget <= 2000
                or not isinstance(tag, str) or re.fullmatch(r"[A-Za-z0-9-]*", tag) is None):
            raise ValueError("invalid ETW prelude row")
    return rows


def trace_rows(path, metadata):
    integers = ("flags", "error", "start_status", "malformed", "overflow", "consumer_status", "events_lost",
                "buffers_lost", "buffer_kib", "number_of_buffers", "maximum_buffers", "rows", "qpc_start",
                "qpc_end", "qpc_frequency")
    if (any(type(metadata.get(k)) is not int or metadata[k] < 0 for k in integers)
            or metadata.get("ok") is not True or metadata.get("started") is not True
            or metadata.get("stopped") is not True or metadata.get("flags") != 0x10000810
            or any(metadata.get(k) != 0 for k in ("error", "start_status", "malformed", "overflow",
                                                  "consumer_status", "events_lost", "buffers_lost"))
            or not 0 < metadata.get("buffer_kib", 0) <= 64
            or not 0 < metadata.get("number_of_buffers", 0) <= metadata.get("maximum_buffers", 0) <= 256
            or not 0 < metadata.get("rows", 0) <= 1000000
            or not 0 < metadata.get("qpc_start", 0) < metadata.get("qpc_end", 0)
            or not 0 < metadata.get("qpc_frequency", 0)):
        raise ValueError("incomplete ETW capture")
    if path.stat().st_size != metadata["rows"] * ROW.size:
        raise ValueError("ETW row count mismatch")
    data = path.read_bytes()
    rows = list(ROW.iter_unpack(data))
    if any(t <= 0 or kind not in (36, 50) or state > 9 or reserved
           for t, new, old, cpu, kind, state, reserved in rows):
        raise ValueError("invalid ETW numeric row")
    # ProcessTrace merges CPU buffers; sorting also makes equal-timestamp input
    # order explicit. Ambiguous state transitions fail rather than invent time.
    return sorted(rows, key=lambda row: row[0]), hashlib.sha256(data).hexdigest()


def interval(rows, tid, begin, end, frequency):
    if not 0 < begin < end or frequency <= 0 or tid <= 0:
        raise ValueError("invalid ETW interval")
    state, cursor = "scheduled", begin  # the probe executed the begin QPC call
    totals = dict(scheduled=0, ready=0, waiting=0, unknown=0)
    counts = dict(switch_out=0, switch_in=0, ready=0)
    for tick, new, old, cpu, kind, oldstate, _ in rows:
        # Microsoft documents +/-1 QPC tick ordering uncertainty across threads.
        if min(abs(tick - begin), abs(tick - end)) <= 1 and tid in (new, old):
            raise ValueError("ambiguous ETW event at QPC boundary")
        if tick <= begin or tick >= end or tid not in (new, old):
            continue
        totals[state] += tick - cursor
        cursor = tick
        if kind == 50:
            if new != tid or state == "scheduled":
                raise ValueError("inconsistent ReadyThread event")
            state = "ready"
            counts["ready"] += 1
        elif old == tid and new != tid:
            if state != "scheduled":
                raise ValueError("duplicate switch out")
            state = "ready" if oldstate in (1, 3, 7) else "waiting" if oldstate == 5 else "unknown"
            counts["switch_out"] += 1
        elif new == tid and old != tid:
            if state == "scheduled":
                raise ValueError("duplicate switch in")
            state = "scheduled"
            counts["switch_in"] += 1
        else:
            raise ValueError("self switch")
    if state != "scheduled":
        raise ValueError("target did not return to CPU before end marker")
    totals[state] += end - cursor
    return {**{key + "_ms": ticks * 1000 / frequency for key, ticks in totals.items()},
            "wall_ms": (end - begin) * 1000 / frequency, "events": counts}


def observation(rec, rows, metadata, length):
    marker = rec.get("events", {}).get("etw_markers", {})
    plain = dict(rec, build="cand")
    if (not latency_diagnostic.witness_record(plain, rec["case"], length)
            or rec["build"] != "cand-etw" or marker.get("pid") != rec["report"]["pid"]
            or marker.get("creation_filetime") != rec["report"]["creation_filetime"]
            or type(marker.get("tid")) is not int or marker["tid"] <= 0
            or marker.get("frequency") != metadata["qpc_frequency"]
            or not all(type(marker.get(k)) is int for k in
                       ("parse_start", "parse_end", "cleanup_start", "cleanup_end", "gap_start", "gap_end"))
            or not (metadata["qpc_start"] < marker["parse_start"] < marker["parse_end"]
                    <= marker["cleanup_start"] < marker["cleanup_end"] < metadata["qpc_end"])
            or not marker["parse_start"] <= marker["gap_start"] < marker["gap_end"] <= marker["parse_end"]
            or not all(type(marker.get(k)) is int and 0 <= marker[k] <= length
                       for k in ("gap_from_byte", "gap_to_byte"))
            or any(gates.number(marker.get(k)) is None for k in ("parse_cpu_ms", "cleanup_cpu_ms"))):
        raise ValueError("incomplete ETW probe markers")
    if (not any(metadata["qpc_start"] < tick < marker["parse_start"] and kind == 36 and new == marker["tid"]
                for tick, new, old, cpu, kind, state, reserved in rows)
            or not any(marker["cleanup_end"] < tick < metadata["qpc_end"] and kind == 36 and old == marker["tid"]
                       for tick, new, old, cpu, kind, state, reserved in rows)):
        raise ValueError("target thread trace inclusion is unproved")
    result = {name: interval(rows, marker["tid"], marker[name + "_start"], marker[name + "_end"],
                             marker["frequency"]) for name in ("parse", "cleanup", "gap")}
    p, c = rec["events"]["parse"], rec["events"]["cleanup"]
    # Both paths use the same QPC calls, so tolerate decimal printing/float
    # conversion only, not a whole additional counter tick.
    tolerance = 0.000005
    if (abs(result["parse"]["wall_ms"] - p["parse_ms"]) > tolerance
            or abs(result["gap"]["wall_ms"] - p["max_gap_incl_edges_ms"]) > tolerance
            or result["cleanup"]["wall_ms"] - c["tree_delete_ms"] - c["parser_delete_ms"] < -tolerance):
        raise ValueError("ETW markers differ from probe timings")
    return {"case": rec["case"], "tag": rec["tag"], "phases": result,
            "parse_cpu_ms": marker["parse_cpu_ms"], "cleanup_cpu_ms": marker["cleanup_cpu_ms"],
            "gap_from_byte": marker["gap_from_byte"], "gap_to_byte": marker["gap_to_byte"]}
