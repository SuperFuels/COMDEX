#!/usr/bin/env python3
"""Compute an oracle lower bound for training-residual subspace prediction."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


def percentile(values: list[float], fraction: float) -> float:
    return sorted(values)[int(fraction * (len(values) - 1))]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("refusing to overwrite evidence")
    manifest = json.loads(args.manifest.read_text())
    split = {family: name for name, families in manifest["family_disjoint_split"].items()
             for family in families}
    rows = []
    for family in manifest["families"]:
        for record in family["records"]:
            rows.append((split[family["family_id"]], family["family_id"], record["layer"],
                         np.fromfile(record["residual_path"], dtype="<f4").astype(np.float64)))
    observations = []
    for layer in sorted({row[2] for row in rows}):
        train = np.stack([row[3] for row in rows if row[0] == "train" and row[2] == layer])
        # QR produces a stable orthonormal basis for the complete observed span.
        basis, _ = np.linalg.qr(train.T, mode="reduced")
        for split_name, family_id, row_layer, target in rows:
            if row_layer != layer or split_name not in ("calibration", "numerical_holdout",
                                                         "semantic_holdout"):
                continue
            projection = basis @ (basis.T @ target)
            error = float(np.linalg.norm(projection - target) /
                          max(np.linalg.norm(target), np.finfo(np.float64).tiny))
            observations.append({"split": split_name, "family_id": family_id,
                                 "layer": layer, "training_span_rank": int(basis.shape[1]),
                                 "oracle_relative_l2": error})
    summaries = {}
    for split_name in ("calibration", "numerical_holdout", "semantic_holdout"):
        errors = [row["oracle_relative_l2"] for row in observations if row["split"] == split_name]
        summaries[split_name] = {"samples": len(errors), "oracle_relative_l2_p50": statistics.median(errors),
                                 "oracle_relative_l2_p95": percentile(errors, .95),
                                 "oracle_relative_l2_max": max(errors),
                                 "rows_below_0_02": sum(error <= .02 for error in errors),
                                 "rows_below_0_05": sum(error <= .05 for error in errors)}
    holdout = [row["oracle_relative_l2"] for row in observations
               if row["split"] in ("numerical_holdout", "semantic_holdout")]
    advance = percentile(holdout, .95) <= .02 and max(holdout) <= .05
    report = {
        "schema": "aion.shadow-expert-residual-subspace-oracle-bound.v1",
        "status": "ADVANCE_RESIDUAL_SUBSPACE" if advance else "STOP_RESIDUAL_DICTIONARY_SUBSPACE",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "manifest_canonical_sha256": manifest["canonical_sha256"],
        "quality_track": True, "oracle_uses_holdout_target": True,
        "summaries": summaries, "observations": observations,
        "claim_boundary": (
            "This is an impossible oracle lower bound: holdout targets choose their best "
            "projection inside the complete training-residual span. A failure therefore stops "
            "codebooks confined to that span; it is not a deployable predictor or speed result."
        ),
    }
    body = json.dumps(report, sort_keys=True, separators=(",", ":"))
    report["canonical_sha256"] = hashlib.sha256(body.encode()).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": report["status"], "summaries": summaries,
                      "canonical_sha256": report["canonical_sha256"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
