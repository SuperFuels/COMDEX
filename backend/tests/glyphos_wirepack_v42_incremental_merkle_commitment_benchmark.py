#!/usr/bin/env python3
"""
v42 — Incremental Merkle-style commitment from deltas (no materialization)

Prints (deterministic, lockable):
- receipt metrics + drift_sha256
- LEAN_OK=1 if the Lean bridge compiles
- SHA256 lines for:
    - the Lean file (workspace canonical path)
    - this benchmark

Policy:
- Lean compile check uses:
    backend/modules/lean/workspace/SymaticsBridge/V42_IncrementalMerkleCommitment.lean
- If Lean fails, LEAN_OK=0 and the benchmark still succeeds
  unless REQUIRE_LEAN=1 is set.
- If UPDATE_LOCKS=1:
    - writes backend/tests/locks/v42_incremental_merkle_commitment_out.txt
      from the deterministic stdout payload
    - writes backend/tests/locks/v42_incremental_merkle_commitment_lock.sha256
      using sha256(Lean file) and sha256(stdout payload)

IMPORTANT:
- Wall-clock timings are nondeterministic; they are excluded from locked output and drift_sha256.
  Timings print only when PRINT_TIMINGS=1 (and do not affect drift).
"""

from __future__ import annotations

import gzip
import hashlib
import json
import os
import random
import subprocess
import sys
import time
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

SEED = 42042
N_LEAVES = 4096  # must be power of 2
K_UPDATES = 2048
M_EDITS = 4
Q_CHECKS = 256

VAL_MIN = -100_000
VAL_MAX = 100_000

Op = Tuple[int, int]  # (idx, new_value)

REQUIRE_LEAN = os.environ.get("REQUIRE_LEAN", "1") == "1"
UPDATE_LOCKS = os.environ.get("UPDATE_LOCKS", "0") == "1"
PRINT_TIMINGS = os.environ.get("PRINT_TIMINGS", "0") == "1"

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


# -------------------- Lean check (workspace) --------------------

LEAN_REL = "SymaticsBridge/V42_IncrementalMerkleCommitment.lean"
LEAN_WS = ROOT / "backend/modules/lean/workspace"
LEAN_FILE = LEAN_WS / LEAN_REL
THIS_FILE = Path(__file__).resolve()

LOCK_DIR = ROOT / "backend/tests/locks"
OUT_FILE = LOCK_DIR / "v42_incremental_merkle_commitment_out.txt"
LOCK_SHA = LOCK_DIR / "v42_incremental_merkle_commitment_lock.sha256"


def lean_check() -> int:
    if not LEAN_FILE.exists():
        return 0
    r = subprocess.run(
        ["lake", "env", "lean", LEAN_REL],
        cwd=str(LEAN_WS),
    )
    return 1 if r.returncode == 0 else 0


# -------------------- merkle implementation --------------------

_hash_ops = 0


def leaf_hash(v: int) -> bytes:
    b = int(v).to_bytes(8, byteorder="big", signed=True)
    return hashlib.sha256(b).digest()


def node_hash(a: bytes, b: bytes) -> bytes:
    global _hash_ops
    _hash_ops += 1
    return hashlib.sha256(a + b).digest()


def build_levels(leaves: List[bytes]) -> List[List[bytes]]:
    # levels[0] = leaves, levels[-1][0] = root
    levels: List[List[bytes]] = [leaves[:]]
    cur = leaves[:]
    while len(cur) > 1:
        nxt = [node_hash(cur[i], cur[i + 1]) for i in range(0, len(cur), 2)]
        levels.append(nxt)
        cur = nxt
    return levels


def update_levels_in_place(levels: List[List[bytes]], idx: int, new_leaf: bytes) -> bytes:
    levels[0][idx] = new_leaf
    i = idx
    for lvl in range(1, len(levels)):
        parent = i // 2
        left = levels[lvl - 1][2 * parent]
        right = levels[lvl - 1][2 * parent + 1]
        levels[lvl][parent] = node_hash(left, right)
        i = parent
    return levels[-1][0]


