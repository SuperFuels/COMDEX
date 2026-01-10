#!/usr/bin/env python3
"""
v28 — Projection Query Without Full Materialization

We build:
  - A snapshot stream (NDJSON): full state every tick
  - A template+delta stream (NDJSON): state0 once + deltas per tick

Then we answer: "what is value at index q after k updates?"

Baseline (snapshot): decompress + parse last full state JSON (large object)
Stream query (delta): decompress + parse template once + scan deltas, tracking only q (no full materialization per tick)

We report raw/gzip sizes plus query agreement and a drift hash.
"""

import gzip
import hashlib
import json
from typing import Any, Dict, List, Tuple


def canon(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def gz(b: bytes) -> bytes:
    return gzip.compress(b, compresslevel=9)


def gz_len(b: bytes) -> int:
    return len(gz(b))


def sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def make_initial(n: int) -> List[int]:
    return [(i * 17 + 5) % 10007 for i in range(n)]


def step_edit(t: int, n: int) -> Tuple[int, int]:
    idx = (t * 1315423911) % n
    val = (t * 97 + 23) % 1000003
    return idx, val


def make_delta(t: int, m: int, n: int) -> Dict[str, Any]:
    edits = []
    for j in range(m):
        idx, val = step_edit(t * 1000 + j, n)
        edits.append({"i": idx, "v": val})
    return {"op": "delta", "t": t, "edits": edits}


def apply_delta(state: List[int], d: Dict[str, Any]) -> None:
    for e in d["edits"]:
        state[e["i"]] = e["v"]


def query_from_snapshot_gz(gz_bytes: bytes, q: int) -> int:
    # NDJSON: last line is last full state
    data = gzip.decompress(gz_bytes)
    last = data.splitlines()[-1]
    obj = json.loads(last)
    return obj["agents"][q]


def query_from_delta_gz(gz_bytes: bytes, q: int) -> int:
    # NDJSON: first line is template state0; remaining are deltas
    data = gzip.decompress(gz_bytes)
    lines = data.splitlines()
    st0 = json.loads(lines[0])
    acc = st0["agents"][q]
    for ln in lines[1:]:
        d = json.loads(ln)
        for e in d["edits"]:
            if e["i"] == q:
                acc = e["v"]
    return acc


def main() -> None:
    # Locked params
    n_agents = 4096
    k_updates = 1024
    m_edits = 1
    seed = 28028  # informational

    # Build streams
    state = make_initial(n_agents)

    snap_lines: List[bytes] = []
    delta_lines: List[bytes] = []

    # template line
    delta_lines.append(canon({"op": "state0", "agents": state}))

    # snapshot line t=0
    snap_lines.append(canon({"op": "state", "t": 0, "agents": state}))

    for t in range(1, k_updates + 1):
        d = make_delta(t, m_edits, n_agents)
        delta_lines.append(canon(d))
        apply_delta(state, d)
        snap_lines.append(canon({"op": "state", "t": t, "agents": state}))

    snap_stream = b"\n".join(snap_lines) + b"\n"
    delta_stream = b"\n".join(delta_lines) + b"\n"

    snap_gz = gz(snap_stream)
    delta_gz = gz(delta_stream)

    # Query a few fixed indices
    qs = [0, 1, 17, 999, 2048, 4095]
    ok = True
    for q in qs:
        a = query_from_snapshot_gz(snap_gz, q)
        b = query_from_delta_gz(delta_gz, q)
        if a != b:
            ok = False
            break

    drift = sha256_hex(snap_gz + b"|" + delta_gz)

    print("v28_projection_query_no_materialization")
    print(f"seed={seed}")
    print(f"n_agents={n_agents} k_updates={k_updates} m_edits={m_edits}")
    print(f"raw_snapshot_stream={len(snap_stream)}")
    print(f"raw_delta_stream={len(delta_stream)}")
    print(f"raw_ratio(snapshot/delta)={(len(snap_stream)/len(delta_stream)):.6f}")
    print(f"gz_snapshot_stream={len(snap_gz)}")
    print(f"gz_delta_stream={len(delta_gz)}")
    print(f"gz_ratio(snapshot/delta)={(len(snap_gz)/len(delta_gz)):.6f}")
    print(f"queries_ok={ok}")
    print(f"query_indices={qs}")
    print(f"drift_sha256={drift}")


if __name__ == "__main__":
    main()