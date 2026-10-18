#!/usr/bin/env python3
"""Build non-trained oracle/zero controls for Shadow Expert evaluator testing."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--mode", choices=("oracle", "zero"), required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=False)
    manifest = json.loads(args.manifest.read_text())
    holdout = set(manifest["family_disjoint_split"]["numerical_holdout"] +
                  manifest["family_disjoint_split"]["semantic_holdout"])
    count = 0
    for family in manifest["families"]:
        if family["family_id"] not in holdout:
            continue
        for record in family["records"]:
            target = np.fromfile(record["residual_path"], dtype="<f4")
            prediction = target if args.mode == "oracle" else np.zeros_like(target)
            key = (f"{family['family_id']}--position-{record['position']}"
                   f"--layer-{record['layer']}")
            prediction_path = args.output_dir / f"{key}-prediction.bin"
            prediction.tofile(prediction_path)
            receipt = {
                "schema": "aion.shadow-expert-deterministic-control.v1",
                "mode": args.mode,
                "confidence": 1.0,
                "prediction_sha256": digest(prediction_path),
                "training_performed": False,
                "claim_boundary": "Evaluator control only; not a deployable Shadow Expert.",
            }
            (args.output_dir / f"{key}-confidence.json").write_text(
                json.dumps(receipt, indent=2, sort_keys=True) + "\n")
            count += 1
    if not count:
        raise SystemExit("manifest has no holdout rows")
    print(json.dumps({"mode": args.mode, "holdout_predictions": count,
                      "training_performed": False}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