def main() -> None:
    assert (N_LEAVES & (N_LEAVES - 1)) == 0, "N_LEAVES must be power of two"

    rng = random.Random(SEED)

    base_x: List[int] = [rng.randrange(VAL_MIN, VAL_MAX) for _ in range(N_LEAVES)]
    template_bytes = encode_template(base_x)

    leaves = [leaf_hash(v) for v in base_x]
    global _hash_ops
    _hash_ops = 0
    levels = build_levels(leaves)
    root_inc = levels[-1][0]
    inc_hash_ops_init = _hash_ops

    def full_root(x_vals: List[int]) -> bytes:
        lf = [leaf_hash(v) for v in x_vals]
        global _hash_ops
        _hash_ops = 0
        lv = build_levels(lf)
        return lv[-1][0]

    deltas_can: List[bytes] = []
    x_materialized = base_x[:]  # only for verification

    inc_hash_ops_updates = 0
    full_hash_ops_checks = 0
    t_inc = 0.0
    t_full = 0.0

    root_ok = True
    check_stride = max(1, (K_UPDATES // Q_CHECKS))

    for t in range(K_UPDATES):
        ops: List[Op] = []
        for _ in range(M_EDITS):
            idx = rng.randrange(0, N_LEAVES)
            newv = rng.randrange(VAL_MIN, VAL_MAX)
            ops.append((idx, newv))

        d_raw = encode_delta(ops)
        d_can = canonicalize_delta(d_raw)
        deltas_can.append(d_can)

        for idx, newv in ops:
            x_materialized[idx] = newv
            new_leaf = leaf_hash(newv)

            _hash_ops = 0
            t0 = time.perf_counter()
            root_inc = update_levels_in_place(levels, idx, new_leaf)
            t_inc += time.perf_counter() - t0
            inc_hash_ops_updates += _hash_ops

        if (t + 1) % check_stride == 0:
            _hash_ops = 0
            t0 = time.perf_counter()
            root_full = full_root(x_materialized)
            t_full += time.perf_counter() - t0
            full_hash_ops_checks += _hash_ops
            if root_full != root_inc:
                root_ok = False
                break

    delta_stream_bytes = encode_delta_stream(deltas_can)
    raw_template = len(template_bytes)
    raw_ds = len(delta_stream_bytes)
    gz_template = len(gzip.compress(template_bytes, compresslevel=9))
    gz_ds = len(gzip.compress(delta_stream_bytes, compresslevel=9))

    # Deterministic receipt payload (NO timings).
    receipt_obj = {
        "codec": "wirepack_v1",
        "seed": SEED,
        "n_leaves": N_LEAVES,
        "k_updates": K_UPDATES,
        "m_edits": M_EDITS,
        "q_checks": Q_CHECKS,
        "root_ok": root_ok,
        "root_hex": root_inc.hex(),
        "raw_template_bytes": raw_template,
        "raw_delta_stream_bytes": raw_ds,
        "gz_template_bytes": gz_template,
        "gz_delta_stream_bytes": gz_ds,
        "inc_hash_ops_init": inc_hash_ops_init,
        "inc_hash_ops_updates": inc_hash_ops_updates,
        "full_hash_ops_checks": full_hash_ops_checks,
        "template_sha256": sha256_hex(template_bytes),
        "deltas_sha256": sha256_hex(delta_stream_bytes),
    }
    drift_sha256 = sha256_hex(stable_json(receipt_obj))

    LEAN_OK = lean_check()

    # Build deterministic stdout payload (lock compared).
    lines: List[str] = []
    lines.append("=== ✅ Bridge Benchmark v42: Incremental Merkle-style commitment (no materialization) ===")
    lines.append("v42_incremental_merkle_commitment_wirepack")
    lines.append(f"seed={SEED}")
    lines.append(f"n_leaves={N_LEAVES} k_updates={K_UPDATES} m_edits={M_EDITS}")
    lines.append(f"q_checks={Q_CHECKS}")
    lines.append(f"root_ok={root_ok}")
    lines.append(f"root_hex={root_inc.hex()}")
    lines.append(f"raw_template_bytes={raw_template}")
    lines.append(f"raw_delta_stream_bytes={raw_ds}")
    lines.append(f"gz_template_bytes={gz_template}")
    lines.append(f"gz_delta_stream_bytes={gz_ds}")
    lines.append(f"inc_hash_ops_init={inc_hash_ops_init}")
    lines.append(f"inc_hash_ops_updates={inc_hash_ops_updates}")
    lines.append(f"full_hash_ops_checks={full_hash_ops_checks}")

    # Optional timings (NOT part of drift/locks unless you choose to save them).
    if PRINT_TIMINGS:
        lines.append(f"t_incremental_s={round(t_inc, 6)}")
        lines.append(f"t_full_checks_s={round(t_full, 6)}")

    lines.append(f"drift_sha256={drift_sha256}")
    lines.append("")
    lines.append(f"LEAN_OK={LEAN_OK}")
    lines.append("")
    lines.append("SHA256 (v42)")
    lines.append("")
    if LEAN_FILE.exists():
        lines.append(f"{sha256_file(LEAN_FILE)}  {LEAN_FILE.as_posix()}")
    else:
        lines.append(f"<missing>  {LEAN_FILE.as_posix()}")
    lines.append(f"{sha256_file(THIS_FILE)}  {THIS_FILE.as_posix()}")

    out_text = "\n".join(lines) + "\n"
    out_bytes = out_text.encode("utf-8")

    # If updating locks, write OUT + LOCK using the stdout payload hash (no tee race).
    if UPDATE_LOCKS:
        LOCK_DIR.mkdir(parents=True, exist_ok=True)
        OUT_FILE.write_bytes(out_bytes)

        lean_sha = sha256_file(LEAN_FILE)
        out_sha = hashlib.sha256(out_bytes).hexdigest()
        LOCK_SHA.write_text(
            f"{lean_sha}  backend/modules/lean/workspace/{LEAN_REL}\n"
            f"{out_sha}  backend/tests/locks/{OUT_FILE.name}\n",
            encoding="utf-8",
        )
        print(f"wrote {LOCK_SHA.as_posix()}", file=sys.stderr)

    # Emit stdout last, once.
    sys.stdout.write(out_text)

    assert root_ok, "incremental root must match snapshot recompute at every check"
    if REQUIRE_LEAN:
        assert LEAN_OK == 1, "Lean bridge file must compile (lake env lean ...)"


if __name__ == "__main__":
    main()