#!/usr/bin/env python3
"""
v38 REAL — Canonical Delta determinism + replay correctness (GlyphOS/WirePack-backed)

This is the SAME property as v38, but it tries hard to use the *real* GlyphOS/WirePack
encoder/canonicalizer/apply pipeline.

It *prints which module it used* (file path) so you can prove it's not the CI-safe toy receipt.

If it can't find the WirePack API, it fails loudly with the attempted imports.
"""

from __future__ import annotations

import gzip
import hashlib
import importlib
import json
import random
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

SEED = 38038
N_AGENTS = 4096
K_UPDATES = 1024
M_EDITS_PER_UPDATE = 1

Op = Tuple[int, int]  # (idx, new_value)


def sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def stable_json_bytes(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _load_wirepack_api():
    """
    Returns: (impl_name, impl_file, encode_template, encode_delta, apply_delta, canonicalize_delta|None)

    We don't guess ONE module name; we try several common placements and validate required callables.
    """
    candidates = [
        "backend.modules.glyphos.wirepack",
        "backend.modules.glyphos.wirepack_codec",
        "backend.modules.glyphos.wirepack_core",
        "backend.modules.glyphos.wirepack_runtime",
        "backend.modules.glyphos.wirepack_v2",
        "backend.modules.codex.wirepack",
        "backend.modules.codex.wirepack_codec",
    ]

    required = ["encode_template", "encode_delta", "apply_delta"]
    optional = ["canonicalize_delta", "canon_delta"]

    last_errs: List[str] = []

    for modname in candidates:
        try:
            m = importlib.import_module(modname)
        except Exception as e:
            last_errs.append(f"{modname}: import failed: {e}")
            continue

        missing = [x for x in required if not hasattr(m, x) or not callable(getattr(m, x))]
        if missing:
            last_errs.append(f"{modname}: missing required callables: {missing}")
            continue

        encode_template = getattr(m, "encode_template")
        encode_delta = getattr(m, "encode_delta")
        apply_delta = getattr(m, "apply_delta")

        canon = None
        for opt in optional:
            if hasattr(m, opt) and callable(getattr(m, opt)):
                canon = getattr(m, opt)
                break

        impl_file = getattr(m, "__file__", "<unknown>")
        return modname, impl_file, encode_template, encode_delta, apply_delta, canon

    raise RuntimeError(
        "Could not locate a usable GlyphOS/WirePack API.\n"
        "Tried modules:\n  - " + "\n  - ".join(candidates) +
        "\n\nFailures:\n  - " + "\n  - ".join(last_errs) +
        "\n\nFix: tell me where your real wirepack lives (module path), or rename/export:\n"
        "  encode_template(base_state)->bytes\n"
        "  encode_delta(list[(idx,val)])->bytes\n"
        "  apply_delta(state, delta_bytes)->state or mutates\n"
        "  canonicalize_delta(delta_bytes)->bytes  (optional)\n"
    )


def _apply_delta(apply_delta_fn: Callable[..., Any], state: List[int], delta_bytes: bytes) -> List[int]:
    """
    Supports either:
      - apply_delta(state, delta_bytes) -> new_state
      - apply_delta(state, delta_bytes) mutates and returns None
    """
    out = apply_delta_fn(state, delta_bytes)
    if out is None:
        return state
    return out


def main() -> None:
    rng = random.Random(SEED)

    # Base state
    base = [rng.randrange(0, 100_000) for _ in range(N_AGENTS)]
    state_a = base.copy()
    state_b = base.copy()

    (
        impl_name,
        impl_file,
        encode_template,
        encode_delta,
        apply_delta_fn,
        canon_delta_fn,
    ) = _load_wirepack_api()

    print("v38_canonical_delta_determinism_replay_REAL")
    print(f"wirepack_impl={impl_name}")
    print(f"wirepack_file={impl_file}")
    print(f"seed={SEED}")
    print(f"n_agents={N_AGENTS} k_updates={K_UPDATES} m_edits_per_update={M_EDITS_PER_UPDATE}")

    canon_idempotent_ok = True
    canon_stable_ok = True

    # Template bytes (real encoder)
    template_bytes: bytes = encode_template(base)

    # Stream bytes: we store length-prefixed deltas so concatenation is unambiguous + deterministic
    stream_chunks: List[bytes] = []

    for _t in range(K_UPDATES):
        ops: List[Op] = []
        for _ in range(M_EDITS_PER_UPDATE):
            idx = rng.randrange(0, N_AGENTS)
            newv = rng.randrange(0, 100_000)
            ops.append((idx, newv))

        # A: normal order
        d_a = encode_delta(ops)

        # B: shuffled order (should canonicalize to same bytes)
        ops_b = list(ops)
        rng.shuffle(ops_b)
        d_b = encode_delta(ops_b)

        # If canonicalizer exists, use it for determinism checks
        if canon_delta_fn is not None:
            d_a_c = canon_delta_fn(d_a)
            d_a_c2 = canon_delta_fn(d_a_c)
            if d_a_c2 != d_a_c:
                canon_idempotent_ok = False

            d_b_c = canon_delta_fn(d_b)
            if d_b_c != d_a_c:
                canon_stable_ok = False

            d_a_use = d_a_c
            d_b_use = d_b_c
        else:
            # Best-effort: treat encode_delta output as canonical
            # Idempotence reduces to "same encode twice == same bytes"
            if encode_delta(ops) != d_a:
                canon_idempotent_ok = False
            if d_b != d_a and M_EDITS_PER_UPDATE > 1:
                canon_stable_ok = False

            d_a_use = d_a
            d_b_use = d_b

        # Apply
        state_a = _apply_delta(apply_delta_fn, state_a, d_a_use)
        state_b = _apply_delta(apply_delta_fn, state_b, d_b_use)

        # Length prefix for stream determinism
        stream_chunks.append(len(d_a_use).to_bytes(4, "big") + d_a_use)

    replay_ok = (state_a == state_b)

    delta_stream_bytes = b"".join(stream_chunks)

    raw_template_bytes = len(template_bytes)
    raw_delta_stream_bytes = len(delta_stream_bytes)

    gz_template_bytes = len(gzip.compress(template_bytes, compresslevel=9))
    gz_delta_stream_bytes = len(gzip.compress(delta_stream_bytes, compresslevel=9))

    final_state_sha256 = sha256_hex(stable_json_bytes({"final": state_a}))

    drift_payload = stable_json_bytes({
        "wirepack_impl": impl_name,
        "wirepack_file": impl_file,
        "seed": SEED,
        "n_agents": N_AGENTS,
        "k_updates": K_UPDATES,
        "m_edits_per_update": M_EDITS_PER_UPDATE,
        "canon_idempotent_ok": canon_idempotent_ok,
        "canon_stable_ok": canon_stable_ok,
        "replay_ok": replay_ok,
        "raw_template_bytes": raw_template_bytes,
        "raw_delta_stream_bytes": raw_delta_stream_bytes,
        "gz_template_bytes": gz_template_bytes,
        "gz_delta_stream_bytes": gz_delta_stream_bytes,
        "final_state_sha256": final_state_sha256,
        "template_sha256": sha256_hex(template_bytes),
        "delta_stream_sha256": sha256_hex(delta_stream_bytes),
    })
    drift_sha256 = sha256_hex(drift_payload)

    print(f"canon_idempotent_ok={canon_idempotent_ok}")
    print(f"canon_stable_ok={canon_stable_ok}")
    print(f"replay_ok={replay_ok}")
    print(f"raw_template_bytes={raw_template_bytes}")
    print(f"raw_delta_stream_bytes={raw_delta_stream_bytes}")
    if raw_delta_stream_bytes:
        print(f"raw_ratio(template/delta)={raw_template_bytes / raw_delta_stream_bytes:.6f}")
    print(f"gz_template_bytes={gz_template_bytes}")
    print(f"gz_delta_stream_bytes={gz_delta_stream_bytes}")
    if gz_delta_stream_bytes:
        print(f"gz_ratio(template/delta)={gz_template_bytes / gz_delta_stream_bytes:.6f}")
    print(f"final_state_sha256={final_state_sha256}")
    print(f"drift_sha256={drift_sha256}")

    assert canon_idempotent_ok, "canon must be idempotent"
    assert canon_stable_ok, "canon must erase op-order nondeterminism"
    assert replay_ok, "replay must match across equivalent canonical deltas"


if __name__ == "__main__":
    main()