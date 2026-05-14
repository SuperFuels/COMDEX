#!/usr/bin/env python3
"""
v43 — Multi-writer deterministic merge (CRDT-style, no materialization) [WirePack-backed]

Prints:
- merge verification metrics + drift_sha256
- LEAN_OK=1 if the Lean bridge compiles
- SHA256 lines for:
    - the Lean file (workspace canonical path)
    - this benchmark

Policy:
- Uses GlyphOS WirePack codec (encode_template/encode_delta/canonicalize_delta/encode_delta_stream).
- Lean compile check uses:
    backend/modules/lean/workspace/SymaticsBridge/V43_MultiWriterMergeNoMaterialization.lean
- If Lean fails, LEAN_OK=0 and the benchmark still succeeds unless REQUIRE_LEAN=1.
- If UPDATE_LOCKS=1:
    - writes backend/tests/locks/v43_multiwriter_merge_out.txt itself (NO tee needed)
    - writes backend/tests/locks/v43_multiwriter_merge_lock.sha256
      using sha256(Lean file) and sha256(locked out file).

IMPORTANT:
- Do NOT pipe to `tee` when UPDATE_LOCKS=1, otherwise you reintroduce a race.
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
from typing import Dict, List, Tuple

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

SEED = 43043
N_AGENTS = 8
N_ITEMS = 4096
K_UPDATES = 1024
M_EDITS = 4

VAL_MIN = -1_000_000
VAL_MAX = 1_000_000

REQUIRE_LEAN = os.environ.get("REQUIRE_LEAN", "1") == "1"
UPDATE_LOCKS = os.environ.get("UPDATE_LOCKS", "0") == "1"

# -------------------- sha / json helpers --------------------


def sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def stable_json(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


# -------------------- Lean check (workspace) --------------------

LEAN_REL = "SymaticsBridge/V43_MultiWriterMergeNoMaterialization.lean"
LEAN_WS = ROOT / "backend/modules/lean/workspace"
LEAN_FILE = LEAN_WS / LEAN_REL
THIS_FILE = Path(__file__).resolve()

LOCK_DIR = ROOT / "backend/tests/locks"
OUT_FILE = LOCK_DIR / "v43_multiwriter_merge_out.txt"
LOCK_SHA = LOCK_DIR / "v43_multiwriter_merge_lock.sha256"


def lean_check() -> int:
    if not LEAN_FILE.exists():
        return 0
    r = subprocess.run(
        ["lake", "env", "lean", LEAN_REL],
        cwd=str(LEAN_WS),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return 1 if r.returncode == 0 else 0


# -------------------- multi-writer model (WirePack deltas) --------------------

# We model "last-writer-wins" with a total order on writer-timestamp pairs.
# Each write sets a cell to (ts, value). Merge is pointwise max on ts.

TS = Tuple[int, int]  # (writer_id, counter)
Cell = Tuple[TS, int]  # ((wid, ctr), value)


def ts_gt(a: TS, b: TS) -> bool:
    return a > b  # lex order, deterministic


def apply_op(state: Dict[int, Cell], idx: int, ts: TS, value: int) -> None:
    cur = state.get(idx)
    if cur is None or ts_gt(ts, cur[0]):
        state[idx] = (ts, value)


def main() -> None:
    rng = random.Random(SEED)

    # base template: for WirePack, we keep a vector of ints (values only)
    base_vals: List[int] = [0 for _ in range(N_ITEMS)]
    template_bytes = encode_template(base_vals)

    # generate per-writer delta streams: each update is M_EDITS point writes
    canon_idempotent_ok = True
    canon_stable_ok = True

    per_writer_deltas: List[List[bytes]] = [[] for _ in range(N_AGENTS)]

    # also build two merge orders for the determinism check
    writer_ops: List[List[Tuple[int, int, int, int]]] = [[] for _ in range(N_AGENTS)]
    # tuple: (wid, ctr, idx, value)

    for wid in range(N_AGENTS):
        for ctr in range(K_UPDATES):
            ops: List[Tuple[int, int]] = []
            for _ in range(M_EDITS):
                idx = rng.randrange(0, N_ITEMS)
                val = rng.randrange(VAL_MIN, VAL_MAX)
                ops.append((idx, val))
                writer_ops[wid].append((wid, ctr, idx, val))

            d_raw_a = encode_delta(ops)
            d_can_a = canonicalize_delta(d_raw_a)

            # canonicalization checks: idempotent + order-stable
            ops_b = list(ops)
            rng.shuffle(ops_b)
            d_raw_b = encode_delta(ops_b)
            d_can_b = canonicalize_delta(d_raw_b)

            if canonicalize_delta(d_can_a) != d_can_a:
                canon_idempotent_ok = False
            if d_can_b != d_can_a:
                canon_stable_ok = False

            per_writer_deltas[wid].append(d_can_a)

    # merge in natural writer order
    s1: Dict[int, Cell] = {}
    for wid in range(N_AGENTS):
        for (w, ctr, idx, val) in writer_ops[wid]:
            apply_op(s1, idx, (w, ctr), val)

    # merge in shuffled writer order (determinism)
    s2: Dict[int, Cell] = {}
    writer_ids = list(range(N_AGENTS))
    random.Random(SEED + 99).shuffle(writer_ids)
    for wid in writer_ids:
        for (w, ctr, idx, val) in writer_ops[wid]:
            apply_op(s2, idx, (w, ctr), val)

    merge_ok = True
    if s1.keys() != s2.keys():
        merge_ok = False
    else:
        for k in s1.keys():
            if s1[k][1] != s2[k][1]:
                merge_ok = False
                break

    # wire sizes: concatenate per-writer delta streams (each already canonical)
    delta_streams = [encode_delta_stream(ds) for ds in per_writer_deltas]
    delta_stream_bytes = b"".join(delta_streams)

    raw_template = len(template_bytes)
    raw_ds = len(delta_stream_bytes)
    gz_template = len(gzip.compress(template_bytes, compresslevel=9))
    gz_ds = len(gzip.compress(delta_stream_bytes, compresslevel=9))

    # final state hash: stable json over (idx -> ((wid,ctr), value)) pairs
    # normalize ordering for determinism
    final_pairs = [(k, s1[k][0][0], s1[k][0][1], s1[k][1]) for k in sorted(s1.keys())]
    final_state_sha = sha256_hex(stable_json(final_pairs))

    receipt_obj = {
        "codec": "wirepack_v1",
        "seed": SEED,
        "n_agents": N_AGENTS,
        "n_items": N_ITEMS,
        "k_updates": K_UPDATES,
        "m_edits": M_EDITS,
        "canon_idempotent_ok": canon_idempotent_ok,
        "canon_stable_ok": canon_stable_ok,
        "merge_ok": merge_ok,
        "raw_template_bytes": raw_template,
        "raw_delta_stream_bytes": raw_ds,
        "gz_template_bytes": gz_template,
        "gz_delta_stream_bytes": gz_ds,
        "final_state_sha256": final_state_sha,
        "template_sha256": sha256_hex(template_bytes),
        "deltas_sha256": sha256_hex(delta_stream_bytes),
    }
    drift_sha256 = sha256_hex(stable_json(receipt_obj))

    # build deterministic stdout (and optionally persist it) to avoid tee races
    out_lines: List[str] = []
    a = out_lines.append

    a("=== ✅ Bridge Benchmark v43: Multi-writer deterministic merge (CRDT-style) ===")
    a("v43_multiwriter_merge_wirepack")
    a(f"seed={SEED}")
    a(f"n_agents={N_AGENTS} n_items={N_ITEMS} k_updates={K_UPDATES} m_edits={M_EDITS}")
    a(f"canon_idempotent_ok={canon_idempotent_ok}")
    a(f"canon_stable_ok={canon_stable_ok}")
    a(f"merge_ok={merge_ok}")
    a(f"raw_template_bytes={raw_template}")
    a(f"raw_delta_stream_bytes={raw_ds}")
    a(f"gz_template_bytes={gz_template}")
    a(f"gz_delta_stream_bytes={gz_ds}")
    a(f"final_state_sha256={final_state_sha}")
    a(f"drift_sha256={drift_sha256}")
    a("")
    LEAN_OK = lean_check()
    a(f"LEAN_OK={LEAN_OK}")
    a("")
    a("SHA256 (v43)")
    a("")
    if LEAN_FILE.exists():
        a(f"{sha256_file(LEAN_FILE)}  {LEAN_FILE.as_posix()}")
    else:
        a(f"<missing>  {LEAN_FILE.as_posix()}")
    a(f"{sha256_file(THIS_FILE)}  {THIS_FILE.as_posix()}")

    out_text = "\n".join(out_lines) + "\n"

    if UPDATE_LOCKS:
        LOCK_DIR.mkdir(parents=True, exist_ok=True)
        OUT_FILE.write_text(out_text, encoding="utf-8")

    sys.stdout.write(out_text)
    sys.stdout.flush()

    # assertions
    assert canon_idempotent_ok, "canon must be idempotent"
    assert canon_stable_ok, "canon must erase op-order nondeterminism"
    assert merge_ok, "merge must be deterministic (order-independent)"

    if REQUIRE_LEAN:
        assert LEAN_OK == 1, "Lean bridge file must compile (lake env lean ...)"

    if UPDATE_LOCKS:
        lean_sha = sha256_file(LEAN_FILE)
        out_sha = sha256_text(out_text)
        LOCK_SHA.write_text(
            f"{lean_sha}  backend/modules/lean/workspace/{LEAN_REL}\n"
            f"{out_sha}  backend/tests/locks/{OUT_FILE.name}\n",
            encoding="utf-8",
        )
        print(f"wrote {LOCK_SHA.as_posix()}", file=sys.stderr)


if __name__ == "__main__":
    main()
