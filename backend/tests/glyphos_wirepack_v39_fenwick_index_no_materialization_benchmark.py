#!/usr/bin/env python3
"""
v39 (WirePack-backed) — Fenwick (BIT) index over delta stream (no materialization)

What this does:
- Maintains a Fenwick tree (BIT) under sparse point updates.
- Verifies prefix/range queries match the true sums from the fully-updated state.
- Emits a receipt (sizes, hashes, drift_sha256) suitable for lock/regression.
- Also prints:
  - LEAN_OK=1 if the Lean bridge file compiles
  - SHA256 lines for the Lean file + this benchmark

Important (Lean + disk space):
- We *compile* Lean using the bridge-only workspace (no Mathlib).
- We *hash* the Lean file from wherever it actually lives (workspace path by default).
"""

from __future__ import annotations

import gzip
import hashlib
import json
import random
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple

# --- ensure repo root is on sys.path so `import backend...` works ---
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.modules.glyphos.wirepack_codec import (  # noqa: E402
    canonicalize_delta,
    encode_delta,
    encode_delta_stream,
    encode_template,
)

# -------------------- locked parameters --------------------

SEED = 39039
N_AGENTS = 4096
K_UPDATES = 2048
M_EDITS_PER_UPDATE = 4

# query verification (post-stream)
Q_PREFIX = 512
Q_RANGE = 512

# value ranges
VAL_MIN = -100_000
VAL_MAX = 100_000

Op = Tuple[int, int]  # (idx, new_value)

# -------------------- sha / json helpers --------------------


def sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def stable_json(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


# -------------------- Lean check (bridge_only compile, workspace hash) --------------------

# Compile in bridge_only (avoids Mathlib)
LEAN_WS = ROOT / "backend/modules/lean/bridge_only"

# The file name / module path must exist under bridge_only for `lake env lean ...` to work.
LEAN_REL = "SymaticsBridge/V39_FenwickIndexNoMaterialization.lean"
LEAN_FILE_COMPILE = LEAN_WS / LEAN_REL

# Hash the "authoritative" file location (you said this is where it is):
LEAN_FILE_HASH = ROOT / "backend/modules/lean/workspace" / LEAN_REL

THIS_FILE = Path(__file__).resolve()


def lean_check() -> int:
    """
    Compile-check the Lean bridge file using bridge_only lake env.
    This should NOT clone Mathlib.
    """
    if not LEAN_FILE_COMPILE.exists():
        return 0
    r = subprocess.run(
        ["lake", "env", "lean", LEAN_REL],
        cwd=str(LEAN_WS),
    )
    return 1 if r.returncode == 0 else 0


# -------------------- Fenwick tree (BIT) --------------------


class Fenwick:
    """1-indexed Fenwick tree for Int sums."""

    def __init__(self, n: int):
        if n <= 0:
            raise ValueError("n must be positive")
        self.n = n
        self.bit: List[int] = [0] * (n + 1)

    def add(self, idx0: int, delta: int) -> None:
        """Add delta at 0-indexed idx."""
        i = idx0 + 1
        n = self.n
        bit = self.bit
        while i <= n:
            bit[i] += delta
            i += i & -i

    def prefix_sum(self, r0: int) -> int:
        """Sum over [0..r0] inclusive. If r0 < 0 => 0. If r0 >= n => sum(all)."""
        if r0 < 0:
            return 0
        if r0 >= self.n:
            r0 = self.n - 1
        i = r0 + 1
        s = 0
        bit = self.bit
        while i > 0:
            s += bit[i]
            i -= i & -i
        return s

    def range_sum(self, l0: int, r0: int) -> int:
        """Sum over [l0..r0] inclusive."""
        if r0 < l0:
            return 0
        return self.prefix_sum(r0) - self.prefix_sum(l0 - 1)


# -------------------- main benchmark --------------------


def main() -> None:
    rng = random.Random(SEED)

    # base state
    base: List[int] = [rng.randrange(VAL_MIN, VAL_MAX) for _ in range(N_AGENTS)]
    state: List[int] = base.copy()

    # BIT built from base
    bit = Fenwick(N_AGENTS)
    for i, v in enumerate(base):
        if v != 0:
            bit.add(i, v)

    # wirepack stream
    canon_idempotent_ok = True
    canon_stable_ok = True
    deltas_can: List[bytes] = []

    for _t in range(K_UPDATES):
        ops: List[Op] = []
        for _ in range(M_EDITS_PER_UPDATE):
            idx = rng.randrange(0, N_AGENTS)
            newv = rng.randrange(VAL_MIN, VAL_MAX)
            ops.append((idx, newv))

        # A: encode then canonicalize
        d_raw_a = encode_delta(ops)
        d_can_a = canonicalize_delta(d_raw_a)

        # B: shuffle ops then encode then canonicalize (order-independence check)
        ops_b = list(ops)
        rng.shuffle(ops_b)
        d_raw_b = encode_delta(ops_b)
        d_can_b = canonicalize_delta(d_raw_b)

        # Canon idempotence
        if canonicalize_delta(d_can_a) != d_can_a:
            canon_idempotent_ok = False

        # Canon stability vs input op-order
        if d_can_b != d_can_a:
            canon_stable_ok = False

        # Apply updates to state + BIT (using diffs)
        # NOTE: semantics here are "set index to new value".
        for idx, newv in ops:
            oldv = state[idx]
            if newv != oldv:
                state[idx] = newv
                bit.add(idx, newv - oldv)

        deltas_can.append(d_can_a)

    # Query verification (post-stream)
    query_ok = True

    # prefix queries
    for _ in range(Q_PREFIX):
        r = rng.randrange(0, N_AGENTS)
        true_sum = sum(state[: r + 1])
        bit_sum = bit.prefix_sum(r)
        if true_sum != bit_sum:
            query_ok = False
            break

    # range queries
    if query_ok:
        for _ in range(Q_RANGE):
            l = rng.randrange(0, N_AGENTS)
            r = rng.randrange(0, N_AGENTS)
            if l > r:
                l, r = r, l
            true_sum = sum(state[l : r + 1])
            bit_sum = bit.range_sum(l, r)
            if true_sum != bit_sum:
                query_ok = False
                break

    # wire sizes
    template_bytes = encode_template(base)
    delta_stream_bytes = encode_delta_stream(deltas_can)

    raw_template = len(template_bytes)
    raw_deltas = len(delta_stream_bytes)
    gz_template = len(gzip.compress(template_bytes, compresslevel=9))
    gz_deltas = len(gzip.compress(delta_stream_bytes, compresslevel=9))

    # anchors
    final_state_sha = sha256_hex(encode_template(state))

    receipt_obj = {
        "codec": "wirepack_v1",
        "seed": SEED,
        "n_agents": N_AGENTS,
        "k_updates": K_UPDATES,
        "m_edits_per_update": M_EDITS_PER_UPDATE,
        "q_prefix": Q_PREFIX,
        "q_range": Q_RANGE,
        "canon_idempotent_ok": canon_idempotent_ok,
        "canon_stable_ok": canon_stable_ok,
        "query_ok": query_ok,
        "final_state_sha256": final_state_sha,
        "template_sha256": sha256_hex(template_bytes),
        "deltas_sha256": sha256_hex(delta_stream_bytes),
        "raw_template_bytes": raw_template,
        "raw_delta_stream_bytes": raw_deltas,
        "gz_template_bytes": gz_template,
        "gz_delta_stream_bytes": gz_deltas,
    }
    drift_payload = stable_json(receipt_obj)
    drift_sha256 = sha256_hex(drift_payload)

    # -------------------- print receipt --------------------

    print("=== ✅ Bridge Benchmark v39: Fenwick index over delta stream (no materialization) ===")
    print("v39_fenwick_index_no_materialization_wirepack")
    print(f"seed={SEED}")
    print(f"n_agents={N_AGENTS} k_updates={K_UPDATES} m_edits_per_update={M_EDITS_PER_UPDATE}")
    print(f"q_prefix={Q_PREFIX} q_range={Q_RANGE}")
    print(f"canon_idempotent_ok={canon_idempotent_ok}")
    print(f"canon_stable_ok={canon_stable_ok}")
    print(f"query_ok={query_ok}")
    print(f"raw_template_bytes={raw_template}")
    print(f"raw_delta_stream_bytes={raw_deltas}")
    if raw_deltas > 0:
        print(f"raw_ratio(template/delta)={raw_template / raw_deltas:.6f}")
    print(f"gz_template_bytes={gz_template}")
    print(f"gz_delta_stream_bytes={gz_deltas}")
    if gz_deltas > 0:
        print(f"gz_ratio(template/delta)={gz_template / gz_deltas:.6f}")
    print(f"final_state_sha256={final_state_sha}")
    print(f"drift_sha256={drift_sha256}")

    LEAN_OK = lean_check()
    print("\nLEAN_OK={}\n".format(LEAN_OK))

    print("SHA256 (v39)\n")
    if LEAN_FILE_HASH.exists():
        print(f"{sha256_file(LEAN_FILE_HASH)}  {LEAN_FILE_HASH.as_posix()}")
    else:
        print(f"<missing>  {LEAN_FILE_HASH.as_posix()}")
    print(f"{sha256_file(THIS_FILE)}  {THIS_FILE.as_posix()}")

    # -------------------- assertions --------------------
    assert canon_idempotent_ok, "canon must be idempotent"
    assert canon_stable_ok, "canon must erase op-order nondeterminism"
    assert query_ok, "Fenwick prefix/range queries must match true sums"

    # Require Lean compile only if the bridge_only compile target exists
    if LEAN_FILE_COMPILE.exists():
        assert LEAN_OK == 1, "Lean bridge file must compile (bridge_only lake env lean ...)"


if __name__ == "__main__":
    main()