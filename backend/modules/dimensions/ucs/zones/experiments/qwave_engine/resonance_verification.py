from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


def load_jsonl(path: Path):
    rows = []
    with path.open() as f:
        for line in f:
            rows.append(json.loads(line))
    return rows


def phi_of(r):
    return float(r.get("phi_hint", r.get("phi", 0.0)))


def pickup_of(r):
    return float(r.get("pickup", r.get("pickup_mean", 0.0)))


def resonance_score(phi: float, harmonic: int) -> float:
    return abs(math.cos(harmonic * phi / 2.0))


def classify(score: float) -> str:
    if score > 0.9:
        return "R1_strong"
    if score > 0.6:
        return "R2_moderate"
    if score > 0.3:
        return "R3_weak"
    return "R4_none"


def run(args):
    rows = load_jsonl(Path(args.input))

    print("\n=== RESONANCE VERIFICATION ===\n")

    for r in rows:
        phi = phi_of(r)
        pickup = pickup_of(r)
        score = resonance_score(phi, args.harmonic)

        print(
            f"phi={phi:.6f} | "
            f"pickup={pickup:.6f} | "
            f"res_score={score:.6f} | "
            f"state={classify(score)}"
        )


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--harmonic", type=int, default=4)
    run(ap.parse_args())