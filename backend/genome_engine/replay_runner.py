from __future__ import annotations

from typing import Any, Dict
import argparse
import json

from .gx1_builder import build_gx1_payload, stable_hash
from .schema_validate import validate_or_raise
from backend.utils.log_gate import tprint


def verify_replay_bundle(replay_path: str) -> Dict[str, Any]:
    with open(replay_path, "r", encoding="utf-8") as f:
        bundle = json.load(f)

    validate_or_raise("gx1_replay_bundle.schema.json", bundle)

    cfg = dict(bundle.get("config") or {})
    if not cfg:
        raise ValueError("Replay bundle missing config")

    # Recompute (SIM only for now)
    payload = build_gx1_payload(cfg)
    replay2 = payload["replay_bundle"]

    # Prefer contract digests if present
    d1 = bundle.get("trace_digest")
    d2 = replay2.get("trace_digest")

    ok = True
    reasons = []

    if d1 is not None and d2 is not None and str(d1) != str(d2):
        ok = False
        reasons.append(f"trace_digest mismatch: {d1} != {d2}")

    # Also compare metrics deterministically (hash compare avoids noisy diffs)
    m1 = bundle.get("metrics")
    m2 = replay2.get("metrics")
    if m1 is not None and m2 is not None:
        h1 = stable_hash(m1)
        h2 = stable_hash(m2)
        if h1 != h2:
            ok = False
            reasons.append("metrics hash mismatch")

    return {
        "ok": ok,
        "reasons": reasons,
        "run_id": payload["run_id"],
        "mode": payload["mode"],
        "trace_digest_bundle": d1,
        "trace_digest_recomputed": d2,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--replay", required=True, help="Path to REPLAY_BUNDLE.json")
    args = ap.parse_args()

    r = verify_replay_bundle(args.replay)
    if r["ok"]:
        tprint(f"✅ REPLAY verify OK: run_id={r['run_id']} mode={r['mode']}")
        return
    tprint(f"❌ REPLAY verify FAIL: run_id={r['run_id']} mode={r['mode']}")
    for x in r["reasons"]:
        tprint(f"   - {x}")
    raise SystemExit(2)


if __name__ == "__main__":
    main()
