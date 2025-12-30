#!/usr/bin/env python3
import json
import os
import time
import hashlib
import random
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

ART_ROOT = "/workspaces/COMDEX/docs/Artifacts/vol5_delta_telemetry"
SCENE_PATH = os.path.join(ART_ROOT, "qfc", "VOL5_DELTA_TELEMETRY.scene.json")
THRESH_PATH = os.path.join(ART_ROOT, "build", "VOL5_ACCEPTANCE_THRESHOLDS.yaml")

TRACE_PATH = os.path.join(ART_ROOT, "V5_TRACE.jsonl")
METRICS_PATH = os.path.join(ART_ROOT, "V5_METRICS.json")
LOG_PATH = os.path.join(ART_ROOT, "V5_LINT_PROOF.log")

SCHEMA_PATH = os.path.join(ART_ROOT, "artifacts", "V5_EVENT_SCHEMA.json")


def canonical_json(obj: Any) -> str:
    # Byte-stable JSON: sort keys + compact separators + no floats formatting tricks beyond python std
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def read_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def read_yaml_minimal(path: str) -> Dict[str, Any]:
    # Minimal YAML reader sufficient for our threshold file (key: value, lists, simple scalars).
    # Avoid adding new deps; keep deterministic and portable.
    out: Dict[str, Any] = {}
    cur_key = None
    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if ":" in line and not line.startswith("-"):
                k, v = line.split(":", 1)
                k = k.strip()
                v = v.strip()
                cur_key = k
                if v == "":
                    out[k] = []
                elif v.startswith("[") and v.endswith("]"):
                    # very small list form: [a, b]
                    inner = v[1:-1].strip()
                    parts = [p.strip() for p in inner.split(",")] if inner else []
                    # convert numeric
                    parsed = []
                    for p in parts:
                        if p.lower() in ("true", "false"):
                            parsed.append(p.lower() == "true")
                        else:
                            try:
                                parsed.append(float(p) if "." in p else int(p))
                            except Exception:
                                parsed.append(p.strip('"').strip("'"))
                    out[k] = parsed
                else:
                    if v.lower() in ("true", "false"):
                        out[k] = (v.lower() == "true")
                    else:
                        try:
                            out[k] = float(v) if "." in v else int(v)
                        except Exception:
                            out[k] = v.strip('"').strip("'")
            elif line.startswith("-") and cur_key is not None:
                item = line[1:].strip()
                out[cur_key].append(item.strip('"').strip("'"))
            else:
                raise ValueError(f"Unsupported YAML line: {raw}")
    return out


@dataclass
class RunResult:
    trace_lines: List[str]
    trace_sha256: str
    metrics: Dict[str, Any]


def validate_event_schema(event: Dict[str, Any], schema: Dict[str, Any]) -> None:
    for k in schema["required_top_level_keys"]:
        if k not in event:
            raise AssertionError(f"missing top-level key: {k}")

    et = event["event_type"]
    if et not in schema["event_type_enum"]:
        raise AssertionError(f"unknown event_type: {et}")

    req_fields = schema["required_fields_by_type"][et]
    payload = event["payload"]
    for f in req_fields:
        if f not in payload:
            raise AssertionError(f"event_type={et} missing payload field: {f}")


