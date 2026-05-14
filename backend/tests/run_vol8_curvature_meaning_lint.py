#!/usr/bin/env python3
"""
Vol VIII lint runner (skeleton).
Contract:
- Loads the VolVIII scene card
- Executes a deterministic scene driver (to be implemented) producing events
- Canonical-normalizes JSON and writes VOL8_TRACE.jsonl
- Writes VOL8_METRICS.json + VOL8_LINT_PROOF.log
- Computes trace_sha256 and asserts determinism gates

NOTE: This file is a skeleton to match the Vol0/Vol5/Vol7 patterns.
Replace `run_scene_generate_events()` with your actual engine hook.
"""
from __future__ import annotations

import json
import hashlib
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List

REPO = "/workspaces/COMDEX"

SCENE_PATH = f"{REPO}/docs/Artifacts/VolVIII/qfc/VOL8_CURVATURE_MEANING.scene.json"
OUT_DIR = f"{REPO}/docs/Artifacts/VolVIII/ledger"
LOG_PATH = f"{OUT_DIR}/VOL8_LINT_PROOF.log"
METRICS_PATH = f"{OUT_DIR}/VOL8_METRICS.json"
TRACE_PATH = f"{OUT_DIR}/VOL8_TRACE.jsonl"

THRESH_PATH = f"{REPO}/docs/Artifacts/VolVIII/build/VOLVIII_ACCEPTANCE_THRESHOLDS.yaml"


def canonical_json_dumps(obj: Any) -> str:
    # IMPORTANT: byte-stable normalization
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_scene() -> Dict[str, Any]:
    with open(SCENE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def ensure_dirs() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)


def run_scene_generate_events(scene: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    TODO: Replace with your actual Vol VIII scene driver.
    Must return a list of event dicts with top-level:
      event_type, ts, payload, context
    """
    seed = int(scene["seed"])
    dt = float(scene["dt"])
    steps = int(scene["steps"])

    # Deterministic placeholder stream (DO NOT KEEP for lock):
    # Generates 3 events per step: wave_step, energy_metric, feedback_apply
    events: List[Dict[str, Any]] = []
    E = 1.0
    coherence = 1.0
    for step_idx in range(steps):
        # simple deterministic drift
        dE = -0.0001 * (step_idx + 1)
        E = E + dE
        coherence = max(0.0, 1.0 - 1e-6 * (step_idx + 1))

        base_context = {
            "scene_id": scene["scene_id"],
            "lock_id": scene["lock_id"],
            "version": scene["version"],
            "seed": seed,
        }

        events.append({
            "event_type": "wave_step",
            "ts": step_idx * dt,
            "payload": {
                "step_idx": step_idx,
                "dt": dt,
                "psi_summary": {"N": scene["model"]["N"], "manifold": scene["model"]["manifold"]},
                "coherence": coherence,
                "lambda_summary": {"lambda_mean": 1.0},
            },
            "context": base_context,
        })

        events.append({
            "event_type": "energy_metric",
            "ts": step_idx * dt,
            "payload": {"E": E, "dE": dE},
            "context": base_context,
        })

        events.append({
            "event_type": "feedback_apply",
            "ts": step_idx * dt,
            "payload": {"source": "coherence", "target": "self_loop", "delta_rule": "noop", "delta_value": 0.0},
            "context": base_context,
        })

    return events


def validate_contract(scene: Dict[str, Any], events: List[Dict[str, Any]]) -> None:
    contract = scene["telemetry_contract"]
    required_top = set(contract["required_top_level_keys"])
    allowed_types = set(contract["event_type_enum"])
    required_by_type = contract["required_fields_by_type"]

    found_types = set()

    for e in events:
        if not required_top.issubset(set(e.keys())):
            missing = sorted(required_top - set(e.keys()))
            raise AssertionError(f"Event missing top-level keys: {missing}")

        et = e["event_type"]
        if et not in allowed_types:
            raise AssertionError(f"Unexpected event_type={et}")

        found_types.add(et)
        payload = e["payload"]
        req_fields = required_by_type.get(et, [])
        for f in req_fields:
            if f not in payload:
                raise AssertionError(f"Event type {et} missing payload field {f}")

    if not allowed_types.issubset(found_types):
        missing_types = sorted(allowed_types - found_types)
        raise AssertionError(f"Missing required event types: {missing_types}")


def write_trace(events: List[Dict[str, Any]]) -> None:
    with open(TRACE_PATH, "w", encoding="utf-8") as f:
        for e in events:
            f.write(canonical_json_dumps(e) + "\n")


def main() -> int:
    ensure_dirs()
    scene = load_scene()

    events = run_scene_generate_events(scene)
    validate_contract(scene, events)
    write_trace(events)

    trace_sha256 = sha256_file(TRACE_PATH)

    # Minimal derived metrics (tighten once real scene implemented)
    coherence_final = float(events[-3]["payload"]["coherence"])  # last wave_step
    closure_error_final = 0.0  # placeholder; real scene must compute this
    pi_s_final = 3.141592653589793  # placeholder; real scene may record/reuse this

    metrics = {
        "lock_id": scene["lock_id"],
        "scene_id": scene["scene_id"],
        "version": scene["version"],
        "timestamp": scene.get("timestamp_utc", datetime.now(timezone.utc).isoformat()),
        "seed": scene["seed"],
        "dt": scene["dt"],
        "steps": scene["steps"],
        "events": len(events),
        "coherence_final": coherence_final,
        "closure_error_final": closure_error_final,
        "pi_s_final": pi_s_final,
        "trace_sha256": trace_sha256,
        "status": "PASS",
    }

    with open(METRICS_PATH, "w", encoding="utf-8") as f:
        f.write(json.dumps(metrics, indent=2, sort_keys=True) + "\n")

    with open(LOG_PATH, "w", encoding="utf-8") as f:
        f.write("PASS\n")
        f.write(f"trace_sha256={trace_sha256}\n")
        f.write(f"[VOL8] lock_id={scene['lock_id']} scene_id={scene['scene_id']} version={scene['version']}\n")
        f.write(f"[VOL8] steps={scene['steps']} dt={scene['dt']} seed={scene['seed']}\n")
        f.write(f"[VOL8] events={len(events)}\n")
        f.write(f"[VOL8] coherence_final={coherence_final}\n")
        f.write(f"[VOL8] closure_error_final={closure_error_final}\n")
        f.write(f"[VOL8] pi_s_final={pi_s_final}\n")
        f.write(f"[VOL8] status=PASS\n")

    # stdout summary (match other lints)
    print("PASS")
    print(f"trace_sha256={trace_sha256}")
    print(f"[VOL8] lock_id={scene['lock_id']} scene_id={scene['scene_id']} version={scene['version']}")
    print(f"[VOL8] steps={scene['steps']} dt={scene['dt']} seed={scene['seed']}")
    print(f"[VOL8] events={len(events)}")
    print(f"[VOL8] coherence_final={coherence_final}")
    print(f"[VOL8] closure_error_final={closure_error_final}")
    print(f"[VOL8] pi_s_final={pi_s_final}")
    print(f"[VOL8] status=PASS")
    print(json.dumps(metrics, sort_keys=True))

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        os.makedirs(OUT_DIR, exist_ok=True)
        with open(LOG_PATH, "w", encoding="utf-8") as f:
            f.write("FAIL\n")
            f.write(str(e) + "\n")
        print("FAIL")
        print(str(e))
        sys.exit(1)
