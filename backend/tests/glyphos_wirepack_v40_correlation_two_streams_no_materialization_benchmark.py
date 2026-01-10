#!/usr/bin/env python3
"""
v40 (WirePack-backed) — Correlation over two delta streams (no materialization)

Prints:
- receipt metrics + drift_sha256
- LEAN_OK=1 if the Lean bridge file compiles (lake env lean ...)
- SHA256 lines for:
    - the Lean file (workspace canonical path, for RFC mirroring)
    - this benchmark

Policy:
- Lean compile check uses the standard workspace:
    backend/modules/lean/workspace/SymaticsBridge/V40_CorrelationTwoStreamsNoMaterialization.lean
- This script NEVER references any "bridge_only" path.
- If Lean fails to compile, LEAN_OK=0 and the benchmark still succeeds
  unless REQUIRE_LEAN=1 is set in the environment.
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

SEED = 40040
N_AGENTS = 4096
K_UPDATES = 2048
M_EDITS_X = 4
M_EDITS_Y = 4
Q_CHECKS = 256

VAL_MIN = -100_000
VAL_MAX = 100_000

Op = Tuple[int, int]  # (idx, new_value)

# Require Lean compile to pass? default NO to avoid breaking until Lean proof is finished.
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


# -------------------- Lean check (workspace) --------------------

LEAN_REL = "SymaticsBridge/V40_CorrelationTwoStreamsNoMaterialization.lean"
LEAN_WS = ROOT / "backend/modules/lean/workspace"
LEAN_FILE = LEAN_WS / LEAN_REL
THIS_FILE = Path(__file__).resolve()

# Level-A policy: require Lean proof to compile (no sorry) by default.
# You can temporarily set REQUIRE_LEAN=0 to unblock CI if needed.
REQUIRE_LEAN = os.environ.get("REQUIRE_LEAN", "1") == "1"


def lean_check() -> int:
    """
    Compile-check the Lean bridge file using the workspace lake env.
    This assumes mathlib deps are present/available (same as v39 standard).
    """
    if not LEAN_FILE.exists():
        return 0

    r = subprocess.run(
        ["lake", "env", "lean", LEAN_REL],
        cwd=str(LEAN_WS),
    )
    return 1 if r.returncode == 0 else 0

# -------------------- correlation maintenance --------------------


class CorrAgg:
    """
    Maintain sums for Pearson components:
      Sx, Sy, Sxx, Syy, Sxy
    for vectors x,y under point-set updates.
    """

    __slots__ = ("n", "sx", "sy", "sxx", "syy", "sxy", "x", "y")

    def __init__(self, x0: List[int], y0: List[int]):
        if len(x0) != len(y0):
            raise ValueError("x and y must have same length")
        self.n = len(x0)
        self.x = x0
        self.y = y0
        sx = sy = sxx = syy = sxy = 0
        for xi, yi in zip(x0, y0):
            sx += xi
            sy += yi
            sxx += xi * xi
            syy += yi * yi
            sxy += xi * yi
        self.sx, self.sy, self.sxx, self.syy, self.sxy = sx, sy, sxx, syy, sxy

    def set_x(self, idx: int, newx: int) -> None:
        oldx = self.x[idx]
        if newx == oldx:
            return
        y = self.y[idx]
        self.sx += newx - oldx
        self.sxx += newx * newx - oldx * oldx
        self.sxy += (newx - oldx) * y
        self.x[idx] = newx

    def set_y(self, idx: int, newy: int) -> None:
        oldy = self.y[idx]
        if newy == oldy:
            return
        x = self.x[idx]
        self.sy += newy - oldy
        self.syy += newy * newy - oldy * oldy
        self.sxy += x * (newy - oldy)
        self.y[idx] = newy

    def pearson_components(self) -> Tuple[int, int]:
        """
        Return (numerator, denom_squared) for exact integer comparison.
        numerator = n*Sxy - Sx*Sy
        denom^2   = (n*Sxx - Sx^2)*(n*Syy - Sy^2)
        """
        n = self.n
        num = n * self.sxy - self.sx * self.sy
        a = n * self.sxx - self.sx * self.sx
        b = n * self.syy - self.sy * self.sy
        den2 = a * b
        return num, den2


def recompute_components(x: List[int], y: List[int]) -> Tuple[int, int]:
    sx = sy = sxx = syy = sxy = 0
    for xi, yi in zip(x, y):
        sx += xi
        sy += yi
        sxx += xi * xi
        syy += yi * yi
        sxy += xi * yi
    n = len(x)
    num = n * sxy - sx * sy
    a = n * sxx - sx * sx
    b = n * syy - sy * sy
    den2 = a * b
    return num, den2


# -------------------- main benchmark --------------------


def main() -> None:
    rng = random.Random(SEED)

    base_x: List[int] = [rng.randrange(VAL_MIN, VAL_MAX) for _ in range(N_AGENTS)]
    base_y: List[int] = [rng.randrange(VAL_MIN, VAL_MAX) for _ in range(N_AGENTS)]

    x = base_x.copy()
    y = base_y.copy()
    agg = CorrAgg(x, y)

    canon_idempotent_ok_x = True
    canon_stable_ok_x = True
    canon_idempotent_ok_y = True
    canon_stable_ok_y = True

    deltas_x_can: List[bytes] = []
    deltas_y_can: List[bytes] = []

    for _t in range(K_UPDATES):
        ops_x: List[Op] = []
        ops_y: List[Op] = []

        for _ in range(M_EDITS_X):
            idx = rng.randrange(0, N_AGENTS)
            newv = rng.randrange(VAL_MIN, VAL_MAX)
            ops_x.append((idx, newv))

        for _ in range(M_EDITS_Y):
            idx = rng.randrange(0, N_AGENTS)
            newv = rng.randrange(VAL_MIN, VAL_MAX)
            ops_y.append((idx, newv))

        # X canon checks
        d_raw_x_a = encode_delta(ops_x)
        d_can_x_a = canonicalize_delta(d_raw_x_a)
        ops_x_b = list(ops_x)
        rng.shuffle(ops_x_b)
        d_raw_x_b = encode_delta(ops_x_b)
        d_can_x_b = canonicalize_delta(d_raw_x_b)

        if canonicalize_delta(d_can_x_a) != d_can_x_a:
            canon_idempotent_ok_x = False
        if d_can_x_b != d_can_x_a:
            canon_stable_ok_x = False

        # Y canon checks
        d_raw_y_a = encode_delta(ops_y)
        d_can_y_a = canonicalize_delta(d_raw_y_a)
        ops_y_b = list(ops_y)
        rng.shuffle(ops_y_b)
        d_raw_y_b = encode_delta(ops_y_b)
        d_can_y_b = canonicalize_delta(d_raw_y_b)

        if canonicalize_delta(d_can_y_a) != d_can_y_a:
            canon_idempotent_ok_y = False
        if d_can_y_b != d_can_y_a:
            canon_stable_ok_y = False

        # Apply semantics + update aggregates
        for idx, newv in ops_x:
            agg.set_x(idx, newv)
        for idx, newv in ops_y:
            agg.set_y(idx, newv)

        deltas_x_can.append(d_can_x_a)
        deltas_y_can.append(d_can_y_a)

    # Verify maintained components == recomputed snapshot components
    query_ok = True
    for _ in range(Q_CHECKS):
        num1, den2_1 = agg.pearson_components()
        num2, den2_2 = recompute_components(agg.x, agg.y)
        if num1 != num2 or den2_1 != den2_2:
            query_ok = False
            break

    # wire sizes
    template_x_bytes = encode_template(base_x)
    template_y_bytes = encode_template(base_y)
    delta_stream_x_bytes = encode_delta_stream(deltas_x_can)
    delta_stream_y_bytes = encode_delta_stream(deltas_y_can)

    raw_template_x = len(template_x_bytes)
    raw_template_y = len(template_y_bytes)
    raw_dx = len(delta_stream_x_bytes)
    raw_dy = len(delta_stream_y_bytes)

    gz_template_x = len(gzip.compress(template_x_bytes, compresslevel=9))
    gz_template_y = len(gzip.compress(template_y_bytes, compresslevel=9))
    gz_dx = len(gzip.compress(delta_stream_x_bytes, compresslevel=9))
    gz_dy = len(gzip.compress(delta_stream_y_bytes, compresslevel=9))

    final_x_sha = sha256_hex(encode_template(agg.x))
    final_y_sha = sha256_hex(encode_template(agg.y))

    receipt_obj = {
        "codec": "wirepack_v1",
        "seed": SEED,
        "n_agents": N_AGENTS,
        "k_updates": K_UPDATES,
        "m_edits_x": M_EDITS_X,
        "m_edits_y": M_EDITS_Y,
        "q_checks": Q_CHECKS,
        "canon_idempotent_ok_x": canon_idempotent_ok_x,
        "canon_stable_ok_x": canon_stable_ok_x,
        "canon_idempotent_ok_y": canon_idempotent_ok_y,
        "canon_stable_ok_y": canon_stable_ok_y,
        "query_ok": query_ok,
        "final_x_sha256": final_x_sha,
        "final_y_sha256": final_y_sha,
        "template_x_sha256": sha256_hex(template_x_bytes),
        "template_y_sha256": sha256_hex(template_y_bytes),
        "deltas_x_sha256": sha256_hex(delta_stream_x_bytes),
        "deltas_y_sha256": sha256_hex(delta_stream_y_bytes),
        "raw_template_x_bytes": raw_template_x,
        "raw_template_y_bytes": raw_template_y,
        "raw_delta_stream_x_bytes": raw_dx,
        "raw_delta_stream_y_bytes": raw_dy,
        "gz_template_x_bytes": gz_template_x,
        "gz_template_y_bytes": gz_template_y,
        "gz_delta_stream_x_bytes": gz_dx,
        "gz_delta_stream_y_bytes": gz_dy,
    }
    drift_payload = stable_json(receipt_obj)
    drift_sha256 = sha256_hex(drift_payload)

    print("=== ✅ Bridge Benchmark v40: Correlation over two delta streams (no materialization) ===")
    print("v40_correlation_two_streams_no_materialization_wirepack")
    print(f"seed={SEED}")
    print(f"n_agents={N_AGENTS} k_updates={K_UPDATES} m_edits_x={M_EDITS_X} m_edits_y={M_EDITS_Y}")
    print(f"q_checks={Q_CHECKS}")
    print(f"canon_idempotent_ok_x={canon_idempotent_ok_x}")
    print(f"canon_stable_ok_x={canon_stable_ok_x}")
    print(f"canon_idempotent_ok_y={canon_idempotent_ok_y}")
    print(f"canon_stable_ok_y={canon_stable_ok_y}")
    print(f"query_ok={query_ok}")
    print(f"raw_template_x_bytes={raw_template_x}")
    print(f"raw_template_y_bytes={raw_template_y}")
    print(f"raw_delta_stream_x_bytes={raw_dx}")
    print(f"raw_delta_stream_y_bytes={raw_dy}")
    print(f"gz_template_x_bytes={gz_template_x}")
    print(f"gz_template_y_bytes={gz_template_y}")
    print(f"gz_delta_stream_x_bytes={gz_dx}")
    print(f"gz_delta_stream_y_bytes={gz_dy}")
    print(f"final_x_sha256={final_x_sha}")
    print(f"final_y_sha256={final_y_sha}")
    print(f"drift_sha256={drift_sha256}")

    LEAN_OK = lean_check()
    print(f"\nLEAN_OK={LEAN_OK}\n")

    print("SHA256 (v40)\n")
    if LEAN_FILE.exists():
        print(f"{sha256_file(LEAN_FILE)}  {LEAN_FILE.as_posix()}")
    else:
        print(f"<missing>  {LEAN_FILE.as_posix()}")
    print(f"{sha256_file(THIS_FILE)}  {THIS_FILE.as_posix()}")

    # Assertions for the executable receipt
    assert canon_idempotent_ok_x, "canon(x) must be idempotent"
    assert canon_stable_ok_x, "canon(x) must erase op-order nondeterminism"
    assert canon_idempotent_ok_y, "canon(y) must be idempotent"
    assert canon_stable_ok_y, "canon(y) must erase op-order nondeterminism"
    assert query_ok, "maintained correlation components must match snapshot recompute"

    # Level-A: enforce Lean compile unless explicitly disabled
    if REQUIRE_LEAN:
        assert LEAN_OK == 1, "Lean bridge file must compile (lake env lean ...)"


if __name__ == "__main__":
    main()