#!/usr/bin/env python3
"""Train a compact nonlinear kernel Shadow Expert on frozen numerical rows."""

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


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def percentile(values: list[float], fraction: float) -> float:
    return sorted(values)[int(fraction * (len(values) - 1))]


def load_vector(path: str) -> np.ndarray:
    value = np.fromfile(path, dtype="<f4").astype(np.float64)
    if value.size != WIDTH:
        raise SystemExit("capture width mismatch")
    return value


def feature(record: dict, route_scale: float = 0.0) -> np.ndarray:
    activation = np.concatenate((load_vector(record["ffn_path"]),
                                 load_vector(record["router_path"])))
    activation /= max(np.linalg.norm(activation), np.finfo(np.float64).tiny)
    route = np.zeros(128, dtype=np.float64)
    for expert, gate in zip(record["route"], record["gates"]):
        route[int(expert)] = float(gate)
    value = np.concatenate((activation, route_scale * route))
    return value / max(np.linalg.norm(value), np.finfo(np.float64).tiny)


def relative_l2(prediction: np.ndarray, target: np.ndarray) -> float:
    return float(np.linalg.norm(prediction - target) /
                 max(np.linalg.norm(target), np.finfo(np.float64).tiny))


def kernel_values(kind: str, left: np.ndarray, right: np.ndarray,
                  gamma: float | None) -> np.ndarray:
    if kind == "linear":
        return left @ right.T
    if kind == "polynomial2":
        return (left @ right.T + 1.0) ** 2
    if kind == "rbf":
        return np.exp(-float(gamma) *
                      ((left[:, None, :] - right[None, :, :]) ** 2).sum(axis=2))
    raise ValueError(f"unknown kernel: {kind}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--authorization", type=Path, required=True)
    parser.add_argument("--cartridge", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.cartridge.exists() or args.output.exists():
        raise SystemExit("refusing to overwrite evidence")
    authorization = json.loads(args.authorization.read_text())
    if not authorization.get("authorized"):
        raise SystemExit("training is not authorized")
    manifest = json.loads(args.manifest.read_text())
    if manifest.get("status") != "READY_FOR_AUTHORIZED_TRAINING":
        raise SystemExit("manifest is not training-ready")
    family_split = {family: split for split, families in
                    manifest["family_disjoint_split"].items() for family in families}
    rows = []
    for family in manifest["families"]:
        for record in family["records"]:
            rows.append({"family_id": family["family_id"],
                         "split": family_split[family["family_id"]],
                         "layer": record["layer"], "record": record})
    layers = sorted({row["layer"] for row in rows})
    trained = {}
    selection = []
    for layer in layers:
        train_rows = [row for row in rows if row["layer"] == layer and row["split"] == "train"]
        calibration_rows = [row for row in rows if row["layer"] == layer and row["split"] == "calibration"]
        y = np.stack([load_vector(row["record"]["residual_path"]) for row in train_rows])
        best = None
        for route_scale in (0.0, .25, .5, 1.0, 2.0, 4.0):
            x = np.stack([feature(row["record"], route_scale) for row in train_rows])
            squared = ((x[:, None, :] - x[None, :, :]) ** 2).sum(axis=2)
            nonzero = squared[squared > 0]
            scale = float(np.median(nonzero)) if nonzero.size else 1.0
            configurations = [("linear", None), ("polynomial2", None)]
            configurations += [("rbf", multiplier / scale)
                               for multiplier in (.25, 1.0, 4.0, 16.0)]
            for kernel_kind, gamma in configurations:
                kernel = kernel_values(kernel_kind, x, x, gamma)
                for ridge in (1e-6, 1e-4, 1e-2, 1e-1):
                    alpha = np.linalg.solve(kernel + ridge * np.eye(len(x)), y)
                    errors = []
                    for row in calibration_rows:
                        candidate = feature(row["record"], route_scale)[None, :]
                        weights = kernel_values(kernel_kind, candidate, x, gamma)[0]
                        errors.append(relative_l2(weights @ alpha,
                                                  load_vector(row["record"]["residual_path"])))
                    score = statistics.median(errors)
                    if best is None or score < best[0]:
                        best = (score, kernel_kind, gamma, ridge, route_scale,
                                x, alpha, errors)
        score, kernel_kind, gamma, ridge, route_scale, x, alpha, errors = best
        trained[layer] = {"prototypes": x.astype(np.float32), "alpha": alpha.astype(np.float32),
                          "kernel": kernel_kind, "gamma": gamma, "ridge": ridge,
                          "route_scale": route_scale, "calibration_error": score}
        selection.append({"layer": layer, "kernel": kernel_kind, "gamma": gamma,
                          "ridge": ridge, "route_scale": route_scale,
                          "calibration_relative_l2": score})

    args.cartridge.mkdir(parents=True, exist_ok=False)
    layer_receipts = {}
    for layer, model in trained.items():
        prototype_path = args.cartridge / f"layer-{layer}-prototypes-f32.bin"
        alpha_path = args.cartridge / f"layer-{layer}-alpha-f32.bin"
        model["prototypes"].tofile(prototype_path); model["alpha"].tofile(alpha_path)
        layer_receipts[str(layer)] = {
            "prototype_shape": list(model["prototypes"].shape),
            "prototype_sha256": digest(prototype_path),
            "alpha_shape": list(model["alpha"].shape), "alpha_sha256": digest(alpha_path),
            "kernel": model["kernel"], "gamma": model["gamma"], "ridge": model["ridge"],
            "route_scale": model["route_scale"],
            "calibration_relative_l2": model["calibration_error"],
        }
    cartridge_receipt = {
        "schema": "aion.shadow-expert-rbf-kernel-cartridge.v1",
        "quality_track": True, "exact_fallback_required": True,
        "source_manifest_canonical_sha256": manifest["canonical_sha256"],
        "authorization_sha256": digest(args.authorization), "layers": layer_receipts,
        "claim_boundary": "Nonlinear RBF baseline; changed arithmetic; never exact GPT-OSS 120B.",
    }
    body = json.dumps(cartridge_receipt, sort_keys=True, separators=(",", ":"))
    cartridge_receipt["canonical_sha256"] = hashlib.sha256(body.encode()).hexdigest()
    receipt_path = args.cartridge / "cartridge.json"
    receipt_path.write_text(json.dumps(cartridge_receipt, indent=2, sort_keys=True) + "\n")

    timings = []
    sample = next(row for row in rows if row["split"] == "train")
    sample_model = trained[sample["layer"]]
    sample_feature = feature(sample["record"], sample_model["route_scale"])
    for _ in range(200):
        began = time.perf_counter_ns()
        weights = kernel_values(sample_model["kernel"], sample_feature[None, :],
                                sample_model["prototypes"], sample_model["gamma"])[0]
        weights @ sample_model["alpha"]
        timings.append((time.perf_counter_ns() - began) / 1e6)
    observations = []
    for row in rows:
        model = trained[row["layer"]]
        candidate = feature(row["record"], model["route_scale"])
        weights = kernel_values(model["kernel"], candidate[None, :],
                                model["prototypes"], model["gamma"])[0]
        prediction = weights @ model["alpha"]
        observations.append({"split": row["split"], "family_id": row["family_id"],
                             "layer": row["layer"], "relative_l2": relative_l2(
                                 prediction, load_vector(row["record"]["residual_path"]))})
    summaries = {}
    for split in manifest["family_disjoint_split"]:
        errors = [row["relative_l2"] for row in observations if row["split"] == split]
        summaries[split] = {"samples": len(errors), "relative_l2_p50": statistics.median(errors),
                            "relative_l2_p95": percentile(errors, .95), "relative_l2_max": max(errors)}
    accepted_layers = sorted(layer for layer, model in trained.items()
                             if model["calibration_error"] <= .02)
    holdout = [row for row in observations if row["split"] in
               ("numerical_holdout", "semantic_holdout")]
    accepted_holdout = [row for row in holdout if row["layer"] in accepted_layers]
    unsafe = [row for row in accepted_holdout if row["relative_l2"] > .05]
    accepted_errors = [row["relative_l2"] for row in accepted_holdout]
    accepted_error_p95 = percentile(accepted_errors, .95) if accepted_errors else None
    accepted_error_max = max(accepted_errors) if accepted_errors else None
    accepted_fraction = len(accepted_holdout) / len(holdout)
    traffic_reduction = 1 / max(1 - accepted_fraction, 1 / len(holdout))
    cartridge_bytes = sum(path.stat().st_size for path in args.cartridge.iterdir())
    accuracy_passed = bool(accepted_errors) and accepted_error_p95 <= .02 and accepted_error_max <= .05
    status = ("ADVANCE_EXPERIMENTAL_RUNG" if accepted_layers and accuracy_passed
              and not unsafe and traffic_reduction > 1.10 else "STOP_KERNEL_BASELINE")
    report = {
        "schema": "aion.shadow-expert-rbf-kernel-training-gate.v1", "status": status,
        "created_at": datetime.now(timezone.utc).isoformat(), "quality_track": True,
        "training_authorized": True, "manifest_canonical_sha256": manifest["canonical_sha256"],
        "authorization_sha256": digest(args.authorization),
        "cartridge_path": str(args.cartridge.resolve()), "cartridge_bytes": cartridge_bytes,
        "cartridge_receipt_sha256": digest(receipt_path),
        "calculation_ms_p50": statistics.median(timings),
        "calculation_ms_p95": percentile(timings, .95), "selection": selection,
        "summaries": summaries, "accepted_layers": accepted_layers,
        "accepted_holdout_fraction": accepted_fraction,
        "accepted_holdout_relative_l2_p95": accepted_error_p95,
        "accepted_holdout_relative_l2_max": accepted_error_max,
        "accepted_holdout_accuracy_passed": accuracy_passed,
        "unsafe_accepted_holdout_rows": unsafe,
        "projected_expert_traffic_reduction": traffic_reduction,
        "observations": observations,
        "claim_boundary": (
            "Authorized nonlinear changed-arithmetic microgate. Exact SD fallback remains "
            "authoritative; no full-model speed or quality claim is made."
        ),
    }
    report_body = json.dumps(report, sort_keys=True, separators=(",", ":"))
    report["canonical_sha256"] = hashlib.sha256(report_body.encode()).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": status, "cartridge_bytes": cartridge_bytes,
                      "calculation_ms_p50": report["calculation_ms_p50"],
                      "accepted_layers": accepted_layers,
                      "projected_expert_traffic_reduction": traffic_reduction,
                      "holdout_p95": max(summaries["numerical_holdout"]["relative_l2_p95"],
                                         summaries["semantic_holdout"]["relative_l2_p95"]),
                      "canonical_sha256": report["canonical_sha256"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
