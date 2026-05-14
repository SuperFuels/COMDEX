#!/usr/bin/env python3
"""
v44 — SQL subset translation on stream primitives (SELECT/WHERE/GROUP BY + simple JOIN)

Query modeled:
  SELECT bucket, SUM(a[i] + b[i])
  FROM A JOIN B ON i
  WHERE a[i] > THRESH_A AND b[i] < THRESH_B
  GROUP BY bucket = (i % N_BUCKETS)

We maintain the GROUP BY result incrementally from two independent delta streams (A and B),
and verify semantic equivalence vs snapshot recompute at periodic checkpoints.

WirePack/GlyphOS:
- Uses backend.modules.glyphos.wirepack_codec for:
    encode_template, encode_delta, canonicalize_delta, encode_delta_stream
- Reports raw/gz sizes + drift_sha256.

Lock policy:
- stdout is lock-compared byte-for-byte (no timings; no "wrote ..." on stdout).
- If UPDATE_LOCKS=1, writes backend/tests/locks/v44_sql_subset_translation_lock.sha256
  using sha256(Lean file) and sha256(locked out file), and prints the "wrote ..." line to stderr.
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

SEED = 44044
N_ROWS = 4096
N_BUCKETS = 64

K_UPDATES = 2048
M_EDITS_A = 4
M_EDITS_B = 4
Q_CHECKS = 256

VAL_MIN = -100_000
VAL_MAX = 100_000

THRESH_A = 0
THRESH_B = 0  # predicate is b < THRESH_B

Op = Tuple[int, int]  # (idx, new_value)

REQUIRE_LEAN = os.environ.get("REQUIRE_LEAN", "1") == "1"
UPDATE_LOCKS = os.environ.get("UPDATE_LOCKS", "0") == "1"
PRINT_LEAN_LOG = os.environ.get("PRINT_LEAN_LOG", "0") == "1"

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

LEAN_REL = "SymaticsBridge/V44_SQLSubsetTranslationNoMaterialization.lean"
LEAN_WS = ROOT / "backend/modules/lean/workspace"
LEAN_FILE = LEAN_WS / LEAN_REL
THIS_FILE = Path(__file__).resolve()

LOCK_DIR = ROOT / "backend/tests/locks"
OUT_FILE = LOCK_DIR / "v44_sql_subset_translation_out.txt"
LOCK_SHA = LOCK_DIR / "v44_sql_subset_translation_lock.sha256"


def lean_check() -> int:
    if not LEAN_FILE.exists():
        return 0
    if PRINT_LEAN_LOG:
        r = subprocess.run(
            ["lake", "env", "lean", LEAN_REL],
            cwd=str(LEAN_WS),
        )
    else:
        r = subprocess.run(
            ["lake", "env", "lean", LEAN_REL],
            cwd=str(LEAN_WS),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    return 1 if r.returncode == 0 else 0


# -------------------- query semantics --------------------


def contrib(a: int, b: int) -> int:
    # WHERE a > THRESH_A AND b < THRESH_B
    if a > THRESH_A and b < THRESH_B:
        return a + b
    return 0


def bucket_of(i: int) -> int:
    return i % N_BUCKETS


def snapshot_groupby_join(a: List[int], b: List[int]) -> List[int]:
    out = [0] * N_BUCKETS
    for i in range(N_ROWS):
        out[bucket_of(i)] += contrib(a[i], b[i])
    return out


def main() -> None:
    assert N_ROWS > 0 and N_BUCKETS > 0
    rng = random.Random(SEED)

    # base tables (two systems)
    a: List[int] = [rng.randrange(VAL_MIN, VAL_MAX) for _ in range(N_ROWS)]
    b: List[int] = [rng.randrange(VAL_MIN, VAL_MAX) for _ in range(N_ROWS)]

    # wirepack templates
    tmpl_a = encode_template(a)
    tmpl_b = encode_template(b)

    # maintained GROUP BY result (no snapshot scan per query)
    agg = snapshot_groupby_join(a, b)

    deltas_a_can: List[bytes] = []
    deltas_b_can: List[bytes] = []

    canon_idempotent_ok = True
    canon_stable_ok = True
    query_ok = True

    check_stride = max(1, (K_UPDATES // Q_CHECKS))

    for t in range(K_UPDATES):
        # generate sparse deltas for each system
        ops_a: List[Op] = []
        ops_b: List[Op] = []

        for _ in range(M_EDITS_A):
            idx = rng.randrange(0, N_ROWS)
            newv = rng.randrange(VAL_MIN, VAL_MAX)
            ops_a.append((idx, newv))

        for _ in range(M_EDITS_B):
            idx = rng.randrange(0, N_ROWS)
            newv = rng.randrange(VAL_MIN, VAL_MAX)
            ops_b.append((idx, newv))

        # WirePack canonicalization checks (idempotent + order-invariant)
        raw_a = encode_delta(ops_a)
        can_a = canonicalize_delta(raw_a)
        deltas_a_can.append(can_a)
        canon_idempotent_ok = canon_idempotent_ok and (canonicalize_delta(can_a) == can_a)

        raw_b = encode_delta(ops_b)
        can_b = canonicalize_delta(raw_b)
        deltas_b_can.append(can_b)
        canon_idempotent_ok = canon_idempotent_ok and (canonicalize_delta(can_b) == can_b)

        # order-invariance (shuffle ops, canonical form should match)
        ops_a_shuf = ops_a[:]
        rng.shuffle(ops_a_shuf)
        canon_stable_ok = canon_stable_ok and (canonicalize_delta(encode_delta(ops_a_shuf)) == can_a)

        ops_b_shuf = ops_b[:]
        rng.shuffle(ops_b_shuf)
        canon_stable_ok = canon_stable_ok and (canonicalize_delta(encode_delta(ops_b_shuf)) == can_b)

        # apply deltas incrementally (stream primitives): update only affected bucket
        for (idx, newv) in ops_a:
            buck = bucket_of(idx)
            oldc = contrib(a[idx], b[idx])
            newc = contrib(newv, b[idx])
            agg[buck] += (newc - oldc)
            a[idx] = newv

        for (idx, newv) in ops_b:
            buck = bucket_of(idx)
            oldc = contrib(a[idx], b[idx])
            newc = contrib(a[idx], newv)
            agg[buck] += (newc - oldc)
            b[idx] = newv

        # periodic semantic equivalence check vs snapshot recompute
        if (t + 1) % check_stride == 0:
            snap = snapshot_groupby_join(a, b)
            if snap != agg:
                query_ok = False
                break

    # wirepack streams + sizes
    ds_a = encode_delta_stream(deltas_a_can)
    ds_b = encode_delta_stream(deltas_b_can)

    raw_template_a_bytes = len(tmpl_a)
    raw_template_b_bytes = len(tmpl_b)
    raw_delta_a_bytes = len(ds_a)
    raw_delta_b_bytes = len(ds_b)

    gz_template_a_bytes = len(gzip.compress(tmpl_a, compresslevel=9))
    gz_template_b_bytes = len(gzip.compress(tmpl_b, compresslevel=9))
    gz_delta_a_bytes = len(gzip.compress(ds_a, compresslevel=9))
    gz_delta_b_bytes = len(gzip.compress(ds_b, compresslevel=9))

    final_a_sha256 = sha256_hex(stable_json(a))
    final_b_sha256 = sha256_hex(stable_json(b))
    result_sha256 = sha256_hex(stable_json(agg))

    receipt_obj = {
        "codec": "wirepack_v1",
        "seed": SEED,
        "n_rows": N_ROWS,
        "n_buckets": N_BUCKETS,
        "k_updates": K_UPDATES,
        "m_edits_a": M_EDITS_A,
        "m_edits_b": M_EDITS_B,
        "q_checks": Q_CHECKS,
        "canon_idempotent_ok": canon_idempotent_ok,
        "canon_stable_ok": canon_stable_ok,
        "query_ok": query_ok,
        "raw_template_a_bytes": raw_template_a_bytes,
        "raw_template_b_bytes": raw_template_b_bytes,
        "raw_delta_stream_a_bytes": raw_delta_a_bytes,
        "raw_delta_stream_b_bytes": raw_delta_b_bytes,
        "gz_template_a_bytes": gz_template_a_bytes,
        "gz_template_b_bytes": gz_template_b_bytes,
        "gz_delta_stream_a_bytes": gz_delta_a_bytes,
        "gz_delta_stream_b_bytes": gz_delta_b_bytes,
        "final_a_sha256": final_a_sha256,
        "final_b_sha256": final_b_sha256,
        "result_sha256": result_sha256,
        "template_a_sha256": sha256_hex(tmpl_a),
        "template_b_sha256": sha256_hex(tmpl_b),
        "delta_a_sha256": sha256_hex(ds_a),
        "delta_b_sha256": sha256_hex(ds_b),
    }
    drift_sha256 = sha256_hex(stable_json(receipt_obj))

    print("=== ✅ Bridge Benchmark v44: SQL subset translation (SELECT/WHERE/GROUP BY + simple JOIN) ===")
    print("v44_sql_subset_translation_wirepack")
    print(f"seed={SEED}")
    print(f"n_rows={N_ROWS} n_buckets={N_BUCKETS}")
    print(f"k_updates={K_UPDATES} m_edits_a={M_EDITS_A} m_edits_b={M_EDITS_B}")
    print(f"q_checks={Q_CHECKS}")
    print(f"canon_idempotent_ok={canon_idempotent_ok}")
    print(f"canon_stable_ok={canon_stable_ok}")
    print(f"query_ok={query_ok}")
    print(f"raw_template_a_bytes={raw_template_a_bytes}")
    print(f"raw_template_b_bytes={raw_template_b_bytes}")
    print(f"raw_delta_stream_a_bytes={raw_delta_a_bytes}")
    print(f"raw_delta_stream_b_bytes={raw_delta_b_bytes}")
    print(f"gz_template_a_bytes={gz_template_a_bytes}")
    print(f"gz_template_b_bytes={gz_template_b_bytes}")
    print(f"gz_delta_stream_a_bytes={gz_delta_a_bytes}")
    print(f"gz_delta_stream_b_bytes={gz_delta_b_bytes}")
    print(f"final_a_sha256={final_a_sha256}")
    print(f"final_b_sha256={final_b_sha256}")
    print(f"result_sha256={result_sha256}")
    print(f"drift_sha256={drift_sha256}")

    LEAN_OK = lean_check()
    print(f"\nLEAN_OK={LEAN_OK}\n")

    print("SHA256 (v44)\n")
    if LEAN_FILE.exists():
        print(f"{sha256_file(LEAN_FILE)}  {LEAN_FILE.as_posix()}")
    else:
        print(f"<missing>  {LEAN_FILE.as_posix()}")
    print(f"{sha256_file(THIS_FILE)}  {THIS_FILE.as_posix()}")

    assert query_ok, "SQL-subset semantics drifted vs snapshot recompute"
    if REQUIRE_LEAN:
        assert LEAN_OK == 1, "Lean bridge file must compile (lake env lean ...)"

    if UPDATE_LOCKS:
        LOCK_DIR.mkdir(parents=True, exist_ok=True)
        if not OUT_FILE.exists():
            raise RuntimeError(f"UPDATE_LOCKS=1 but missing out file: {OUT_FILE}")
        lean_sha = sha256_file(LEAN_FILE)
        out_sha = sha256_file(OUT_FILE)
        LOCK_SHA.write_text(
            f"{lean_sha}  backend/modules/lean/workspace/{LEAN_REL}\n"
            f"{out_sha}  backend/tests/locks/{OUT_FILE.name}\n",
            encoding="utf-8",
        )
        print(f"wrote {LOCK_SHA.as_posix()}", file=sys.stderr)


if __name__ == "__main__":
    main()