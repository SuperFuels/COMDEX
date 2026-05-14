#!/usr/bin/env python3
"""
v36 — Cosine Similarity (Squared) from Delta Stream (No Materialization)

We simulate a high-cardinality evolving state vector x (n_agents).
Baseline stream: full JSON snapshot per update (huge).
Glyph-style stream: initial snapshot once + sparse deltas (small).

We maintain:
  dot = <x, w>
  norm_sq = ||x||^2
under point updates (i, old -> new), and verify equality against recomputation.

We report:
- raw/gzip sizes for snapshot-stream vs delta-stream
- cos^2 numerator/denominator (exact integers; avoids sqrt)
- drift sha256 for regression locks
"""

import gzip
import hashlib
import json
from typing import Any, Dict, List, Tuple


def canon_bytes(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def gz_len(b: bytes) -> int:
    return len(gzip.compress(b, compresslevel=9))


def make_initial_state(n: int) -> List[int]:
    return [(i * 7 + 3) % 97 for i in range(n)]


def make_weights(n: int) -> List[int]:
    # Deterministic weights (include negatives).
    # Keep small-ish magnitude so squares are safe in Python int anyway.
    out: List[int] = []
    for i in range(n):
        v = (i * 17 + 11) % 101  # 0..100
        out.append(v - 50)       # -50..50
    return out


def dot(x: List[int], w: List[int]) -> int:
    return sum(a * b for a, b in zip(x, w))


def norm_sq(x: List[int]) -> int:
    return sum(a * a for a in x)


def next_index(t: int, n: int, seed: int) -> int:
    # Deterministic pseudo-random-ish index
    return (seed + t * 131 + (t * t) * 17) % n


def next_value(old: int, t: int) -> int:
    # Deterministic new value
    return (old + 1 + (t % 23)) % 100000


def main() -> None:
    seed = 36036
    n_agents = 4096
    k_updates = 1024

    x = make_initial_state(n_agents)
    w = make_weights(n_agents)

    w_norm_sq = norm_sq(w)

    # Maintained aggregates
    dot_acc = dot(x, w)
    x_norm_sq_acc = norm_sq(x)

    # Streams
    snapshot_chunks: List[bytes] = []
    delta_chunks: List[bytes] = []

    # Initial snapshot once for delta stream (so the state is defined)
    init_rec = {"t": 0, "state": x}
    delta_chunks.append(canon_bytes(init_rec))

    # Snapshot stream uses a full snapshot each update (including t)
    snapshot_chunks.append(canon_bytes(init_rec))

    # Apply updates
    for t in range(1, k_updates + 1):
        i = next_index(t, n_agents, seed)
        old = x[i]
        new = next_value(old, t)

        # O(1) updates
        dot_acc += (new - old) * w[i]
        x_norm_sq_acc += (new * new) - (old * old)

        # Apply
        x[i] = new

        # Record streams
        snap = {"t": t, "state": x}
        dlt = {"t": t, "i": i, "old": old, "new": new}
        snapshot_chunks.append(canon_bytes(snap))
        delta_chunks.append(canon_bytes(dlt))

    # Verify against recomputation
    dot_final = dot(x, w)
    x_norm_sq_final = norm_sq(x)

    ok = (dot_acc == dot_final) and (x_norm_sq_acc == x_norm_sq_final)

    # Cosine^2 exact rational: (dot^2) / (||x||^2 * ||w||^2)
    cos2_num = dot_final * dot_final
    cos2_den = x_norm_sq_final * w_norm_sq

    snapshot_stream = b"".join(snapshot_chunks)
    delta_stream = b"".join(delta_chunks)

    raw_snapshot = len(snapshot_stream)
    raw_delta = len(delta_stream)
    gz_snapshot = gz_len(snapshot_stream)
    gz_delta = gz_len(delta_stream)

    drift_obj = {
        "seed": seed,
        "n_agents": n_agents,
        "k_updates": k_updates,
        "dot": dot_final,
        "x_norm_sq": x_norm_sq_final,
        "w_norm_sq": w_norm_sq,
        "cos2_num": cos2_num,
        "cos2_den": cos2_den,
        "state_tail16": x[-16:],
    }
    drift = sha256_hex(canon_bytes(drift_obj))

    print("v36_cosine_similarity_no_materialization")
    print(f"seed={seed}")
    print(f"n_agents={n_agents} k_updates={k_updates}")
    print(f"raw_snapshot_stream={raw_snapshot}")
    print(f"raw_delta_stream={raw_delta}")
    print(f"raw_ratio(snapshot/delta)={(raw_snapshot / raw_delta):.6f}")
    print(f"gz_snapshot_stream={gz_snapshot}")
    print(f"gz_delta_stream={gz_delta}")
    print(f"gz_ratio(snapshot/delta)={(gz_snapshot / gz_delta):.6f}")
    print(f"cos2_ok={ok}")
    print(f"cos2_num={cos2_num}")
    print(f"cos2_den={cos2_den}")
    print(f"drift_sha256={drift}")


if __name__ == "__main__":
    main()