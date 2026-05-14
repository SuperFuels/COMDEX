#!/usr/bin/env python3
import gzip
import hashlib
import json
import random
from dataclasses import dataclass
from typing import List, Tuple

def jdump(obj) -> bytes:
    return (json.dumps(obj, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")

def sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

@dataclass
class Fenwick:
    n: int
    bit: List[int]

    @staticmethod
    def build(arr: List[int]) -> "Fenwick":
        n = len(arr)
        bit = [0] * (n + 1)
        fw = Fenwick(n=n, bit=bit)
        for i, v in enumerate(arr):
            fw.add(i, v)
        return fw

    def add(self, idx0: int, delta: int) -> None:
        i = idx0 + 1
        n = self.n
        bit = self.bit
        while i <= n:
            bit[i] += delta
            i += i & -i

    def prefix_sum(self, r0: int) -> int:
        # sum arr[0..r0]
        i = r0 + 1
        s = 0
        bit = self.bit
        while i > 0:
            s += bit[i]
            i -= i & -i
        return s

    def range_sum(self, l0: int, r0: int) -> int:
        if l0 == 0:
            return self.prefix_sum(r0)
        return self.prefix_sum(r0) - self.prefix_sum(l0 - 1)

def main() -> None:
    name = "v39_range_prefix_index_no_materialization"
    seed = 39039
    n_agents = 4096
    k_updates = 1024
    m_edits_per_update = 1

    rng = random.Random(seed)

    # initial state
    state0 = [rng.randrange(0, 1000) for _ in range(n_agents)]
    state = state0[:]  # baseline mutable

    # Build Fenwick index over initial state
    fw = Fenwick.build(state0)

    deltas: List[Tuple[int, int, int]] = []
    for _ in range(k_updates):
        idx = rng.randrange(0, n_agents)
        old = state[idx]
        # bounded step to keep values stable-ish
        step = rng.randrange(-9, 10)
        if step == 0:
            step = 1
        new = old + step
        # record delta (idx, old, new)
        deltas.append((idx, old, new))
        # apply to baseline state
        state[idx] = new
        # apply to Fenwick as (new-old)
        fw.add(idx, new - old)

    # Validate Fenwick answers against materialized baseline
    q_rng = random.Random(seed + 1)
    prefix_queries = [q_rng.randrange(0, n_agents) for _ in range(128)]
    range_queries = [(q_rng.randrange(0, n_agents), q_rng.randrange(0, n_agents)) for _ in range(128)]
    range_queries = [(min(a, b), max(a, b)) for (a, b) in range_queries]

    prefix_ok = True
    for r in prefix_queries:
        got = fw.prefix_sum(r)
        exp = sum(state[: r + 1])
        if got != exp:
            prefix_ok = False
            break

    range_ok = True
    for l, r in range_queries:
        got = fw.range_sum(l, r)
        exp = sum(state[l : r + 1])
        if got != exp:
            range_ok = False
            break

    fenwick_ok = prefix_ok and range_ok

    # Build snapshot stream: full state each tick (incl. initial)
    snap_bytes = bytearray()
    tmp_state = state0[:]
    snap_bytes += (json.dumps(tmp_state, separators=(",", ":")) + "\n").encode("utf-8")
    for (idx, old, new) in deltas:
        tmp_state[idx] = new
        snap_bytes += (json.dumps(tmp_state, separators=(",", ":")) + "\n").encode("utf-8")

    # Build delta stream: template once + deltas
    delta_bytes = bytearray()
    delta_bytes += (json.dumps(state0, separators=(",", ":")) + "\n").encode("utf-8")
    for (idx, old, new) in deltas:
        delta_bytes += (json.dumps({"i": idx, "o": old, "n": new}, separators=(",", ":")) + "\n").encode("utf-8")

    raw_snapshot_stream = len(snap_bytes)
    raw_delta_stream = len(delta_bytes)
    raw_ratio = (raw_snapshot_stream / raw_delta_stream) if raw_delta_stream else float("inf")

    gz_snapshot = gzip.compress(bytes(snap_bytes), compresslevel=9)
    gz_delta = gzip.compress(bytes(delta_bytes), compresslevel=9)
    gz_snapshot_stream = len(gz_snapshot)
    gz_delta_stream = len(gz_delta)
    gz_ratio = (gz_snapshot_stream / gz_delta_stream) if gz_delta_stream else float("inf")

    final_state_sha256 = sha256_hex((json.dumps(state, separators=(",", ":"))).encode("utf-8"))

    receipt = {
        "name": name,
        "seed": seed,
        "n_agents": n_agents,
        "k_updates": k_updates,
        "m_edits_per_update": m_edits_per_update,
        "fenwick_ok": fenwick_ok,
        "prefix_queries_ok": prefix_ok,
        "range_queries_ok": range_ok,
        "raw_snapshot_stream": raw_snapshot_stream,
        "raw_delta_stream": raw_delta_stream,
        "raw_ratio(snapshot/delta)": raw_ratio,
        "gz_snapshot_stream": gz_snapshot_stream,
        "gz_delta_stream": gz_delta_stream,
        "gz_ratio(snapshot/delta)": gz_ratio,
        "final_state_sha256": final_state_sha256,
        # include a small deterministic sample for drift anchoring
        "sample_prefix": [(r, fw.prefix_sum(r)) for r in prefix_queries[:10]],
        "sample_ranges": [((l, r), fw.range_sum(l, r)) for (l, r) in range_queries[:10]],
    }
    drift_sha256 = sha256_hex(json.dumps(receipt, sort_keys=True, separators=(",", ":")).encode("utf-8"))

    # Print in the same “receipt” style as prior bridges
    print(name)
    print(f"seed={seed}")
    print(f"n_agents={n_agents} k_updates={k_updates} m_edits_per_update={m_edits_per_update}")
    print(f"fenwick_ok={fenwick_ok}")
    print(f"prefix_queries_ok={prefix_ok}")
    print(f"range_queries_ok={range_ok}")
    print(f"raw_snapshot_stream={raw_snapshot_stream}")
    print(f"raw_delta_stream={raw_delta_stream}")
    print(f"raw_ratio(snapshot/delta)={raw_ratio:.6f}")
    print(f"gz_snapshot_stream={gz_snapshot_stream}")
    print(f"gz_delta_stream={gz_delta_stream}")
    print(f"gz_ratio(snapshot/delta)={gz_ratio:.6f}")
    print(f"final_state_sha256={final_state_sha256}")
    print(f"drift_sha256={drift_sha256}")

if __name__ == "__main__":
    main()
