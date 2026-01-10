#!/usr/bin/env python3
"""
v32 — Heavy hitters (exact TOP-K) from delta stream (no full materialization)

We compare:
1) Snapshot stream: full state each tick (naive).
2) Delta stream: state0 + sparse edits (idx, old, new).

Query:
- Exact global TOP-K values at final time.
- Baseline: parse last snapshot.
- Delta method: track only touched indices while scanning deltas; final value(i) = touched[i] else state0[i].
  Then compute topK over all n.

Locks:
- raw/gzip sizes and ratios
- topK correctness
- drift sha over gz bytes + topK receipt
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
    new = (t * 97 + 23) % 1000003
    return idx, new


def make_delta_with_old(t: int, n: int, state: List[int]) -> Dict[str, Any]:
    idx, new = step_edit(t, n)
    old = state[idx]
    return {"op": "delta", "t": t, "edits": [{"i": idx, "old": old, "new": new}]}


def apply_delta(state: List[int], d: Dict[str, Any]) -> None:
    for e in d["edits"]:
        state[e["i"]] = e["new"]


def topk_vals(vals: List[int], K: int) -> List[int]:
    return sorted(vals, reverse=True)[:K]


def topk_from_snapshot_last(snap_gz: bytes, K: int) -> List[int]:
    data = gzip.decompress(snap_gz)
    last = data.splitlines()[-1]
    obj = json.loads(last)
    agents = obj["agents"]
    return topk_vals(agents, K)


def topk_from_delta_stream(delta_gz: bytes, K: int) -> List[int]:
    data = gzip.decompress(delta_gz)
    lines = data.splitlines()
    st0 = json.loads(lines[0])
    agents0 = st0["agents"]

    touched: Dict[int, int] = {}
    for ln in lines[1:]:
        d = json.loads(ln)
        for e in d["edits"]:
            touched[e["i"]] = e["new"]

    # reconstruct final values without materializing intermediate snapshots
    final_vals = [touched.get(i, agents0[i]) for i in range(len(agents0))]
    return topk_vals(final_vals, K)


def main() -> None:
    seed = 32032  # informational
    n_agents = 4096
    k_updates = 1024
    K = 10

    state = make_initial(n_agents)

    snap_lines: List[bytes] = []
    delta_lines: List[bytes] = []

    delta_lines.append(canon({"op": "state0", "agents": state}))
    snap_lines.append(canon({"op": "state", "t": 0, "agents": state}))

    for t in range(1, k_updates + 1):
        d = make_delta_with_old(t, n_agents, state)
        delta_lines.append(canon(d))
        apply_delta(state, d)
        snap_lines.append(canon({"op": "state", "t": t, "agents": state}))

    snap_stream = b"\n".join(snap_lines) + b"\n"
    delta_stream = b"\n".join(delta_lines) + b"\n"

    snap_gz = gz(snap_stream)
    delta_gz = gz(delta_stream)

    top_snap = topk_from_snapshot_last(snap_gz, K)
    top_delta = topk_from_delta_stream(delta_gz, K)
    ok = (top_snap == top_delta)

    drift_obj = {
        "snap_gz_sha": sha256_hex(snap_gz),
        "delta_gz_sha": sha256_hex(delta_gz),
        "K": K,
        "top": top_delta,
        "ok": ok,
    }
    drift = sha256_hex(canon(drift_obj))

    print("v32_heavy_hitters_no_materialization")
    print(f"seed={seed}")
    print(f"n_agents={n_agents} k_updates={k_updates} K={K}")
    print(f"raw_snapshot_stream={len(snap_stream)}")
    print(f"raw_delta_stream={len(delta_stream)}")
    print(f"raw_ratio(snapshot/delta)={(len(snap_stream)/len(delta_stream)):.6f}")
    print(f"gz_snapshot_stream={len(snap_gz)}")
    print(f"gz_delta_stream={len(delta_gz)}")
    print(f"gz_ratio(snapshot/delta)={(len(snap_gz)/len(delta_gz)):.6f}")
    print(f"topk_ok={ok}")
    print(f"topk_values={top_delta}")
    print(f"drift_sha256={drift}")


if __name__ == "__main__":
    main()