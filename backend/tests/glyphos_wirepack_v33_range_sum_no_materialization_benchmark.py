#!/usr/bin/env python3
"""
v33 — Range/window sums from delta stream (no full materialization)

We reuse the same synthetic stream family as v30/v31/v32:
- state0 once
- sparse edits (idx, old, new) for k_updates ticks

Queries:
- exact sum over windows [L,R] at final time, for several windows
- baseline: parse final snapshot and sum slice
- delta method: scan deltas into touched map; sum = sum(state0[L:R]) + sum(delta_updates_in_range)

Locks:
- raw/gzip sizes and ratios
- all window sums ok
- drift sha over gz bytes + query receipts
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


def sum_window(vals: List[int], L: int, R: int) -> int:
    return sum(vals[L:R + 1])


def window_sum_from_snapshot_last(snap_gz: bytes, windows: List[Tuple[int, int]]) -> List[int]:
    data = gzip.decompress(snap_gz)
    last = data.splitlines()[-1]
    obj = json.loads(last)
    agents = obj["agents"]
    return [sum_window(agents, L, R) for (L, R) in windows]


def window_sum_from_delta_stream(delta_gz: bytes, windows: List[Tuple[int, int]]) -> List[int]:
    data = gzip.decompress(delta_gz)
    lines = data.splitlines()
    st0 = json.loads(lines[0])
    agents0 = st0["agents"]

    # precompute baseline sums for each window from state0
    base = [sum_window(agents0, L, R) for (L, R) in windows]

    # touched: idx -> new
    touched: Dict[int, int] = {}

    # incremental correction: for each touched idx in a window, adjust by (new - old0)
    corr = [0 for _ in windows]

    for ln in lines[1:]:
        d = json.loads(ln)
        for e in d["edits"]:
            i = e["i"]
            new = e["new"]
            old_final = touched.get(i, agents0[i])  # previous final value at i
            touched[i] = new
            delta = new - old_final
            # apply delta to any window containing i
            for wi, (L, R) in enumerate(windows):
                if L <= i <= R:
                    corr[wi] += delta

    return [base[wi] + corr[wi] for wi in range(len(windows))]


def main() -> None:
    seed = 33033  # informational
    n_agents = 4096
    k_updates = 1024

    # deterministic windows (cover small + medium + large)
    windows = [
        (0, 0),
        (0, 31),
        (64, 127),
        (1000, 1100),
        (2048, 3071),
        (3500, 4095),
    ]

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

    w_snap = window_sum_from_snapshot_last(snap_gz, windows)
    w_delta = window_sum_from_delta_stream(delta_gz, windows)
    ok = (w_snap == w_delta)

    drift_obj = {
        "snap_gz_sha": sha256_hex(snap_gz),
        "delta_gz_sha": sha256_hex(delta_gz),
        "windows": windows,
        "sums": w_delta,
        "ok": ok,
    }
    drift = sha256_hex(canon(drift_obj))

    print("v33_range_sum_no_materialization")
    print(f"seed={seed}")
    print(f"n_agents={n_agents} k_updates={k_updates}")
    print(f"windows={windows}")
    print(f"raw_snapshot_stream={len(snap_stream)}")
    print(f"raw_delta_stream={len(delta_stream)}")
    print(f"raw_ratio(snapshot/delta)={(len(snap_stream)/len(delta_stream)):.6f}")
    print(f"gz_snapshot_stream={len(snap_gz)}")
    print(f"gz_delta_stream={len(delta_gz)}")
    print(f"gz_ratio(snapshot/delta)={(len(snap_gz)/len(delta_gz)):.6f}")
    print(f"window_sums_ok={ok}")
    print(f"window_sums={w_delta}")
    print(f"drift_sha256={drift}")


if __name__ == "__main__":
    main()