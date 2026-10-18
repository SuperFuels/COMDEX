from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import numpy as np


def _state_from_phi(phi: float, state_width: float) -> str:
    phi_mod = phi % (2.0 * math.pi)

    def circ_dist(a: float, b: float) -> float:
        d = abs(a - b) % (2.0 * math.pi)
        return min(d, 2.0 * math.pi - d)

    if circ_dist(phi_mod, math.pi) <= state_width:
        return "S4_destructive"
    if circ_dist(phi_mod, 0.0) <= state_width or circ_dist(phi_mod, 2.0 * math.pi) <= state_width:
        return "S1_constructive"
    return "S2_intermediate"


def predict_point(phi: float, harmonic: int, alpha: float, nu: float, *, state_width: float) -> dict[str, Any]:
    cos2 = float(math.cos(phi / 2.0) ** 2)

    # Current sim evidence suggests this broad-sweep regime is dominated by phase.
    # Keep the alpha/nu/harmonic modifiers intentionally small and explicit.
    harmonic_weight = {3: 0.97, 4: 1.00, 5: 1.03}.get(harmonic, 1.00)
    alpha_penalty = max(0.0, abs(alpha - 0.080)) * 0.0
    nu_penalty = max(0.0, abs(nu - 0.020)) * 0.0

    pickup_norm = min(1.0, max(0.0, cos2 * harmonic_weight - alpha_penalty - nu_penalty))
    state = _state_from_phi(phi, state_width)

    # map normalized prediction into rough observed band from current h=4 broad-sweep data
    pickup_min = 0.278135019
    pickup_max = 0.990601248
    pickup_est = pickup_min + (pickup_max - pickup_min) * pickup_norm

    # rough expected coherence heuristic from current sim outputs
    if state == "S4_destructive":
        expected_coherence = 0.58
    elif state == "S1_constructive":
        expected_coherence = 0.97
    else:
        expected_coherence = 0.94

    return {
        "phi": phi,
        "harmonic": harmonic,
        "alpha": alpha,
        "nu": nu,
        "expected_state": state,
        "expected_pickup_norm": pickup_norm,
        "expected_pickup_estimate": pickup_est,
        "expected_pickup_range": [
            max(pickup_min, pickup_est - 0.03),
            min(pickup_max, pickup_est + 0.03),
        ],
        "expected_coherence": expected_coherence,
        "reference_cos2_model": cos2,
    }


def run(args: argparse.Namespace) -> None:
    preds = [
        predict_point(
            phi=phi,
            harmonic=args.harmonic,
            alpha=args.alpha,
            nu=args.nu,
            state_width=args.state_width,
        )
        for phi in args.phis
    ]

    payload = {
        "harmonic": args.harmonic,
        "alpha": args.alpha,
        "nu": args.nu,
        "predictions": preds,
    }

    print("\n=== INTERFERENCE PREDICTION ===\n")
    print(f"harmonic : {args.harmonic}")
    print(f"alpha    : {args.alpha}")
    print(f"nu       : {args.nu}")
    print()

    for p in preds:
        lo, hi = p["expected_pickup_range"]
        print(
            f"phi={p['phi']:.6f} | state={p['expected_state']} | "
            f"pickup_norm={p['expected_pickup_norm']:.6f} | "
            f"pickup_est={p['expected_pickup_estimate']:.6f} | "
            f"pickup_range=[{lo:.6f},{hi:.6f}] | "
            f"coh≈{p['expected_coherence']:.3f}"
        )

    if args.json_out:
        out_path = Path(args.json_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"\nWrote JSON: {out_path}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Predict Symatics interference state before running.")
    ap.add_argument("--phis", nargs="+", type=float, required=True)
    ap.add_argument("--harmonic", type=int, default=4)
    ap.add_argument("--alpha", type=float, default=0.080)
    ap.add_argument("--nu", type=float, default=0.020)
    ap.add_argument("--state-width", type=float, default=0.35)
    ap.add_argument(
        "--json-out",
        default="backend/modules/dimensions/ucs/zones/experiments/qwave_engine/outputs/interference_prediction_latest.json",
    )
    run(ap.parse_args())