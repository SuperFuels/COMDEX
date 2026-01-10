#!/usr/bin/env python3
"""
v30 — Exact aggregate from old/new deltas (no full materialization)

We maintain SUM over a query set Q while scanning deltas that carry (idx, old, new).
We prove by test: streamSum(Q) == sum(snapshot_last[Q]) for multiple Q sizes,
without materializing the full n-agent state during the delta query.

We also report stream sizes (raw + gzip) and lock with drift_sha256.
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
    return sorted(set(out))  # make it a true set for clean semantics


def sum_snapshot_last(gz_bytes: bytes, Q: List[int]) -> int:
    data = gzip.decompress(gz_bytes)
    last = data.splitlines()[-1]
    obj = json.loads(last)
    agents = obj["agents"]
    return sum(agents[i] for i in Q)


def sum_delta_stream(gz_bytes: bytes, Q: List[int]) -> int:
    data = gzip.decompress(gz_bytes)
    lines = data.splitlines()
    st0 = json.loads(lines[0])
    agents0 = st0["agents"]

    qset = set(Q)
    acc = {i: agents0[i] for i in Q}
    s = sum(acc.values())

    for ln in lines[1:]:
        d = json.loads(ln)
        for e in d["edits"]:
            ii = e["i"]
            if ii in qset:
                old = e["old"]
                new = e["new"]
                # exact aggregate update:
                s += (new - old)
                acc[ii] = new

    # sanity: sum(acc) equals s (detect logic bugs)
    if s != sum(acc.values()):
        raise AssertionError("aggregate drift: s != sum(acc)")
    return s


def main() -> None:
    seed = 30030  # informational
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

    ks = [1, 8, 64, 512]
    results = []
    all_ok = True

    for k in ks:
        Q = make_query_indices(n_agents, k)
        a = sum_snapshot_last(snap_gz, Q)
        b = sum_delta_stream(delta_gz, Q)
        ok = (a == b)
        results.append({"k": k, "qsize": len(Q), "ok": ok, "first10": Q[:10]})
        if not ok:
            all_ok = False

    drift_obj = {
        "snap_gz_sha": sha256_hex(snap_gz),
        "delta_gz_sha": sha256_hex(delta_gz),
        "results": results,
    }
    drift = sha256_hex(canon(drift_obj))

    print("v30_delta_aggregate_no_materialization")
    print(f"seed={seed}")
    print(f"n_agents={n_agents} k_updates={k_updates}")
    print(f"raw_snapshot_stream={len(snap_stream)}")
    print(f"raw_delta_stream={len(delta_stream)}")
    print(f"raw_ratio(snapshot/delta)={(len(snap_stream)/len(delta_stream)):.6f}")
    print(f"gz_snapshot_stream={len(snap_gz)}")
    print(f"gz_delta_stream={len(delta_gz)}")
    print(f"gz_ratio(snapshot/delta)={(len(snap_gz)/len(delta_gz)):.6f}")
    print(f"all_k_sums_ok={all_ok}")
    for r in results:
        print(f"k={r['k']} qsize={r['qsize']} ok={r['ok']} first10={r['first10']}")
    print(f"drift_sha256={drift}")


if __name__ == "__main__":
    main()