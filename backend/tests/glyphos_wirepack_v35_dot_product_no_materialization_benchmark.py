#!/usr/bin/env python3
"""
v35 — Exact dot-product / correlation from delta stream (no materialization)

Compute dot(state_T, weights) exactly by only updating touched indices:
dot += (new-old) * w[i]

Compare:
- snapshot stream vs delta stream size (raw + gzip)
- correctness: dot_ok
- drift sha256 lock
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


def make_weights(n: int) -> List[int]:
    # deterministic weights; mix signs to look like correlations/scores
    return [((i * 131 + 7) % 2001) - 1000 for i in range(n)]


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


def dot(a: List[int], w: List[int]) -> int:
    return sum(x * wi for x, wi in zip(a, w))


def dot_from_snapshot_last(snap_gz: bytes, w: List[int]) -> int:
    data = gzip.decompress(snap_gz)
    last = data.splitlines()[-1]
    obj = json.loads(last)
    return dot(obj["agents"], w)


def dot_from_delta_stream(delta_gz: bytes, w: List[int]) -> int:
    data = gzip.decompress(delta_gz)
    lines = data.splitlines()
    st0 = json.loads(lines[0])
    agents0 = st0["agents"]

    d = dot(agents0, w)
    touched: Dict[int, int] = {}

    for ln in lines[1:]:
        obj = json.loads(ln)
        for e in obj["edits"]:
            i = e["i"]
            new = e["new"]
            old_final = touched.get(i, agents0[i])
            d += (new - old_final) * w[i]
            touched[i] = new

    return d


def main() -> None:
    seed = 35035  # informational
    n_agents = 4096
    k_updates = 1024

    state = make_initial(n_agents)
    weights = make_weights(n_agents)

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

    d_snap = dot_from_snapshot_last(snap_gz, weights)
    d_delta = dot_from_delta_stream(delta_gz, weights)
    ok = (d_snap == d_delta)

    drift_obj = {
        "snap_gz_sha": sha256_hex(snap_gz),
        "delta_gz_sha": sha256_hex(delta_gz),
        "dot": d_delta,
        "ok": ok,
    }
    drift = sha256_hex(canon(drift_obj))

    print("v35_dot_product_no_materialization")
    print(f"seed={seed}")
    print(f"n_agents={n_agents} k_updates={k_updates}")
    print(f"raw_snapshot_stream={len(snap_stream)}")
    print(f"raw_delta_stream={len(delta_stream)}")
    print(f"raw_ratio(snapshot/delta)={(len(snap_stream)/len(delta_stream)):.6f}")
    print(f"gz_snapshot_stream={len(snap_gz)}")
    print(f"gz_delta_stream={len(delta_gz)}")
    print(f"gz_ratio(snapshot/delta)={(len(snap_gz)/len(delta_gz)):.6f}")
    print(f"dot_ok={ok}")
    print(f"dot_value={d_delta}")
    print(f"drift_sha256={drift}")


if __name__ == "__main__":
    main()