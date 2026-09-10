#!/usr/bin/env python3
"""Train the first tiny, explicitly changed-arithmetic Shadow Expert baseline."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


WIDTH = 2880
FEATURES = ("constant", "ffn", "router", "ffn_router", "ffn_squared", "router_squared")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def percentile(values: list[float], fraction: float) -> float:
    return sorted(values)[int(fraction * (len(values) - 1))]


def design(ffn: np.ndarray, router: np.ndarray) -> np.ndarray:
    return np.column_stack((np.ones(WIDTH), ffn, router, ffn * router,
                            ffn * ffn, router * router)).astype(np.float64)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--authorization", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cartridge", type=Path, required=True)
    parser.add_argument("--ridge", type=float, default=1e-6)
    args = parser.parse_args()
    if args.output.exists() or args.cartridge.exists():
        raise SystemExit("refusing to overwrite evidence")
    authorization = json.loads(args.authorization.read_text())
    if (authorization.get("schema") != "aion.shadow-expert-training-authorization.v1"
            or authorization.get("authorized") is not True):
        raise SystemExit("explicit training authorization is absent")
    manifest = json.loads(args.manifest.read_text())
    if manifest.get("status") != "READY_FOR_AUTHORIZED_TRAINING":
        raise SystemExit("dataset is not ready for authorized training")
    family_to_split = {family: split for split, families in
                       manifest["family_disjoint_split"].items() for family in families}
    rows: dict[str, list[dict]] = {split: [] for split in manifest["family_disjoint_split"]}
    for family in manifest["families"]:
        split = family_to_split[family["family_id"]]
        for record in family["records"]:
            ffn = np.fromfile(record["ffn_path"], dtype="<f4")
            router = np.fromfile(record["router_path"], dtype="<f4")
            target = np.fromfile(record["residual_path"], dtype="<f4")
            if any(value.size != WIDTH for value in (ffn, router, target)):
                raise SystemExit("training row width mismatch")
            rows[split].append({"family_id": family["family_id"], "layer": record["layer"],
                                "ffn": ffn, "router": router, "target": target})
    by_layer: dict[int, list[dict]] = {}
    for row in rows["train"]:
        by_layer.setdefault(row["layer"], []).append(row)
    coefficients = {}
    for layer, layer_rows in sorted(by_layer.items()):
        x = np.concatenate([design(row["ffn"], row["router"]) for row in layer_rows])
        y = np.concatenate([row["target"].astype(np.float64) for row in layer_rows])
        # Solve directly rather than forming X^T X; the raw activation scales
        # make normal equations needlessly ill-conditioned.
        if args.ridge > 0:
            x_fit = np.vstack((x, np.sqrt(args.ridge) * np.eye(len(FEATURES))))
            y_fit = np.concatenate((y, np.zeros(len(FEATURES))))
        else:
            x_fit, y_fit = x, y
        coefficients[layer] = np.linalg.lstsq(x_fit, y_fit, rcond=None)[0]

    timings = []
    sample = rows["train"][0]
    for _ in range(200):
        began = time.perf_counter_ns()
        design(sample["ffn"], sample["router"]) @ coefficients[sample["layer"]]
        timings.append((time.perf_counter_ns() - began) / 1e6)

    observations = []
    for split, split_rows in rows.items():
        for row in split_rows:
            prediction = design(row["ffn"], row["router"]) @ coefficients[row["layer"]]
            target = row["target"].astype(np.float64)
            error = float(np.linalg.norm(prediction - target) /
                          max(np.linalg.norm(target), np.finfo(np.float64).tiny))
            observations.append({"split": split, "family_id": row["family_id"],
                                 "layer": row["layer"], "relative_l2": error})
    summaries = {}
    for split in rows:
        errors = [row["relative_l2"] for row in observations if row["split"] == split]
        summaries[split] = {"samples": len(errors), "relative_l2_p50": statistics.median(errors),
                            "relative_l2_p95": percentile(errors, .95),
                            "relative_l2_max": max(errors)}
    # Calibration is intentionally independent of fitting. A layer is eligible
    # only when its calibration row meets the locked 0.02 error threshold.
    calibration_by_layer = {row["layer"]: row["relative_l2"] for row in observations
                            if row["split"] == "calibration"}
    accepted_layers = sorted(layer for layer, error in calibration_by_layer.items() if error <= .02)
    holdout = [row for row in observations if row["split"] in
               ("numerical_holdout", "semantic_holdout")]
    accepted_holdout = [row for row in holdout if row["layer"] in accepted_layers]
    unsafe = [row for row in accepted_holdout if row["relative_l2"] > .05]
    accepted_fraction = len(accepted_holdout) / len(holdout)
    traffic_reduction = 1 / max(1 - accepted_fraction, 1 / len(holdout))
    cartridge = {
        "schema": "aion.shadow-expert-affine-cartridge.v1",
        "quality_track": True, "exact_fallback_required": True,
        "features": FEATURES, "ridge": args.ridge,
        "layers": {str(layer): values.tolist() for layer, values in coefficients.items()},
        "accepted_layers_from_calibration": accepted_layers,
        "source_manifest_canonical_sha256": manifest["canonical_sha256"],
        "authorization_sha256": digest(args.authorization),
        "claim_boundary": "Tiny affine baseline; changed arithmetic; never exact GPT-OSS 120B.",
    }
    encoded = json.dumps(cartridge, sort_keys=True, separators=(",", ":"))
    cartridge["canonical_sha256"] = hashlib.sha256(encoded.encode()).hexdigest()
    args.cartridge.parent.mkdir(parents=True, exist_ok=True)
    args.cartridge.write_text(json.dumps(cartridge, indent=2, sort_keys=True) + "\n")
    passed = bool(accepted_layers) and not unsafe and traffic_reduction > 1.0
    report = {
        "schema": "aion.shadow-expert-affine-training-gate.v1",
        "status": "ADVANCE_EXPERIMENTAL_RUNG" if passed else "STOP_AFFINE_BASELINE",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "quality_track": True, "training_authorized": True,
        "manifest_canonical_sha256": manifest["canonical_sha256"],
        "authorization_sha256": digest(args.authorization),
        "cartridge_path": str(args.cartridge.resolve()),
        "cartridge_sha256": digest(args.cartridge),
        "cartridge_canonical_sha256": cartridge["canonical_sha256"],
        "cartridge_bytes": args.cartridge.stat().st_size,
        "calculation_ms_p50": statistics.median(timings),
        "calculation_ms_p95": percentile(timings, .95),
        "summaries": summaries, "accepted_layers": accepted_layers,
        "accepted_holdout_fraction": accepted_fraction,
        "unsafe_accepted_holdout_rows": unsafe,
        "projected_expert_traffic_reduction": traffic_reduction,
        "observations": observations,
        "claim_boundary": (
            "This is the first authorized changed-arithmetic baseline. It may advance only as an "
            "experimental rung; exact SD experts remain the fallback and 10x remains the target."
        ),
    }
    report_body = json.dumps(report, sort_keys=True, separators=(",", ":"))
    report["canonical_sha256"] = hashlib.sha256(report_body.encode()).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": report["status"], "accepted_layers": accepted_layers,
                      "projected_expert_traffic_reduction": traffic_reduction,
                      "calculation_ms_p50": report["calculation_ms_p50"],
                      "holdout_p95": max(summaries["numerical_holdout"]["relative_l2_p95"],
                                         summaries["semantic_holdout"]["relative_l2_p95"]),
                      "canonical_sha256": report["canonical_sha256"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
