#!/usr/bin/env python3
"""
v27 — State-Space Scaling Law (Sparse High-Cardinality Telemetry)

Compare:
  A) Snapshot stream: (k+1) full states (initial + k updates)
  B) Template+Delta stream: initial state once + k sparse deltas (m edits/tick)

We emit canonical JSON bytes (sort_keys + tight separators) and measure raw + gzip.
"""

import gzip
import hashlib
import json
from typing import Any, Dict, List, Tuple


def canon_bytes(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def gz_len(b: bytes) -> int:
    return len(gzip.compress(b, compresslevel=9))


def sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def make_initial_state(n_agents: int) -> List[int]:
    # Deterministic, dense initial state
    return [(i * 17 + 5) % 10007 for i in range(n_agents)]


def step_edit(t: int, n_agents: int) -> Tuple[int, int]:
    # Deterministic "sparse change": one agent changes each tick
    idx = (t * 1315423911) % n_agents
    val = (t * 97 + 23) % 1000003
    return idx, val


def make_delta(t: int, m: int, n_agents: int) -> Dict[str, Any]:
    edits = []
    for j in range(m):
        idx, val = step_edit(t * 1000 + j, n_agents)
        edits.append({"i": idx, "v": val})
    return {"op": "delta", "t": t, "edits": edits}


def apply_delta(state: List[int], delta: Dict[str, Any]) -> None:
    for e in delta["edits"]:
        state[e["i"]] = e["v"]


def main() -> None:
    # Locked params (edit once, then lock)
    n_agents = 4096
    k_updates = 1024
    m_edits = 1
    seed = 27027  # informational (generator is deterministic)

    state = make_initial_state(n_agents)

    # Build snapshot stream (k+1 full states)
    snap_blobs: List[bytes] = []
    snap_blobs.append(canon_bytes({"op": "state", "t": 0, "agents": state}))

    # Build delta stream: initial state once + k deltas
    init_blob = canon_bytes({"op": "state0", "agents": state})
    delta_blobs: List[bytes] = []

    for t in range(1, k_updates + 1):
        d = make_delta(t, m_edits, n_agents)
        d_b = canon_bytes(d)
        delta_blobs.append(d_b)

        apply_delta(state, d)
        snap_blobs.append(canon_bytes({"op": "state", "t": t, "agents": state}))

    snap_stream = b"".join(snap_blobs)
    delta_stream = init_blob + b"".join(delta_blobs)

    raw_snap = len(snap_stream)
    raw_delta = len(delta_stream)
    gz_snap = gz_len(snap_stream)
    gz_delta = gz_len(delta_stream)

    drift = sha256_hex(delta_stream + b"|" + snap_stream)

    print("v27_state_space_sparse_update")
    print(f"seed={seed}")
    print(f"n_agents={n_agents} k_updates={k_updates} m_edits={m_edits}")
    print(f"raw_snapshot_stream={raw_snap}")
    print(f"raw_delta_stream={raw_delta}")
    print(f"raw_ratio(snapshot/delta)={(raw_snap / raw_delta):.6f}")
    print(f"gz_snapshot_stream={gz_snap}")
    print(f"gz_delta_stream={gz_delta}")
    print(f"gz_ratio(snapshot/delta)={(gz_snap / gz_delta):.6f}")
    print(f"drift_sha256={drift}")


if __name__ == "__main__":
    main()