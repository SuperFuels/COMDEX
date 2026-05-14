#!/usr/bin/env python3
"""
v38 — Canonical Delta determinism + replay correctness (locked)

This benchmark is a *receipt generator*:
- determinism: canon(delta) is stable across repeated canonicalization
- replay correctness: applying deltas to a base state yields the same final state
  regardless of (a) redundant canon passes and (b) equivalent op-order before canon
- drift_sha256: stable hash over the printed receipt fields to lock regressions

Design constraints:
- Pure Python, deterministic by seed.
- No dependency on the rest of the system: safe to run in CI.
"""

from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass
from typing import List, Tuple

SEED = 38038
N_AGENTS = 4096
K_UPDATES = 1024
M_EDITS_PER_UPDATE = 1

# ---------------------------
# Delta model (minimal)
# ---------------------------
Op = Tuple[int, int]  # (idx, new_value)

@dataclass(frozen=True)
class Delta:
    ops: Tuple[Op, ...]

def canon_delta(d: Delta) -> Delta:
    # canonical order: (idx asc, value asc)
    ops = tuple(sorted(d.ops, key=lambda t: (t[0], t[1])))
    return Delta(ops=ops)

def apply_delta(state: List[int], d: Delta) -> None:
    for idx, newv in d.ops:
        state[idx] = newv

def sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def stable_json(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")

def main() -> None:
    rng = random.Random(SEED)

    # Base state: deterministic pseudo-random ints
    base = [rng.randrange(0, 100_000) for _ in range(N_AGENTS)]

    # We'll create two logically-equivalent streams:
    # - stream A: deltas emitted in canonical order already
    # - stream B: same deltas but ops may be shuffled before canon; canon should normalize
    deltas_a: List[Delta] = []
    deltas_b: List[Delta] = []

    # For replay check we keep copies
    state_a = base.copy()
    state_b = base.copy()

    # Determinism checks
    canon_idempotent_ok = True
    canon_stable_ok = True

    # We will also hash the whole receipt deterministically.
    receipt_rows = []

    for t in range(K_UPDATES):
        # pick indices; for M=1 it's just one index
        ops: List[Op] = []
        for _ in range(M_EDITS_PER_UPDATE):
            idx = rng.randrange(0, N_AGENTS)
            newv = rng.randrange(0, 100_000)
            ops.append((idx, newv))

        d_raw = Delta(ops=tuple(ops))
        d_a = canon_delta(d_raw)

        # For B, we shuffle ops before canon (noop when M=1, but keeps harness general)
        ops_b = list(ops)
        rng.shuffle(ops_b)
        d_b = canon_delta(Delta(ops=tuple(ops_b)))

        # Canon determinism properties
        d_a2 = canon_delta(d_a)
        if d_a2 != d_a:
            canon_idempotent_ok = False

        # Stability against input op order (after canon)
        if d_b != d_a:
            canon_stable_ok = False

        # Apply deltas
        apply_delta(state_a, d_a)
        apply_delta(state_b, d_b)

        # Collect a compact receipt row for drift hashing
        receipt_rows.append({
            "t": t,
            "ops": list(d_a.ops),  # canonical ops
        })

        deltas_a.append(d_a)
        deltas_b.append(d_b)

    replay_ok = (state_a == state_b)

    # Serialize "template" (base state) and "delta stream" in a stable way for byte counts.
    # This is not WirePack; it’s a deterministic receipt that matches your existing v27+ style.
    template_bytes = stable_json({"base": base})
    delta_stream_bytes = stable_json({"deltas": receipt_rows})

    raw_template = len(template_bytes)
    raw_deltas = len(delta_stream_bytes)

    # gzip sizes (level 9)
    import gzip
    gz_template = len(gzip.compress(template_bytes, compresslevel=9))
    gz_deltas = len(gzip.compress(delta_stream_bytes, compresslevel=9))

    # Drift hash over the key printed fields (stable JSON)
    drift_payload = stable_json({
        "seed": SEED,
        "n_agents": N_AGENTS,
        "k_updates": K_UPDATES,
        "m_edits_per_update": M_EDITS_PER_UPDATE,
        "canon_idempotent_ok": canon_idempotent_ok,
        "canon_stable_ok": canon_stable_ok,
        "replay_ok": replay_ok,
        "final_state_sha256": sha256_hex(stable_json({"final": state_a})),
        "template_sha256": sha256_hex(template_bytes),
        "deltas_sha256": sha256_hex(delta_stream_bytes),
        "raw_template": raw_template,
        "raw_deltas": raw_deltas,
        "gz_template": gz_template,
        "gz_deltas": gz_deltas,
    })
    drift_sha256 = sha256_hex(drift_payload)

    # Print in the same key=value style your lock parsers like.
    print("v38_canonical_delta_determinism_replay")
    print(f"seed={SEED}")
    print(f"n_agents={N_AGENTS} k_updates={K_UPDATES} m_edits_per_update={M_EDITS_PER_UPDATE}")
    print(f"canon_idempotent_ok={canon_idempotent_ok}")
    print(f"canon_stable_ok={canon_stable_ok}")
    print(f"replay_ok={replay_ok}")
    print(f"raw_template_bytes={raw_template}")
    print(f"raw_delta_stream_bytes={raw_deltas}")
    # keep the ratio naming consistent with your other benches where possible
    if raw_deltas > 0:
        print(f"raw_ratio(template/delta)={raw_template / raw_deltas:.6f}")
    print(f"gz_template_bytes={gz_template}")
    print(f"gz_delta_stream_bytes={gz_deltas}")
    if gz_deltas > 0:
        print(f"gz_ratio(template/delta)={gz_template / gz_deltas:.6f}")
    print(f"final_state_sha256={sha256_hex(stable_json({'final': state_a}))}")
    print(f"drift_sha256={drift_sha256}")

    # Hard fail if correctness broken (so CI catches immediately)
    assert canon_idempotent_ok, "canon must be idempotent"
    assert canon_stable_ok, "canon must erase op-order nondeterminism"
    assert replay_ok, "replay must match across equivalent canonical deltas"

if __name__ == "__main__":
    main()
