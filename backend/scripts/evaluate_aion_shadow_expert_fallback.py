#!/usr/bin/env python3
"""Evaluate a frozen Shadow Expert candidate and its exact-fallback gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


WIDTH = 2880


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def percentile(values: list[float], fraction: float) -> float:
    return sorted(values)[int(fraction * (len(values) - 1))]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--candidate-dir", type=Path, required=True)
    parser.add_argument("--confidence-threshold", type=float, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("refusing to overwrite evidence")
    manifest = json.loads(args.manifest.read_text())
    claimed = manifest.get("canonical_sha256")
    body = dict(manifest); body.pop("canonical_sha256", None)
    calculated = hashlib.sha256(json.dumps(
        body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    if claimed != calculated:
        raise SystemExit("dataset manifest failed canonical hash verification")
    split = manifest["family_disjoint_split"]
    holdout = set(split["numerical_holdout"] + split["semantic_holdout"])
    observations = []
    for family in manifest["families"]:
        if family["family_id"] not in holdout:
            continue
        for record in family["records"]:
            if "residual_path" not in record:
                raise SystemExit("holdout record has no verified target residual")
            target_path = Path(record["residual_path"])
            if digest(target_path) != record["residual_sha256"]:
                raise SystemExit("target residual failed hash verification")
            key = f"{family['family_id']}--position-{record['position']}--layer-{record['layer']}"
            prediction_path = args.candidate_dir / f"{key}-prediction.bin"
            confidence_path = args.candidate_dir / f"{key}-confidence.json"
            prediction = np.fromfile(prediction_path, dtype="<f4")
            target = np.fromfile(target_path, dtype="<f4")
            if prediction.size != WIDTH or target.size != WIDTH:
                raise SystemExit("candidate or target width mismatch")
            confidence_receipt = json.loads(confidence_path.read_text())
            if confidence_receipt.get("prediction_sha256") != digest(prediction_path):
                raise SystemExit("prediction failed confidence-receipt hash verification")
            confidence = float(confidence_receipt["confidence"])
            relative_l2 = float(np.linalg.norm(
                prediction.astype(np.float64) - target.astype(np.float64)) /
                max(np.linalg.norm(target.astype(np.float64)), np.finfo(np.float64).tiny))
            violation = relative_l2 > .05
            accepted = confidence >= args.confidence_threshold
            observations.append({
                "family_id": family["family_id"], "position": record["position"],
                "layer": record["layer"], "confidence": confidence,
                "accepted": accepted, "relative_l2": relative_l2,
                "violation": violation, "violation_captured_by_fallback": violation and not accepted,
                "prediction_sha256": digest(prediction_path),
                "confidence_receipt_sha256": digest(confidence_path),
            })
    if not observations:
        raise SystemExit("manifest has no holdout observations")
    errors = [item["relative_l2"] for item in observations]
    violations = [item for item in observations if item["violation"]]
    accepted = [item for item in observations if item["accepted"]]
    captured = sum(item["violation_captured_by_fallback"] for item in violations)
    capture_rate = captured / len(violations) if violations else 1.0
    accepted_fraction = len(accepted) / len(observations)
    projected_traffic_reduction = (1.0 / max(1.0 - accepted_fraction, 1 / len(observations)))
    passed = (percentile(errors, .95) <= .02 and max(errors) <= .05
              and capture_rate >= .999 and projected_traffic_reduction >= 10.0)
    report = {
        "schema": "aion.shadow-expert-exact-fallback-evaluation.v1",
        "status": "MECHANISM_GATE_PASSED" if passed else "MECHANISM_GATE_FAILED",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "quality_track": True, "training_authorized": False,
        "dataset_manifest_path": str(args.manifest.resolve()),
        "dataset_manifest_canonical_sha256": claimed,
        "candidate_directory": str(args.candidate_dir.resolve()),
        "confidence_threshold": args.confidence_threshold,
        "observations": observations,
        "summary": {
            "samples": len(observations), "relative_l2_p50": statistics.median(errors),
            "relative_l2_p95": percentile(errors, .95), "relative_l2_max": max(errors),
            "accepted_fraction": accepted_fraction, "violations": len(violations),
            "violation_capture_rate": capture_rate,
            "projected_expert_traffic_reduction": projected_traffic_reduction,
        },
        "claim_boundary": (
            "This evaluator measures a frozen changed-arithmetic candidate on family-disjoint "
            "holdouts and simulates rejection to the existing exact SD path. It neither trains "
            "nor injects weights, and a mechanism pass does not constitute full-model promotion."
        ),
    }
    encoded = json.dumps(report, sort_keys=True, separators=(",", ":"))
    report["canonical_sha256"] = hashlib.sha256(encoded.encode()).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": report["status"], **report["summary"],
                      "canonical_sha256": report["canonical_sha256"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
