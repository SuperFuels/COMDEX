#!/usr/bin/env python3
"""
v41 (WirePack-backed) — Receipt-gated queries (auth + ancestry bound)

Prints:
- receipt + gating metrics
- LEAN_OK=1 if the Lean bridge file compiles (lake env lean ...)
- SHA256 lines for:
    - the Lean file (workspace canonical path, for RFC mirroring)
    - this benchmark

Policy:
- Lean compile check uses:
    backend/modules/lean/workspace/SymaticsBridge/V41_ReceiptGatedQueries.lean
- If Lean fails to compile, LEAN_OK=0 and the benchmark still succeeds unless REQUIRE_LEAN=1.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import os
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

SEED = 41041
N_AGENTS = 4096
K_UPDATES = 2048
M_EDITS = 4
Q_CHECKS = 256

VAL_MIN = -100_000
VAL_MAX = 100_000

Op = Tuple[int, int]  # (idx, new_value)

UPDATE_LOCKS = os.environ.get("UPDATE_LOCKS", "0") == "1"
REQUIRE_LEAN = os.environ.get("REQUIRE_LEAN", "0") == "1"

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


def sha256_bytes(b: bytes) -> bytes:
    return hashlib.sha256(b).digest()


# -------------------- Lean check (workspace) --------------------

LEAN_REL = "SymaticsBridge/V41_ReceiptGatedQueries.lean"
LEAN_WS = ROOT / "backend/modules/lean/workspace"
LEAN_FILE = LEAN_WS / LEAN_REL
THIS_FILE = Path(__file__).resolve()


def lean_check() -> int:
    if not LEAN_FILE.exists():
        return 0
    r = subprocess.run(["lake", "env", "lean", LEAN_REL], cwd=str(LEAN_WS))
    return 1 if r.returncode == 0 else 0


# -------------------- receipt chain (simple model) --------------------

KEY = b"v41-demo-key"  # demo secret for "signature" binding


def sign(parent: bytes, delta_hash: bytes) -> bytes:
    # Signature-like binding (demo): H(KEY || parent || delta_hash)
    return sha256_bytes(KEY + parent + delta_hash)


def receipt_hash(parent: bytes, delta_hash: bytes, sig: bytes) -> bytes:
    return sha256_bytes(parent + delta_hash + sig)


class Receipt:
    __slots__ = ("parent", "delta", "delta_hash", "sig", "h")

    def __init__(self, parent: bytes, delta: bytes):
        self.parent = parent
        self.delta = delta
        self.delta_hash = sha256_bytes(delta)
        self.sig = sign(parent, self.delta_hash)
        self.h = receipt_hash(parent, self.delta_hash, self.sig)


def verify_chain(receipts: List[Receipt]) -> bool:
    parent = b"\x00" * 32
    for r in receipts:
        if r.parent != parent:
            return False
        if sha256_bytes(r.delta) != r.delta_hash:
            return False
        if sign(r.parent, r.delta_hash) != r.sig:
            return False
        parent = r.h
    return True


# -------------------- query fold (gated) --------------------


class SumAgg:
    __slots__ = ("x", "sx")

    def __init__(self, x0: List[int]):
        self.x = x0
        self.sx = sum(x0)

    def apply_ops(self, ops: List[Op]) -> None:
        for idx, newv in ops:
            old = self.x[idx]
            if newv == old:
                continue
            self.sx += newv - old
            self.x[idx] = newv


def decode_ops(delta_bytes: bytes) -> List[Op]:
    # wirepack delta format is opaque here; we only need *semantic* ops for recompute.
    # But for correctness checks we just reuse the exact ops used to create each delta.
    raise RuntimeError("decode_ops should never be called in this benchmark")


# -------------------- main benchmark --------------------


def main() -> None:
    rng = random.Random(SEED)

    base_x: List[int] = [rng.randrange(VAL_MIN, VAL_MAX) for _ in range(N_AGENTS)]
    x = base_x.copy()
    agg = SumAgg(x)

    deltas_can: List[bytes] = []
    receipts: List[Receipt] = []

    parent = b"\x00" * 32

    # We keep the semantic ops list alongside each delta for recompute checks
    ops_per_delta: List[List[Op]] = []

    for _t in range(K_UPDATES):
        ops: List[Op] = []
        for _ in range(M_EDITS):
            idx = rng.randrange(0, N_AGENTS)
            newv = rng.randrange(VAL_MIN, VAL_MAX)
            ops.append((idx, newv))

        d_raw = encode_delta(ops)
        d_can = canonicalize_delta(d_raw)

        # Apply semantics
        agg.apply_ops(ops)

        # Record stream + receipt chain
        deltas_can.append(d_can)
        r = Receipt(parent, d_can)
        receipts.append(r)
        parent = r.h

        ops_per_delta.append(ops)

    # Query correctness: maintained sum matches snapshot recompute
    query_ok = True
    for _ in range(Q_CHECKS):
        if agg.sx != sum(agg.x):
            query_ok = False
            break

    verify_ok = verify_chain(receipts)
    gated_ok = verify_ok and query_ok

    # Tamper cases
    tamper_ok_delta = False
    tamper_ok_parent = False
    tamper_ok_reorder = False
    tamper_ok_splice = False

    if receipts:
        # delta tamper: flip one byte of a delta (do not update delta_hash/sig)
        t = receipts.copy()
        r0 = t[len(t) // 2]
        bad = bytearray(r0.delta)
        bad[0] ^= 0x01
        r0.delta = bytes(bad)
        tamper_ok_delta = (verify_chain(t) is False)

        # parent tamper: change parent pointer
        t = receipts.copy()
        t[len(t) // 3].parent = b"\x11" * 32
        tamper_ok_parent = (verify_chain(t) is False)

        # reorder: swap two adjacent receipts
        t = receipts.copy()
        if len(t) >= 2:
            i = len(t) // 2
            j = min(i + 1, len(t) - 1)
            t[i], t[j] = t[j], t[i]
            tamper_ok_reorder = (verify_chain(t) is False)

        # splice: remove one receipt
        t = receipts.copy()
        if len(t) >= 3:
            del t[len(t) // 2]
            tamper_ok_splice = (verify_chain(t) is False)

    # wire sizes
    template_bytes = encode_template(base_x)
    delta_stream_bytes = encode_delta_stream(deltas_can)

    raw_template = len(template_bytes)
    raw_ds = len(delta_stream_bytes)
    gz_template = len(gzip.compress(template_bytes, compresslevel=9))
    gz_ds = len(gzip.compress(delta_stream_bytes, compresslevel=9))

    final_x_sha = sha256_hex(encode_template(agg.x))

    receipt_obj = {
        "codec": "wirepack_v1",
        "seed": SEED,
        "n_agents": N_AGENTS,
        "k_updates": K_UPDATES,
        "m_edits": M_EDITS,
        "q_checks": Q_CHECKS,
        "query_ok": query_ok,
        "verify_ok": verify_ok,
        "gated_ok": gated_ok,
        "tamper_ok_delta": tamper_ok_delta,
        "tamper_ok_parent": tamper_ok_parent,
        "tamper_ok_reorder": tamper_ok_reorder,
        "tamper_ok_splice": tamper_ok_splice,
        "final_x_sha256": final_x_sha,
        "template_sha256": sha256_hex(template_bytes),
        "deltas_sha256": sha256_hex(delta_stream_bytes),
        "raw_template_bytes": raw_template,
        "raw_delta_stream_bytes": raw_ds,
        "gz_template_bytes": gz_template,
        "gz_delta_stream_bytes": gz_ds,
    }
    drift_payload = stable_json(receipt_obj)
    drift_sha256 = sha256_hex(drift_payload)

    print("=== ✅ Bridge Benchmark v41: Receipt-gated queries (auth + ancestry bound) ===")
    print("v41_receipt_gated_queries_wirepack")
    print(f"seed={SEED}")
    print(f"n_agents={N_AGENTS} k_updates={K_UPDATES} m_edits={M_EDITS}")
    print(f"q_checks={Q_CHECKS}")
    print(f"query_ok={query_ok}")
    print(f"verify_ok={verify_ok}")
    print(f"gated_ok={gated_ok}")
    print(f"tamper_ok_delta={tamper_ok_delta}")
    print(f"tamper_ok_parent={tamper_ok_parent}")
    print(f"tamper_ok_reorder={tamper_ok_reorder}")
    print(f"tamper_ok_splice={tamper_ok_splice}")
    print(f"raw_template_bytes={raw_template}")
    print(f"raw_delta_stream_bytes={raw_ds}")
    print(f"gz_template_bytes={gz_template}")
    print(f"gz_delta_stream_bytes={gz_ds}")
    print(f"final_x_sha256={final_x_sha}")
    print(f"drift_sha256={drift_sha256}")

    LEAN_OK = lean_check()
    print(f"\nLEAN_OK={LEAN_OK}\n")

    print("SHA256 (v41)\n")
    if LEAN_FILE.exists():
        print(f"{sha256_file(LEAN_FILE)}  {LEAN_FILE.as_posix()}")
    else:
        print(f"<missing>  {LEAN_FILE.as_posix()}")
    print(f"{sha256_file(THIS_FILE)}  {THIS_FILE.as_posix()}")

    # Assertions for executable receipt
    assert query_ok, "maintained query must match snapshot recompute"
    assert verify_ok, "receipt chain must verify"
    assert gated_ok, "gated_ok must hold for untampered stream"
    assert tamper_ok_delta, "delta tamper must fail verification"
    assert tamper_ok_parent, "parent tamper must fail verification"
    assert tamper_ok_reorder, "reorder tamper must fail verification"
    assert tamper_ok_splice, "splice tamper must fail verification"

    if REQUIRE_LEAN:
        assert LEAN_OK == 1, "Lean bridge file must compile (lake env lean ...)"


if __name__ == "__main__":
    main()
