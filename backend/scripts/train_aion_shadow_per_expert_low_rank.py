#!/usr/bin/env python3
"""Train a structured per-expert low-rank Shadow Expert microcandidate."""

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
EXPERTS = 128
LAYERS = (6, 9)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(value: dict) -> str:
    body = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(body.encode()).hexdigest()


def vector(path: str | Path) -> np.ndarray:
    value = np.fromfile(path, dtype="<f4").astype(np.float64)
    if value.size != WIDTH:
        raise SystemExit(f"capture width mismatch: {path}")
    return value


def relative_l2(prediction: np.ndarray, target: np.ndarray) -> float:
    return float(np.linalg.norm(prediction - target) /
                 max(np.linalg.norm(target), np.finfo(np.float64).tiny))


def route(record: dict) -> np.ndarray:
    value = np.zeros(EXPERTS, dtype=np.float64)
    for expert, gate in zip(record["route"], record["gates"]):
        value[int(expert)] = float(gate)
    return value


def normalized_router(record: dict) -> np.ndarray:
    value = vector(record["router_path"])
    return value / max(np.linalg.norm(value), np.finfo(np.float64).tiny)


def fit_projection(values: np.ndarray, dimensions: int) -> tuple[np.ndarray, np.ndarray]:
    center = values.mean(axis=0)
    if dimensions == 0:
        return center, np.empty((0, values.shape[1]), dtype=np.float64)
    _, _, right = np.linalg.svd(values - center, full_matrices=False)
    return center, right[:min(dimensions, right.shape[0])]


def project(values: np.ndarray, center: np.ndarray, projection: np.ndarray) -> np.ndarray:
    if projection.shape[0] == 0:
        return np.empty((values.shape[0], 0), dtype=np.float64)
    result = (values - center) @ projection.T
    scale = np.maximum(np.std(result, axis=0, ddof=0), 1e-8)
    return result / scale


def expert_kernel(left_activation: np.ndarray, left_route: np.ndarray,
                  right_activation: np.ndarray, right_route: np.ndarray,
                  shared_weight: float) -> np.ndarray:
    activation = 1.0 + left_activation @ right_activation.T
    routed = left_route @ right_route.T
    # This is the dual form of separate low-rank affine calculators for every
    # expert: gate_e * [1, activation] for each active expert e.
    return routed * activation + shared_weight * activation


def fit_model(rows: list[dict], activation_dimensions: int, target_rank: int,
              ridge: float, shared_weight: float) -> dict:
    routers = np.stack([normalized_router(row) for row in rows])
    routes = np.stack([route(row) for row in rows])
    targets = np.stack([vector(row["residual_path"]) for row in rows])
    center, projection = fit_projection(routers, activation_dimensions)
    activations = project(routers, center, projection)
    _, _, target_right = np.linalg.svd(targets, full_matrices=False)
    basis = target_right[:min(target_rank, target_right.shape[0])]
    coefficients = targets @ basis.T
    gram = expert_kernel(activations, routes, activations, routes, shared_weight)
    alpha = np.linalg.solve(gram + ridge * np.eye(len(rows)), coefficients)
    return {"center": center, "projection": projection, "basis": basis,
            "alpha": alpha, "train_routers": routers, "train_routes": routes,
            "train_activations": activations, "ridge": ridge,
            "shared_weight": shared_weight,
            "activation_dimensions": activation_dimensions,
            "target_rank": min(target_rank, target_right.shape[0])}


def predict(model: dict, row: dict) -> np.ndarray:
    router_value = normalized_router(row)[None, :]
    activation = project(router_value, model["center"], model["projection"])
    route_value = route(row)[None, :]
    weights = expert_kernel(activation, route_value, model["train_activations"],
                            model["train_routes"], model["shared_weight"])[0]
    return (weights @ model["alpha"]) @ model["basis"]


def grouped_cv(rows: list[dict], configuration: tuple[int, int, float, float]) -> list[float]:
    dimensions, rank, ridge, shared_weight = configuration
    errors = []
    for family in sorted({row["family_id"] for row in rows}):
        training = [row for row in rows if row["family_id"] != family]
        validation = [row for row in rows if row["family_id"] == family]
        if len(training) < 4:
            continue
        model = fit_model(training, dimensions, rank, ridge, shared_weight)
        errors.extend(relative_l2(predict(model, row), vector(row["residual_path"]))
                      for row in validation)
    return errors


