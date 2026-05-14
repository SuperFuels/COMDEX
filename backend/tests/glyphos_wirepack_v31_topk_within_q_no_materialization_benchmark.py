#!/usr/bin/env python3
"""
v31 — Exact TOP-K within a query set Q from old/new deltas (no full materialization)

We track only indices in Q while scanning deltas (idx, old, new), then compute exact TOP-K
over the tracked values. Compare to baseline TOP-K computed from final snapshot.

Locks:
- raw/gzip stream sizes
- correctness across multiple Q sizes and K values
- drift_sha256 over gz bytes + query receipts
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


def make_query_indices(n: int, k: int) -> List[int]:
    out = []
    x = 1
    while len(out) < k:
        x = (x * 1103515245 + 12345) & 0x7FFFFFFF
        out.append(x % n)
    return sorted(set(out))  # set-like


def topk_vals(vals: List[int], K: int) -> List[int]:
    return sorted(vals, reverse=True)[:K]


def topk_snapshot_last(gz_bytes: bytes, Q: List[int], K: int) -> List[int]:
    data = gzip.decompress(gz_bytes)
    last = data.splitlines()[-1]
    obj = json.loads(last)
    agents = obj["agents"]
    return topk_vals([agents[i] for i in Q], K)


def topk_delta_stream(gz_bytes: bytes, Q: List[int], K: int) -> List[int]:
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
                acc[ii] = e["new"]

    return topk_vals(list(acc.values()), K)


def main() -> None:
    seed = 31031  # informational
    n_agents = 4096
    k_updates = 1024

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

    Qsizes = [1, 8, 64, 512]
    Ks = [1, 5, 10]
    results = []
    all_ok = True

    for qk in Qsizes:
        Q = make_query_indices(n_agents, qk)
        for K in Ks:
            a = topk_snapshot_last(snap_gz, Q, K)
            b = topk_delta_stream(delta_gz, Q, K)
            ok = (a == b)
            results.append({"qk": qk, "qsize": len(Q), "K": K, "ok": ok, "first10": Q[:10], "top": b[:5]})
            if not ok:
                all_ok = False

    drift_obj = {
        "snap_gz_sha": sha256_hex(snap_gz),
        "delta_gz_sha": sha256_hex(delta_gz),
        "results": results,
    }
    drift = sha256_hex(canon(drift_obj))

    print("v31_topk_within_q_no_materialization")
    print(f"seed={seed}")
    print(f"n_agents={n_agents} k_updates={k_updates}")
    print(f"raw_snapshot_stream={len(snap_stream)}")
    print(f"raw_delta_stream={len(delta_stream)}")
    print(f"raw_ratio(snapshot/delta)={(len(snap_stream)/len(delta_stream)):.6f}")
    print(f"gz_snapshot_stream={len(snap_gz)}")
    print(f"gz_delta_stream={len(delta_gz)}")
    print(f"gz_ratio(snapshot/delta)={(len(snap_gz)/len(delta_gz)):.6f}")
    print(f"all_topk_ok={all_ok}")
    for r in results:
        if r["K"] == 10:  # keep output compact
            print(f"qk={r['qk']} qsize={r['qsize']} K={r['K']} ok={r['ok']} first10={r['first10']} top5={r['top']}")
    print(f"drift_sha256={drift}")


if __name__ == "__main__":
    main()