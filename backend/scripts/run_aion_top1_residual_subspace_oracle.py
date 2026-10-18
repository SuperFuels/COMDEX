#!/usr/bin/env python3
"""Oracle bound for corrections confined to the training omitted-residual span."""
from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(value: dict) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"),
    ).encode()).hexdigest()


def relative_l2(candidate: np.ndarray, reference: np.ndarray) -> float:
    return float(np.linalg.norm(candidate - reference) /
                 max(np.linalg.norm(reference), np.finfo(np.float64).tiny))


def percentile(values: list[float], fraction: float) -> float:
    return sorted(values)[int(fraction * (len(values) - 1))]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("refusing to overwrite evidence")
    manifest = json.loads(args.dataset_manifest.read_text())
    if manifest.get("status") != "READY_FOR_AUTHORIZED_RESIDUAL_TRAINING":
        raise SystemExit("dataset is not residual-training ready")
    dataset_path = Path(manifest["dataset_path"])
    if digest(dataset_path) != manifest["dataset_sha256"]:
        raise SystemExit("dataset hash mismatch")
    data = np.load(dataset_path)
    observations = []
    for layer in sorted({row["layer"] for row in manifest["rows"]}):
        train_indices = [row["index"] for row in manifest["rows"]
                         if row["layer"] == layer and row["split"] == "train"]
        holdout_rows = [row for row in manifest["rows"] if row["layer"] == layer
                        and row["split"] in ("numerical_holdout", "semantic_holdout")]
        training = data["omitted"][train_indices].astype(np.float64)
        center = training.mean(axis=0)
        _, _, right = np.linalg.svd(training - center, full_matrices=False)
        ranks = sorted({min(rank, len(right)) for rank in (1, 2, 4, 8, 16, len(right))})
        for row in holdout_rows:
            index = row["index"]
            target = data["omitted"][index].astype(np.float64)
            ffn = data["ffn"][index].astype(np.float64)
            top1 = data["top1"][index].astype(np.float64)
            full = data["full"][index].astype(np.float64)
            for rank in ranks:
                basis = right[:rank]
                prediction = center + ((target - center) @ basis.T) @ basis
                observations.append({
                    "layer": layer, "family_id": row["family_id"],
                    "split": row["split"], "rank": rank,
                    "omitted_relative_l2": relative_l2(prediction, target),
                    "output_relative_l2": relative_l2(
                        ffn + top1 + prediction, ffn + full,
                    ),
                })
    full_rank = [row for row in observations if row["rank"] == max(
        item["rank"] for item in observations if item["layer"] == row["layer"]
    )]
    output_errors = [row["output_relative_l2"] for row in full_rank]
    omitted_errors = [row["omitted_relative_l2"] for row in full_rank]
    output_p95 = percentile(output_errors, .95)
    omitted_p95 = percentile(omitted_errors, .95)
    passed = output_p95 <= .02 and omitted_p95 <= .15
    report = {
        "schema": "aion.gptoss-120b-top1-residual-subspace-oracle.v1",
        "status": ("ADVANCE_DEPLOYABLE_RESIDUAL_MODEL" if passed else
                   "STOP_CURRENT_CAPTURE_SPAN"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": "GPT-OSS 120B Q4_K_M/MXFP4", "quality_track": True,
        "oracle_bound": True,
        "dataset_manifest_path": str(args.dataset_manifest.resolve()),
        "dataset_manifest_sha256": digest(args.dataset_manifest),
        "dataset_manifest_canonical_sha256": manifest["canonical_sha256"],
        "full_training_span_output_relative_l2_p50": statistics.median(output_errors),
        "full_training_span_output_relative_l2_p95": output_p95,
        "full_training_span_omitted_relative_l2_p50": statistics.median(omitted_errors),
        "full_training_span_omitted_relative_l2_p95": omitted_p95,
        "promotion_gate": {
            "maximum_output_relative_l2_p95": .02,
            "maximum_omitted_relative_l2_p95": .15,
        },
        "observations": observations,
        "claim_boundary": (
            "Impossible oracle bound: every holdout target chooses its own best "
            "coefficients in the complete centered span of same-layer training "
            "corrections. A failure proves that no predictor confined to the current "
            "capture span can pass; it does not falsify a broader corpus or a more "
            "expressive residual architecture."
        ),
    }
    report["canonical_sha256"] = canonical(report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "status": report["status"], "output_p95": output_p95,
        "omitted_p95": omitted_p95,
        "canonical_sha256": report["canonical_sha256"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
