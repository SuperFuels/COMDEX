from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


def resonance_score(phi: float, harmonic: int) -> float:
    """
    Simple resonance heuristic:
    alignment between phase and harmonic structure
    """
    return abs(math.cos(harmonic * phi / 2.0))


def classify_resonance(score: float) -> str:
    if score > 0.9:
        return "R1_strong"
    if score > 0.6:
        return "R2_moderate"
    if score > 0.3:
        return "R3_weak"
    return "R4_none"


def predict(phi: float, harmonic: int) -> dict[str, Any]:
    score = resonance_score(phi, harmonic)
    return {
        "phi": phi,
        "harmonic": harmonic,
        "resonance_score": score,
        "state": classify_resonance(score),
    }


def run(args):
    preds = [predict(phi, args.harmonic) for phi in args.phis]

    print("\n=== RESONANCE PREDICTION ===\n")
    for p in preds:
        print(
            f"phi={p['phi']:.6f} | "
            f"score={p['resonance_score']:.6f} | "
            f"state={p['state']}"
        )

    if args.json_out:
        Path(args.json_out).write_text(json.dumps(preds, indent=2))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--phis", nargs="+", type=float, required=True)
    ap.add_argument("--harmonic", type=int, default=4)
    ap.add_argument("--json-out", default="resonance_prediction.json")
    run(ap.parse_args())