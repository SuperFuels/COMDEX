#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import hashlib
import statistics
import cmath
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

REPO_ROOT = Path("/workspaces/COMDEX")
SCENE_PATH = REPO_ROOT / "docs/Artifacts/VolVII/qfc/VOL7_PHASE_CLOSURE_PI.scene.json"
LEDGER_DIR = REPO_ROOT / "docs/Artifacts/VolVII/ledger"

TRACE_PATH = LEDGER_DIR / "VOL7_TRACE.jsonl"
METRICS_PATH = LEDGER_DIR / "VOL7_METRICS.json"
LOG_PATH = LEDGER_DIR / "VOL7_LINT_PROOF.log"


def _canon_json(obj: Any) -> str:
    # canonical JSON (byte-stable)
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def _sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _unwrap(dphi: float) -> float:
    # map into (-pi, pi]
    while dphi <= -math.pi:
        dphi += 2 * math.pi
    while dphi > math.pi:
        dphi -= 2 * math.pi
    return dphi


@dataclass(frozen=True)
class SceneParams:
    lock_id: str
    scene_id: str
    version: str
    steps: int
    dt: float
    seed: int
    ring_N: int


def _load_scene() -> Tuple[SceneParams, Dict[str, Any]]:
    scene = json.loads(SCENE_PATH.read_text(encoding="utf-8"))
    p = scene["params"]
    params = SceneParams(
        lock_id=scene["lock_id"],
        scene_id=scene["scene_id"],
        version=scene["version"],
        steps=int(p["steps"]),
        dt=float(p["dt"]),
        seed=int(p["seed"]),
        ring_N=int(p["ring_N"]),
    )
    return params, scene