def simulate(scene: Dict[str, Any], schema: Dict[str, Any]) -> RunResult:
    seed = int(scene["seed"])
    rng = random.Random(seed)

    steps = int(scene["steps"])
    dt = float(scene["dt"])
    eta = float(scene["eta"])
    gamma = float(scene["gamma"])
    kappa = float(scene["kappa"])
    law_ids = list(scene["law_ids"])

    # Simple deterministic state (non-physics; telemetry contract exercise)
    lambdas = {law_id: 1.0 for law_id in law_ids}
    psi_norm = 1.0
    coherence = 0.95
    E = 1.0

    trace_lines: List[str] = []
    ts0 = 1735516800.0  # fixed epoch anchor for byte-stable timestamps

    def emit(event_type: str, payload: Dict[str, Any], context: Dict[str, Any]) -> None:
        ev = {
            "event_type": event_type,
            "ts": ts0 + float(payload.get("step_idx", 0)) * dt,
            "payload": payload,
            "context": context,
        }
        validate_event_schema(ev, schema)
        trace_lines.append(canonical_json(ev))

    for step_idx in range(steps):
        # --- law weight update (λ) ---
        law_id = law_ids[step_idx % len(law_ids)]
        prev = lambdas[law_id]
        # deterministic delta with bounded pseudo-noise
        drift = (0.001 * (step_idx + 1)) + (rng.random() - 0.5) * 0.0002
        delta = -eta * drift
        new = prev + delta
        lambdas[law_id] = new

        emit(
            "law_weight_update",
            {
                "law_id": law_id,
                "prev_weight": prev,
                "new_weight": new,
                "delta": delta
            },
            {"module": "vol5", "phase": "lambda_update"}
        )

        # --- wave step (ψ) ---
        lambda_mean = sum(lambdas.values()) / len(lambdas)
        laplacian_mean = -gamma * psi_norm + 0.01 * (lambda_mean - 1.0)
        psi_norm = max(0.0, psi_norm + dt * laplacian_mean)

        # coherence is clamped (purely telemetry sanity)
        coherence = max(0.0, min(1.0, coherence + (rng.random() - 0.5) * 0.0005 - 0.0001))

        emit(
            "wave_step",
            {
                "step_idx": step_idx,
                "dt": dt,
                "psi_summary": {"norm": psi_norm, "laplacian_mean": laplacian_mean},
                "coherence": coherence,
                "lambda_summary": {"mean": lambda_mean}
            },
            {"module": "vol5", "phase": "psi_step"}
        )

        # --- energy metric (E) ---
        prevE = E
        E = max(0.0, E * (1.0 - kappa * dt) + 0.0005 * psi_norm)
        dE = E - prevE

        emit(
            "energy_metric",
            {"E": E, "dE": dE},
            {"module": "vol5", "phase": "energy"}
        )

        # --- feedback apply (E -> λ) ---
        # feedback signal: small correction proportional to dE (purely demonstrative)
        fb = -0.1 * dE
        target_law = law_ids[(step_idx + 1) % len(law_ids)]
        prev2 = lambdas[target_law]
        new2 = prev2 + fb
        lambdas[target_law] = new2

        emit(
            "feedback_apply",
            {
                "source": "energy_metric",
                "target": target_law,
                "delta_rule": "dE_to_dlambda",
                "delta_value": fb
            },
            {"module": "vol5", "phase": "feedback"}
        )

    trace_blob = ("\n".join(trace_lines) + "\n").encode("utf-8")
    trace_sha = sha256_bytes(trace_blob)

    metrics = {
        "lock_id": scene["lock_id"],
        "scene_id": scene["scene_id"],
        "version": scene["version"],
        "seed": seed,
        "steps": steps,
        "dt": dt,
        "trace_sha256": trace_sha,
        "events": len(trace_lines),
        "lambda_final_mean": sum(lambdas.values()) / len(lambdas),
        "coherence_final": coherence,
        "E_final": E
    }
    return RunResult(trace_lines=trace_lines, trace_sha256=trace_sha, metrics=metrics)


def main() -> int:
    os.makedirs(ART_ROOT, exist_ok=True)

    scene = read_json(SCENE_PATH)
    schema = read_json(SCHEMA_PATH)
    thr = read_yaml_minimal(THRESH_PATH)

    # Run twice and require determinism (byte-stable trace)
    r1 = simulate(scene, schema)
    r2 = simulate(scene, schema)

    required_types = set(thr.get("required_event_types", []))
    min_steps = int(thr.get("min_steps", 10))
    max_steps = int(thr.get("max_steps", 10**9))
    require_det = bool(thr.get("require_determinism", True))

    # Basic checks
    steps = int(scene["steps"])
    if not (min_steps <= steps <= max_steps):
        raise AssertionError(f"steps out of range: {steps} (min={min_steps}, max={max_steps})")

    if require_det and r1.trace_sha256 != r2.trace_sha256:
        raise AssertionError(f"determinism failed: sha1={r1.trace_sha256} sha2={r2.trace_sha256}")

    # Verify required event types are present
    seen = set()
    for line in r1.trace_lines:
        ev = json.loads(line)
        seen.add(ev["event_type"])
    missing = sorted(list(required_types - seen))
    if missing:
        raise AssertionError(f"missing required event types: {missing}")

    # Numeric guardrails
    coh_lo, coh_hi = thr.get("coherence_range", [0.0, 1.0])
    if not (float(coh_lo) <= float(r1.metrics["coherence_final"]) <= float(coh_hi)):
        raise AssertionError("coherence_final out of range")

    if bool(thr.get("energy_nonnegative", True)) and float(r1.metrics["E_final"]) < 0.0:
        raise AssertionError("E_final is negative")

    # Write artifacts (trace is canonical JSONL)
    with open(TRACE_PATH, "w", encoding="utf-8") as f:
        for line in r1.trace_lines:
            f.write(line + "\n")

    with open(METRICS_PATH, "w", encoding="utf-8") as f:
        f.write(canonical_json(r1.metrics) + "\n")

    # Evidence log
    now = "2025-12-30T00:00:00Z"
    log_lines = [
        f"[VOL5] lock_id={scene['lock_id']} scene_id={scene['scene_id']} version={scene['version']}",
        f"[VOL5] timestamp={now}",
        f"[VOL5] steps={scene['steps']} dt={scene['dt']} seed={scene['seed']}",
        f"[VOL5] events={r1.metrics['events']}",
        f"[VOL5] trace_sha256={r1.metrics['trace_sha256']}",
        f"[VOL5] determinism={'PASS' if (not require_det or r1.trace_sha256 == r2.trace_sha256) else 'FAIL'}",
        f"[VOL5] required_event_types_present=PASS",
        f"[VOL5] status=PASS"
    ]
    with open(LOG_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(log_lines) + "\n")

    print("PASS")
    print(f"trace_sha256={r1.metrics['trace_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
