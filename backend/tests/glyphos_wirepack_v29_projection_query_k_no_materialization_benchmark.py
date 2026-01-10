#!/usr/bin/env python3
"""
v29 — k-Projection Query Without Full Materialization

Same stream as v28 (snapshot NDJSON vs template+delta NDJSON), but query a SET of indices Q
of size k (k in {1, 8, 64, 512}) without rebuilding full state.

We verify exact agreement against snapshot-last-state values.
We report raw/gzip sizes (stream-level), plus query correctness for each k, plus drift hash.
"""

import gzip
import hashlib
import json
from typing import Any, Dict, List, Tuple


def canon(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def gz(b: bytes) -> bytes:
    return gzip.compress(b, compresslevel=9)


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


def query_snapshot_last(gz_bytes: bytes, Q: List[int]) -> Dict[int, int]:
    data = gzip.decompress(gz_bytes)
    last = data.splitlines()[-1]
    obj = json.loads(last)
    agents = obj["agents"]
    return {i: agents[i] for i in Q}


def query_delta_stream(gz_bytes: bytes, Q: List[int]) -> Dict[int, int]:
    data = gzip.decompress(gz_bytes)
    lines = data.splitlines()
    st0 = json.loads(lines[0])
    agents0 = st0["agents"]

    qset = set(Q)
    acc = {i: agents0[i] for i in Q}

    for ln in lines[1:]:
        d = json.loads(ln)
        for e in d["edits"]:
            ii = e["i"]
            if ii in qset:
                acc[ii] = e["v"]

    return acc


def make_query_indices(n: int, k: int) -> List[int]:
    # Deterministic spread: take first k of a simple permutation
    out = []
    x = 1
    while len(out) < k:
        x = (x * 1103515245 + 12345) & 0x7FFFFFFF
        out.append(x % n)
    # stable ordering for printing / drift
    return sorted(out)


def main() -> None:
    seed = 29029  # informational
    n_agents = 4096
    k_updates = 1024
    m_edits = 1

    state = make_initial(n_agents)

    snap_lines: List[bytes] = []
    delta_lines: List[bytes] = []

    delta_lines.append(canon({"op": "state0", "agents": state}))
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

    ks = [1, 8, 64, 512]
    results = []

    all_ok = True
    for k in ks:
        Q = make_query_indices(n_agents, k)
        a = query_snapshot_last(snap_gz, Q)
        b = query_delta_stream(delta_gz, Q)
        ok = (a == b)
        results.append({"k": k, "ok": ok, "first10": Q[:10]})
        if not ok:
            all_ok = False

    drift_obj = {
        "snap_gz_sha": sha256_hex(snap_gz),
        "delta_gz_sha": sha256_hex(delta_gz),
        "results": results,
    }
    drift = sha256_hex(canon(drift_obj))

    print("v29_projection_query_k_no_materialization")
    print(f"seed={seed}")
    print(f"n_agents={n_agents} k_updates={k_updates} m_edits={m_edits}")
    print(f"raw_snapshot_stream={len(snap_stream)}")
    print(f"raw_delta_stream={len(delta_stream)}")
    print(f"raw_ratio(snapshot/delta)={(len(snap_stream)/len(delta_stream)):.6f}")
    print(f"gz_snapshot_stream={len(snap_gz)}")
    print(f"gz_delta_stream={len(delta_gz)}")
    print(f"gz_ratio(snapshot/delta)={(len(snap_gz)/len(delta_gz)):.6f}")
    print(f"all_k_queries_ok={all_ok}")
    for r in results:
        print(f"k={r['k']} ok={r['ok']} first10={r['first10']}")
    print(f"drift_sha256={drift}")


if __name__ == "__main__":
    main()