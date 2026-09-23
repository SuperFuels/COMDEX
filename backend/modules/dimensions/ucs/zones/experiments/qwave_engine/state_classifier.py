from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import numpy as np


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _phi_of(row: dict[str, Any]) -> float:
    return float(row.get("phi_hint", row.get("phi", math.nan)))


def _pickup_of(row: dict[str, Any]) -> float:
    if "pickup" in row:
        return float(row["pickup"])
    return float(row.get("pickup_mean", 0.0))


def _harmonic_of(row: dict[str, Any], default: int) -> int:
    h = row.get("harmonic", row.get("harmonics", default))
    if isinstance(h, list):
        if not h:
            return int(default)
        return int(h[0])
    return int(h)


def _alpha_of(row: dict[str, Any]) -> float:
    return float(row.get("alpha", row.get("alpha_hint", math.nan)))


def _nu_of(row: dict[str, Any]) -> float:
    return float(row.get("nu", row.get("nu_hint", math.nan)))


def _drift_of(row: dict[str, Any]) -> float:
    return float(row.get("drift", 0.0))


def _stability_of(row: dict[str, Any]) -> float:
    return float(row.get("stability", math.nan))


def _coherence_from_trace(row: dict[str, Any]) -> float:
    trace = row.get("pickup_trace", [])
    if not trace or len(trace) < 16:
        return 0.0

    x = np.asarray(trace, dtype=float)
    x = x - np.mean(x)
    win = np.hanning(x.size)
    spec = np.fft.rfft(x * win)
    mag = np.abs(spec)
    if mag.size:
        mag[0] = 0.0

    idx = np.argsort(mag)[::-1][:2]
    if len(idx) == 0:
        return 0.0

    top = mag[idx]
    denom = float(np.sum(top))
    return float(np.max(top) / denom) if denom > 0 else 0.0


def _normalize(vals: list[float]) -> list[float]:
    arr = np.asarray(vals, dtype=float)
    vmin = float(np.min(arr))
    vmax = float(np.max(arr))
    if vmax <= vmin:
        return [0.0 for _ in vals]
    return [float((x - vmin) / (vmax - vmin)) for x in arr]


def _circ_dist(a: float, b: float) -> float:
    d = abs((a - b) % (2.0 * math.pi))
    return min(d, 2.0 * math.pi - d)


def classify_s_state(phi: float, width: float) -> str:
    phi_mod = phi % (2.0 * math.pi)

    if _circ_dist(phi_mod, math.pi) <= width:
        return "S4_destructive"
    if _circ_dist(phi_mod, 0.0) <= width or _circ_dist(phi_mod, 2.0 * math.pi) <= width:
        return "S1_constructive"
    return "S2_intermediate"


def resonance_score(phi: float, harmonic: int) -> float:
    # still a heuristic; now uses row harmonic instead of a global fixed one
    return abs(math.cos(harmonic * phi / 2.0))


def classify_r_state(score: float) -> str:
    if score >= 0.90:
        return "R1_strong"
    if score >= 0.60:
        return "R2_moderate"
    if score >= 0.30:
        return "R3_weak"
    return "R4_none"


def classify_observed_regime(pickup_norm: float, coherence: float) -> str:
    if pickup_norm <= 0.15:
        amp = "A4_null"
    elif pickup_norm <= 0.45:
        amp = "A3_low"
    elif pickup_norm <= 0.75:
        amp = "A2_mid"
    else:
        amp = "A1_high"

    if coherence >= 0.95:
        coh = "C1_locked"
    elif coherence >= 0.75:
        coh = "C2_stable"
    elif coherence >= 0.50:
        coh = "C3_loose"
    else:
        coh = "C4_noisy"

    return f"{amp}_{coh}"


def combined_label(s_state: str, r_state: str, observed: str) -> str:
    return f"{s_state}__{r_state}__{observed}"


def run(args: argparse.Namespace) -> None:
    rows = _load_jsonl(Path(args.input))

    if not rows:
        raise SystemExit("No rows found in input JSONL.")

    pickups = [_pickup_of(r) for r in rows]
    pickup_norms = _normalize(pickups)

    print("\n=== STATE CLASSIFIER ===\n")
    print(f"input    : {args.input}")
    print(f"default h: {args.harmonic}")
    print()

    output_rows: list[dict[str, Any]] = []

    for row, pickup_norm in zip(rows, pickup_norms):
        phi = _phi_of(row)
        pickup = _pickup_of(row)
        harmonic = _harmonic_of(row, args.harmonic)
        alpha = _alpha_of(row)
        nu = _nu_of(row)
        drift = _drift_of(row)
        stability = _stability_of(row)
        coherence = _coherence_from_trace(row)

        s_state = classify_s_state(phi, args.state_width)
        r_score = resonance_score(phi, harmonic)
        r_state = classify_r_state(r_score)
        obs = classify_observed_regime(pickup_norm, coherence)
        label = combined_label(s_state, r_state, obs)

        out = {
            "phi": phi,
            "harmonic": harmonic,
            "alpha": alpha,
            "nu": nu,
            "pickup": pickup,
            "pickup_norm": pickup_norm,
            "coherence": coherence,
            "drift": drift,
            "stability": stability,
            "s_state": s_state,
            "r_score": r_score,
            "r_state": r_state,
            "observed_regime": obs,
            "combined_state": label,
        }
        output_rows.append(out)

        print(
            f"phi={phi:.6f} | "
            f"h={harmonic} | "
            f"alpha={alpha:.6f} | "
            f"nu={nu:.6f} | "
            f"pickup={pickup:.6f} | "
            f"pickup_norm={pickup_norm:.6f} | "
            f"coh={coherence:.6f} | "
            f"drift={drift:.6f} | "
            f"stability={stability:.6f} | "
            f"{label}"
        )

    payload = {
        "input": str(args.input),
        "default_harmonic": args.harmonic,
        "state_width": args.state_width,
        "row_count": len(output_rows),
        "rows": output_rows,
    }

    if args.json_out:
        out_path = Path(args.json_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"\nWrote JSON: {out_path}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description="Unified state classifier for Symatics phase + resonance + observed regime."
    )
    ap.add_argument("--input", required=True)
    ap.add_argument("--harmonic", type=int, default=4, help="Fallback harmonic if row has none.")
    ap.add_argument("--state-width", type=float, default=0.35)
    ap.add_argument(
        "--json-out",
        default="backend/modules/dimensions/ucs/zones/experiments/qwave_engine/outputs/state_classifier_latest.json",
    )
    run(ap.parse_args())