def _simulate(params: SceneParams, schema: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    # Deterministic PRNG (Python's internal is stable enough for this fixed use-case,
    # but we avoid relying on numpy; also no floating RNG after initialization).
    import random
    rng = random.Random(params.seed)

    N = params.ring_N
    # initial phase ramp + tiny deterministic noise
    phi0 = [(2 * math.pi * i / N) + (rng.random() - 0.5) * 1e-3 for i in range(N)]
    z: List[complex] = [cmath.exp(1j * p) for p in phi0]

    events: List[Dict[str, Any]] = []

    for step in range(params.steps):
        # small deterministic phase drift
        drift = 1e-4 * math.sin(0.1 * step)

        new: List[complex] = []
        for i in range(N):
            left = z[(i - 1) % N]
            right = z[(i + 1) % N]
            w = 0.98 * z[i] + 0.01 * (left + right)
            w *= cmath.exp(1j * drift)
            if abs(w) == 0:
                w = 1 + 0j
            w /= abs(w)  # renormalize
            new.append(w)
        z = new

        phi = [cmath.phase(zi) for zi in z]

        dphi = [_unwrap(phi[(i + 1) % N] - phi[i]) for i in range(N)]
        integral = float(sum(dphi))
        winding_n = int(round(integral / (2 * math.pi))) if integral != 0.0 else 0
        closure_error = float(abs(integral - (2 * math.pi * winding_n)))

        # coherence: 1 - normalized std(dphi)
        std_dphi = statistics.pstdev(dphi)
        coherence = float(max(0.0, 1.0 - std_dphi / math.pi))

        pi_target = float(math.pi)
        pi_s = float(integral / (2 * winding_n)) if winding_n != 0 else float("nan")
        pi_err = float(abs(pi_s - pi_target)) if winding_n != 0 else float("nan")

        ts = float(step * params.dt)
        ctx = {"lock_id": params.lock_id, "scene_id": params.scene_id, "version": params.version, "seed": params.seed}

        events.append({
            "event_type": "phase_step",
            "ts": ts,
            "payload": {
                "step_idx": step,
                "dt": params.dt,
                "phi_summary": {"mean": float(statistics.fmean(phi)), "std": float(statistics.pstdev(phi))},
                "coherence": coherence,
            },
            "context": ctx,
        })
        events.append({
            "event_type": "closure_metric",
            "ts": ts,
            "payload": {
                "step_idx": step,
                "integral": integral,
                "winding_n": winding_n,
                "closure_error": closure_error,
            },
            "context": ctx,
        })
        events.append({
            "event_type": "pi_estimate",
            "ts": ts,
            "payload": {
                "step_idx": step,
                "pi_s": pi_s,
                "pi_err": pi_err,
                "pi_target": pi_target,
            },
            "context": ctx,
        })

    # schema checks
    required_top = set(schema["telemetry_schema"]["required_top_level_keys"])
    allowed_types = set(schema["telemetry_schema"]["event_type_enum"])
    required_fields_by_type = schema["telemetry_schema"]["required_fields_by_type"]

    present_types = set()
    for ev in events:
        if set(ev.keys()) != required_top:
            raise SystemExit(f"FAIL schema: top-level keys mismatch: got={sorted(ev.keys())} expected={sorted(required_top)}")
        et = ev["event_type"]
        if et not in allowed_types:
            raise SystemExit(f"FAIL schema: unexpected event_type={et}")
        present_types.add(et)

        req_fields = set(required_fields_by_type[et])
        payload_keys = set(ev["payload"].keys())
        missing = req_fields - payload_keys
        if missing:
            raise SystemExit(f"FAIL schema: event_type={et} missing payload keys={sorted(missing)}")

    missing_types = allowed_types - present_types
    if missing_types:
        raise SystemExit(f"FAIL schema: missing required event types: {sorted(missing_types)}")

    # metrics (final step)
    last_pi = [e for e in events if e["event_type"] == "pi_estimate"][-1]["payload"]
    last_cl = [e for e in events if e["event_type"] == "closure_metric"][-1]["payload"]
    last_coh = [e for e in events if e["event_type"] == "phase_step"][-1]["payload"]["coherence"]

    metrics = {
        "lock_id": params.lock_id,
        "scene_id": params.scene_id,
        "version": params.version,
        "seed": params.seed,
        "steps": params.steps,
        "dt": params.dt,
        "events": len(events),
        "winding_n_final": last_cl["winding_n"],
        "closure_error_final": last_cl["closure_error"],
        "pi_s_final": last_pi["pi_s"],
        "pi_err_final": last_pi["pi_err"],
        "coherence_final": last_coh,
    }
    return events, metrics


def _write_artifacts(events: List[Dict[str, Any]], metrics: Dict[str, Any]) -> str:
    LEDGER_DIR.mkdir(parents=True, exist_ok=True)

    # canonical JSONL trace
    lines = [_canon_json(ev) for ev in events]
    blob = ("\n".join(lines) + "\n").encode("utf-8")
    trace_sha256 = _sha256_bytes(blob)

    TRACE_PATH.write_bytes(blob)

    metrics_out = dict(metrics)
    metrics_out["trace_sha256"] = trace_sha256
    METRICS_PATH.write_text(_canon_json(metrics_out) + "\n", encoding="utf-8")

    # evidence log (human readable, deterministic content)
    log_lines = [
        f"[VOL7] lock_id={metrics['lock_id']} scene_id={metrics['scene_id']} version={metrics['version']}",
        f"[VOL7] steps={metrics['steps']} dt={metrics['dt']} seed={metrics['seed']}",
        f"[VOL7] events={metrics['events']}",
        f"[VOL7] winding_n_final={metrics['winding_n_final']}",
        f"[VOL7] closure_error_final={metrics['closure_error_final']}",
        f"[VOL7] pi_s_final={metrics['pi_s_final']}",
        f"[VOL7] pi_err_final={metrics['pi_err_final']}",
        f"[VOL7] coherence_final={metrics['coherence_final']}",
        f"[VOL7] trace_sha256={trace_sha256}",
        "[VOL7] determinism=PASS",
        "[VOL7] status=PASS",
        "",
    ]
    LOG_PATH.write_text("\n".join(log_lines), encoding="utf-8")

    return trace_sha256


def _determinism_check(params: SceneParams, scene: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    # run twice, compare trace digests
    events1, metrics1 = _simulate(params, scene)
    sha1 = _sha256_bytes(("\n".join(_canon_json(ev) for ev in events1) + "\n").encode("utf-8"))

    events2, metrics2 = _simulate(params, scene)
    sha2 = _sha256_bytes(("\n".join(_canon_json(ev) for ev in events2) + "\n").encode("utf-8"))

    if sha1 != sha2:
        raise SystemExit(f"FAIL determinism: sha1={sha1} sha2={sha2}")

    # ensure metrics are stable
    if _canon_json(metrics1) != _canon_json(metrics2):
        raise SystemExit("FAIL determinism: metrics mismatch between runs")

    # write artifacts from run #1
    trace_sha = _write_artifacts(events1, metrics1)
    return trace_sha, metrics1


def main() -> None:
    if not SCENE_PATH.exists():
        raise SystemExit(f"FAIL missing scene: {SCENE_PATH}")

    params, scene = _load_scene()
    trace_sha, metrics = _determinism_check(params, scene)

    print("PASS")
    print(f"trace_sha256={trace_sha}")
    print(f"[VOL7] lock_id={metrics['lock_id']} scene_id={metrics['scene_id']} version={metrics['version']}")
    print(f"[VOL7] steps={metrics['steps']} dt={metrics['dt']} seed={metrics['seed']}")
    print(f"[VOL7] events={metrics['events']}")
    print(f"[VOL7] winding_n_final={metrics['winding_n_final']}")
    print(f"[VOL7] closure_error_final={metrics['closure_error_final']}")
    print(f"[VOL7] pi_s_final={metrics['pi_s_final']}")
    print(f"[VOL7] pi_err_final={metrics['pi_err_final']}")
    print(f"[VOL7] coherence_final={metrics['coherence_final']}")
    print(f"[VOL7] status=PASS")
    # machine-readable metrics (single line)
    metrics_out = dict(metrics)
    metrics_out["trace_sha256"] = trace_sha
    print(_canon_json(metrics_out))


if __name__ == "__main__":
    main()
