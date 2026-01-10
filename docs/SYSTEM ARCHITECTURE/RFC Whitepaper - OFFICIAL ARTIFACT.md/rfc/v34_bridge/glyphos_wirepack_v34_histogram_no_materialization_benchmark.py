#!/usr/bin/env python3
"""
v34 — Exact histogram / group-by from delta stream (no full materialization)

Workload:
- n_agents=4096, k_updates=1024
- state0 + sparse deltas with (idx, old, new)
- baseline: parse last snapshot, compute histogram
- delta: track touched map and update histogram using only changed indices

Bucket:
- bucket = value % M  (M=256), so histogram has 256 bins.

Outputs:
- raw/gzip sizes and ratios (snapshot vs delta)
- histogram_ok
- drift sha256 for lock
"""

import gzip
import hashlib
import json
from typing import Any, Dict, List


def canon(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def gz(b: bytes) -> bytes:
    return gzip.compress(b, compresslevel=9)


def sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def make_initial(n: int) -> List[int]:
    return [(i * 17 + 5) % 10007 for i in range(n)]


def step_edit(t: int, n: int) -> (int, int):
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


def hist(values: List[int], M: int) -> List[int]:
    out = [0] * M
    for v in values:
        out[v % M] += 1
    return out


def hist_from_snapshot_last(snap_gz: bytes, M: int) -> List[int]:
    data = gzip.decompress(snap_gz)
    last = data.splitlines()[-1]
    obj = json.loads(last)
    return hist(obj["agents"], M)


def hist_from_delta_stream(delta_gz: bytes, M: int) -> List[int]:
    data = gzip.decompress(delta_gz)
    lines = data.splitlines()
    st0 = json.loads(lines[0])
    agents0 = st0["agents"]

    # start with histogram of state0
    h = hist(agents0, M)

    # touched final values
    touched: Dict[int, int] = {}

    for ln in lines[1:]:
        d = json.loads(ln)
        for e in d["edits"]:
            i = e["i"]
            new = e["new"]
            old_final = touched.get(i, agents0[i])

            # decrement old bucket, increment new bucket
            h[old_final % M] -= 1
            h[new % M] += 1

            touched[i] = new

    return h


def main() -> None:
    seed = 34034  # informational
    n_agents = 4096
    k_updates = 1024
    M = 256

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

    h_snap = hist_from_snapshot_last(snap_gz, M)
    h_delta = hist_from_delta_stream(delta_gz, M)
    ok = (h_snap == h_delta)

    drift_obj = {
        "snap_gz_sha": sha256_hex(snap_gz),
        "delta_gz_sha": sha256_hex(delta_gz),
        "M": M,
        "hist_head": h_delta[:16],
        "hist_tail": h_delta[-16:],
        "ok": ok,
    }
    drift = sha256_hex(canon(drift_obj))

    print("v34_histogram_no_materialization")
    print(f"seed={seed}")
    print(f"n_agents={n_agents} k_updates={k_updates} M={M}")
    print(f"raw_snapshot_stream={len(snap_stream)}")
    print(f"raw_delta_stream={len(delta_stream)}")
    print(f"raw_ratio(snapshot/delta)={(len(snap_stream)/len(delta_stream)):.6f}")
    print(f"gz_snapshot_stream={len(snap_gz)}")
    print(f"gz_delta_stream={len(delta_gz)}")
    print(f"gz_ratio(snapshot/delta)={(len(snap_gz)/len(delta_gz)):.6f}")
    print(f"histogram_ok={ok}")
    print(f"histogram_head16={h_delta[:16]}")
    print(f"histogram_tail16={h_delta[-16:]}")
    print(f"drift_sha256={drift}")


if __name__ == "__main__":
    main()