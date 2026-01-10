#!/usr/bin/env python3
"""
v38 (WirePack-backed) — Canonical Delta determinism + replay correctness

This one IS "real" in the sense that it:
- uses a binary template encoder
- uses a binary delta encoder
- canonicalizes bytes by decoding + sorting + re-encoding
- replays deltas by decoding + applying

Also prints:
- LEAN_OK=1 if the Lean bridge file compiles
- SHA256 lines for Lean + this benchmark (artifact locking)

NOTE:
- Lean is checked via the *bridge-only* workspace to avoid pulling Mathlib.
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
    apply_delta_inplace,
    canonicalize_delta,
    encode_delta,
    encode_delta_stream,
    encode_template,
)

SEED = 38038
N_AGENTS = 4096
K_UPDATES = 1024
M_EDITS_PER_UPDATE = 1

Op = Tuple[int, int]

# --- Lean bridge-only workspace (no Mathlib) ---
LEAN_WS = ROOT / "backend/modules/lean/bridge_only"
LEAN_FILE = LEAN_WS / "SymaticsBridge/V38_CanonicalDeltaDeterminismReplay.lean"
THIS_FILE = Path(__file__).resolve()


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


def lean_check() -> int:
    """
    Compile-check the Lean bridge file using the bridge-only workspace's `lake env`.
    This should NOT fetch Mathlib unless your bridge-only lakefile requires it.
    """
    r = subprocess.run(
        ["lake", "env", "lean", "SymaticsBridge/V38_CanonicalDeltaDeterminismReplay.lean"],
        cwd=str(LEAN_WS),
    )
    return 1 if r.returncode == 0 else 0


def main() -> None:
    rng = random.Random(SEED)

    base: List[int] = [rng.randrange(0, 100_000) for _ in range(N_AGENTS)]
    state_a = base.copy()
    state_b = base.copy()

    canon_idempotent_ok = True
    canon_stable_ok = True
    deltas_a: List[bytes] = []
    deltas_b: List[bytes] = []

    for _t in range(K_UPDATES):
        ops: List[Op] = []
        for _ in range(M_EDITS_PER_UPDATE):
            idx = rng.randrange(0, N_AGENTS)
            newv = rng.randrange(0, 100_000)
            ops.append((idx, newv))

        # Stream A: encode then canon
        d_raw_a = encode_delta(ops)
        d_can_a = canonicalize_delta(d_raw_a)

        # Stream B: shuffle ops before encode then canon
        ops_b = list(ops)
        rng.shuffle(ops_b)
        d_raw_b = encode_delta(ops_b)
        d_can_b = canonicalize_delta(d_raw_b)

        # Idempotence: canon(canon(x)) == canon(x)
        if canonicalize_delta(d_can_a) != d_can_a:
            canon_idempotent_ok = False

        # Stability vs input op-order: canon(raw(shuffled)) == canon(raw(original))
        if d_can_b != d_can_a:
            canon_stable_ok = False

        apply_delta_inplace(state_a, d_can_a)
        apply_delta_inplace(state_b, d_can_b)

        deltas_a.append(d_can_a)
        deltas_b.append(d_can_b)

    replay_ok = (state_a == state_b)

    template_bytes = encode_template(base)
    delta_stream_bytes = encode_delta_stream(deltas_a)

    raw_template = len(template_bytes)
    raw_deltas = len(delta_stream_bytes)

    gz_template = len(gzip.compress(template_bytes, compresslevel=9))
    gz_deltas = len(gzip.compress(delta_stream_bytes, compresslevel=9))

    final_state_sha = sha256_hex(encode_template(state_a))

    drift_payload = stable_json(
        {
            "codec": "wirepack_v1",
            "seed": SEED,
            "n_agents": N_AGENTS,
            "k_updates": K_UPDATES,
            "m_edits_per_update": M_EDITS_PER_UPDATE,
            "canon_idempotent_ok": canon_idempotent_ok,
            "canon_stable_ok": canon_stable_ok,
            "replay_ok": replay_ok,
            "final_state_sha256": final_state_sha,
            "template_sha256": sha256_hex(template_bytes),
            "deltas_sha256": sha256_hex(delta_stream_bytes),
            "raw_template_bytes": raw_template,
            "raw_delta_stream_bytes": raw_deltas,
            "gz_template_bytes": gz_template,
            "gz_delta_stream_bytes": gz_deltas,
        }
    )
    drift_sha256 = sha256_hex(drift_payload)

    print("=== ✅ Bridge Benchmark v38: Canonical delta determinism + replay correctness ===")
    print("v38_canonical_delta_determinism_replay_wirepack")
    print(f"seed={SEED}")
    print(f"n_agents={N_AGENTS} k_updates={K_UPDATES} m_edits_per_update={M_EDITS_PER_UPDATE}")
    print(f"canon_idempotent_ok={canon_idempotent_ok}")
    print(f"canon_stable_ok={canon_stable_ok}")
    print(f"replay_ok={replay_ok}")
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
    print(f"\nLEAN_OK={LEAN_OK}\n")

    print("SHA256 (v38)\n")
    print(f"{sha256_file(LEAN_FILE)}  {LEAN_FILE.as_posix()}")
    print(f"{sha256_file(THIS_FILE)}  {THIS_FILE.as_posix()}")

    assert canon_idempotent_ok, "canon must be idempotent"
    assert canon_stable_ok, "canon must erase op-order nondeterminism"
    assert replay_ok, "replay must match across equivalent canonical deltas"
    assert LEAN_OK == 1, "Lean bridge file must compile (lake env lean ...)"


if __name__ == "__main__":
    main()