def percentile(values: list[float], fraction: float) -> float:
    return sorted(values)[int(fraction * (len(values) - 1))]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--authorization", type=Path, required=True)
    parser.add_argument("--cartridge", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.cartridge.exists():
        raise SystemExit("refusing to overwrite evidence")
    authorization = json.loads(args.authorization.read_text())
    if not authorization.get("authorized"):
        raise SystemExit("training is not authorized")
    manifest = json.loads(args.manifest.read_text())
    if manifest.get("status") != "READY_FOR_AUTHORIZED_TRAINING":
        raise SystemExit("manifest is not training-ready")
    split_by_family = {family: split for split, families in
                       manifest["family_disjoint_split"].items() for family in families}
    all_rows = []
    for family in manifest["families"]:
        for record in family["records"]:
            if record["layer"] not in LAYERS:
                continue
            for name in ("router", "residual"):
                if digest(Path(record[f"{name}_path"])) != record[f"{name}_sha256"]:
                    raise SystemExit(f"{name} hash mismatch")
            all_rows.append({**record, "family_id": family["family_id"],
                             "split": split_by_family[family["family_id"]]})

    configurations = [(dimensions, rank, ridge, shared)
                      for dimensions in (0, 2, 4, 8)
                      for rank in (4, 8, 12, 16, 20)
                      for ridge in (1e-6, 1e-4, 1e-2, .1, 1.0)
                      for shared in (0.0, .1, 1.0)]
    trained = {}
    selections = []
    observations = []
    timings = []
    for layer in LAYERS:
        training = [row for row in all_rows if row["layer"] == layer and row["split"] == "train"]
        best = None
        for configuration in configurations:
            errors = grouped_cv(training, configuration)
            score = (percentile(errors, .95), statistics.median(errors), max(errors))
            if best is None or score < best[0]:
                best = (score, configuration)
        cv_score, configuration = best
        model = fit_model(training, *configuration)
        trained[layer] = model
        selections.append({"layer": layer, "activation_dimensions": configuration[0],
                           "target_rank": configuration[1], "ridge": configuration[2],
                           "shared_weight": configuration[3],
                           "training_group_cv_relative_l2_p50": cv_score[1],
                           "training_group_cv_relative_l2_p95": cv_score[0],
                           "training_group_cv_relative_l2_max": cv_score[2]})
        for row in [item for item in all_rows if item["layer"] == layer]:
            observations.append({"layer": layer, "family_id": row["family_id"],
                                 "split": row["split"], "route": row["route"],
                                 "relative_l2": relative_l2(
                                     predict(model, row), vector(row["residual_path"]))})
        sample = training[0]
        for _ in range(300):
            began = time.perf_counter_ns(); predict(model, sample)
            timings.append((time.perf_counter_ns() - began) / 1e6)

    calibration_by_layer = {}
    for layer in LAYERS:
        errors = [row["relative_l2"] for row in observations
                  if row["layer"] == layer and row["split"] == "calibration"]
        calibration_by_layer[layer] = max(errors)
    accepted_layers = sorted(layer for layer, error in calibration_by_layer.items()
                             if error <= .02)
    holdout = [row for row in observations if row["split"] in
               ("numerical_holdout", "semantic_holdout") and
               row["layer"] in accepted_layers]
    holdout_errors = [row["relative_l2"] for row in holdout]
    holdout_p95 = percentile(holdout_errors, .95) if holdout_errors else None
    holdout_max = max(holdout_errors) if holdout_errors else None
    accuracy_passed = bool(holdout_errors) and holdout_p95 <= .02 and holdout_max <= .05
    traffic_reduction = 12 / max(12 - len(accepted_layers), 1)
    latency_p50 = statistics.median(timings)
    status = ("ADVANCE_FRESH_VALIDATION" if accepted_layers and accuracy_passed and
              traffic_reduction > 1.10 and latency_p50 < 1.0
              else "STOP_PER_EXPERT_LOW_RANK")

    args.cartridge.mkdir(parents=True, exist_ok=False)
    file_receipts = {}
    for layer, model in trained.items():
        for name in ("center", "projection", "basis", "alpha", "train_routers",
                     "train_routes", "train_activations"):
            path = args.cartridge / f"layer-{layer}-{name}-f32.bin"
            np.asarray(model[name], dtype=np.float32).tofile(path)
            file_receipts[path.name] = {"sha256": digest(path),
                                        "shape": list(np.asarray(model[name]).shape)}
    receipt = {"schema": "aion.shadow-per-expert-low-rank-cartridge.v1",
               "quality_track": True, "exact_fallback_required": True,
               "source_manifest_canonical_sha256": manifest["canonical_sha256"],
               "authorization_sha256": digest(args.authorization),
               "selection": selections, "files": file_receipts}
    receipt["canonical_sha256"] = canonical(receipt)
    receipt_path = args.cartridge / "cartridge.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")

    report = {"schema": "aion.shadow-per-expert-low-rank-gate.v1",
              "created_at": datetime.now(timezone.utc).isoformat(), "status": status,
              "quality_track": True, "exact_fallback_required": True,
              "source_manifest_canonical_sha256": manifest["canonical_sha256"],
              "authorization_sha256": digest(args.authorization),
              "selection_used_training_group_cv_only": True,
              "selection": selections, "calibration_by_layer": calibration_by_layer,
              "accepted_layers": accepted_layers,
              "accepted_holdout_relative_l2_p95": holdout_p95,
              "accepted_holdout_relative_l2_max": holdout_max,
              "accepted_holdout_accuracy_passed": accuracy_passed,
              "calculation_ms_p50": latency_p50,
              "calculation_ms_p95": percentile(timings, .95),
              "projected_expert_traffic_reduction": traffic_reduction,
              "observations": observations,
              "cartridge_receipt_sha256": digest(receipt_path),
              "claim_boundary": ("Training-only group-selected structured per-expert low-rank "
                                  "microgate. Changed arithmetic; exact fallback remains mandatory. "
                                  "No full-model speed or quality claim is made.")}
    report["canonical_sha256"] = canonical(report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": status, "accepted_layers": accepted_layers,
                      "holdout_p95": holdout_p95, "holdout_max": holdout_max,
                      "calculation_ms_p50": latency_p50,
                      "traffic_reduction": traffic_reduction,
                      "canonical_sha256": report["canonical_sha256"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
