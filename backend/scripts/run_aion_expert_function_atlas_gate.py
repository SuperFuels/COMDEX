#!/usr/bin/env python3
"""Compile and test one weight-informed Expert Function Atlas layer."""
from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from sklearn.utils.extmath import randomized_svd

from backend.modules.aion_inference.gptoss_expert_frame_store import GptOssExpertFrameStore


WIDTH = 2880
EXPERTS = 128


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(value: dict) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"),
    ).encode()).hexdigest()


def load_capture(root: Path, layer: int) -> tuple[list[dict], np.ndarray, np.ndarray]:
    rows = []
    routers = []
    outputs = []
    for metadata_path in sorted(root.glob(f"position-*-layer-{layer}.json"),
                                key=lambda path: int(path.name.split("-")[1])):
        metadata = json.loads(metadata_path.read_text())
        stem = metadata_path.with_suffix("")
        paths = {name: Path(str(stem) + f"-{name}.bin")
                 for name in ("ffn", "router", "output", "residual")}
        for name, path in paths.items():
            if digest(path) != metadata[f"{name}_sha256"]:
                raise SystemExit(f"capture hash mismatch: {path}")
        router = np.fromfile(paths["router"], dtype="<f4")
        output = np.fromfile(paths["output"], dtype="<f4")
        if router.size != WIDTH or output.size != WIDTH:
            raise SystemExit("capture width mismatch")
        rows.append(metadata)
        routers.append(router)
        outputs.append(output)
    if not rows:
        raise SystemExit(f"no layer {layer} captures in {root}")
    return rows, np.stack(routers), np.stack(outputs)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--authorization", type=Path, required=True)
    parser.add_argument("--train-captures", type=Path, action="append", required=True)
    parser.add_argument("--validation-captures", type=Path, required=True)
    parser.add_argument("--layer", type=int, default=12)
    parser.add_argument("--threads", type=int, default=6)
    parser.add_argument("--cartridge", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.cartridge.exists() or args.output.exists():
        raise SystemExit("refusing to overwrite evidence")
    authorization = json.loads(args.authorization.read_text())
    if authorization.get("authorized") is not True:
        raise SystemExit("explicit residual training authorization is absent")
    train_groups = [load_capture(root, args.layer) for root in args.train_captures]
    train_rows = [row for rows, _, _ in train_groups for row in rows]
    train_x = np.concatenate([values for _, values, _ in train_groups])
    train_layer_output = np.concatenate([values for _, _, values in train_groups])
    valid_rows, valid_x, valid_layer_output = load_capture(args.validation_captures, args.layer)

    source = Path(__file__).parents[1] / "modules/aion_inference/native/gptoss_persistent_moe_library.cpp"
    store = GptOssExpertFrameStore(args.manifest, 512 * 1024 * 1024)
    train_y = np.empty((EXPERTS, len(train_x), WIDTH), dtype=np.float32)
    valid_y = np.empty((EXPERTS, len(valid_x), WIDTH), dtype=np.float32)
    exact_timings = []
    with tempfile.TemporaryDirectory(prefix="aion-expert-function-atlas-") as temporary:
        library_path = Path(temporary) / "moe.dylib"
        subprocess.run([
            "clang++", "-std=c++17", "-O3", "-dynamiclib",
            "-I/opt/homebrew/include", str(source), "-L/opt/homebrew/lib",
            "-lggml", "-lggml-base", "-ldl", "-o", str(library_path),
        ], check=True)
        library = ctypes.CDLL(str(library_path))
        function = library.aion_gptoss_one_expert_contribution_reuse_graph
        function.argtypes = [
            ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_void_p),
            ctypes.c_float, ctypes.POINTER(ctypes.c_float), ctypes.c_int,
            ctypes.POINTER(ctypes.c_double),
        ]
        function.restype = ctypes.c_int
        for expert_id in range(EXPERTS):
            expert = store.get_layer_route_parallel(args.layer, [expert_id], workers=1)[0]
            blobs = [expert[projection][kind] for projection in ("gate", "up", "down")
                     for kind in ("weight", "bias")]
            references = [ctypes.c_char_p(blob) for blob in blobs]
            pointers = (ctypes.c_void_p * 6)(*[
                ctypes.cast(reference, ctypes.c_void_p).value for reference in references
            ])
            for destination, activations in ((train_y[expert_id], train_x),
                                             (valid_y[expert_id], valid_x)):
                for position, activation in enumerate(activations):
                    elapsed = ctypes.c_double()
                    status = function(
                        activation.ctypes.data_as(ctypes.POINTER(ctypes.c_float)), pointers,
                        ctypes.c_float(1.0),
                        destination[position].ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                        args.threads, ctypes.byref(elapsed),
                    )
                    if status:
                        raise RuntimeError(f"expert contribution status {status}")
                    exact_timings.append(elapsed.value)
            _ = references

    # One output basis is shared by all 128 experts. Expert-specific maps turn a
    # compact live-activation coordinate into coefficients in that basis.
    flattened = train_y.reshape(-1, WIDTH).astype(np.float64)
    output_mean = flattened.mean(0)
    _, _, output_basis = randomized_svd(
        flattened - output_mean, n_components=96, n_iter=5, random_state=12012,
    )
    x_mean = train_x.mean(0).astype(np.float64)
    _, _, activation_basis = np.linalg.svd(
        train_x.astype(np.float64) - x_mean, full_matrices=False,
    )
    candidates = []
    trained = {}
    for activation_rank in (8, 16, 24, 32):
        projected_train = (train_x - x_mean) @ activation_basis[:activation_rank].T
        projected_valid = (valid_x - x_mean) @ activation_basis[:activation_rank].T
        scale = np.maximum(projected_train.std(0), 1e-6)
        design_train = np.concatenate([
            np.ones((len(train_x), 1)), projected_train / scale,
            (projected_train / scale) ** 2,
        ], axis=1)
        design_valid = np.concatenate([
            np.ones((len(valid_x), 1)), projected_valid / scale,
            (projected_valid / scale) ** 2,
        ], axis=1)
        for output_rank in (24, 48, 72, 96):
            basis = output_basis[:output_rank]
            coefficients = ((train_y.astype(np.float64) - output_mean) @ basis.T)
            for ridge in (1e-3, 1e-2, 1e-1, 1.0):
                inverse = np.linalg.solve(
                    design_train.T @ design_train + ridge * np.eye(design_train.shape[1]),
                    design_train.T,
                )
                maps = np.einsum("dn,ens->eds", inverse, coefficients)
                predicted_coefficients = np.einsum("nd,edr->enr", design_valid, maps)
                prediction = (predicted_coefficients @ basis + output_mean).astype(np.float32)
                all_error = np.linalg.norm(prediction - valid_y, axis=2) / np.maximum(
                    np.linalg.norm(valid_y, axis=2), 1e-30,
                )
                selected_error = []
                for index, row in enumerate(valid_rows):
                    expert = int(row["route"][3]); gate = float(row["gates"][3])
                    delta = gate * (prediction[expert, index] - valid_y[expert, index])
                    selected_error.append(np.linalg.norm(delta) /
                                          max(np.linalg.norm(valid_layer_output[index]), 1e-30))
                cartridge_bytes = (
                    basis.size + output_mean.size + activation_basis[:activation_rank].size +
                    x_mean.size + scale.size + maps.size
                ) * 4
                row = {
                    "method": "quadratic_ridge",
                    "activation_rank": activation_rank, "output_rank": output_rank,
                    "ridge": ridge, "cartridge_bytes": cartridge_bytes,
                    "all_expert_function_relative_l2_p50": float(np.median(all_error)),
                    "all_expert_function_relative_l2_p95": float(np.percentile(all_error, 95)),
                    "selected_fourth_layer_output_relative_l2_p50": float(np.median(selected_error)),
                    "selected_fourth_layer_output_relative_l2_p95": float(np.percentile(selected_error, 95)),
                    "selected_fourth_layer_output_relative_l2_max": float(np.max(selected_error)),
                }
                candidates.append(row)
                trained[("quadratic_ridge", activation_rank, output_rank, ridge)] = (
                    basis, scale, maps, design_valid, None,
                )
        normalized_train = projected_train / scale
        normalized_valid = projected_valid / scale
        train_distance = np.sum(
            (normalized_train[:, None, :] - normalized_train[None, :, :]) ** 2,
            axis=2,
        )
        nonzero = train_distance[train_distance > 1e-12]
        base_gamma = 1.0 / max(float(np.median(nonzero)), 1e-12)
        valid_distance = np.sum(
            (normalized_valid[:, None, :] - normalized_train[None, :, :]) ** 2,
            axis=2,
        )
        for output_rank in (24, 48, 72, 96):
            basis = output_basis[:output_rank]
            coefficients = ((train_y.astype(np.float64) - output_mean) @ basis.T)
            for gamma_multiplier in (0.25, 1.0, 4.0):
                gamma = base_gamma * gamma_multiplier
                kernel_train = np.exp(-gamma * train_distance)
                kernel_valid = np.exp(-gamma * valid_distance)
                for ridge in (1e-3, 1e-2, 1e-1, 1.0):
                    inverse = np.linalg.solve(
                        kernel_train + ridge * np.eye(len(train_x)),
                        np.eye(len(train_x)),
                    )
                    alpha = np.einsum("nm,emr->enr", inverse, coefficients)
                    predicted_coefficients = np.einsum("vn,enr->evr", kernel_valid, alpha)
                    prediction = (predicted_coefficients @ basis + output_mean).astype(np.float32)
                    all_error = np.linalg.norm(prediction - valid_y, axis=2) / np.maximum(
                        np.linalg.norm(valid_y, axis=2), 1e-30,
                    )
                    selected_error = []
                    for index, row in enumerate(valid_rows):
                        expert = int(row["route"][3]); gate = float(row["gates"][3])
                        delta = gate * (prediction[expert, index] - valid_y[expert, index])
                        selected_error.append(np.linalg.norm(delta) /
                                              max(np.linalg.norm(valid_layer_output[index]), 1e-30))
                    cartridge_bytes = (
                        basis.size + output_mean.size + activation_basis[:activation_rank].size +
                        x_mean.size + scale.size + normalized_train.size + alpha.size
                    ) * 4
                    row = {
                        "method": "rbf_atlas", "activation_rank": activation_rank,
                        "output_rank": output_rank, "ridge": ridge,
                        "gamma_multiplier": gamma_multiplier, "gamma": gamma,
                        "cartridge_bytes": cartridge_bytes,
                        "all_expert_function_relative_l2_p50": float(np.median(all_error)),
                        "all_expert_function_relative_l2_p95": float(np.percentile(all_error, 95)),
                        "selected_fourth_layer_output_relative_l2_p50": float(np.median(selected_error)),
                        "selected_fourth_layer_output_relative_l2_p95": float(np.percentile(selected_error, 95)),
                        "selected_fourth_layer_output_relative_l2_max": float(np.max(selected_error)),
                    }
                    candidates.append(row)
                    trained[("rbf_atlas", activation_rank, output_rank, ridge,
                             gamma_multiplier)] = (
                        basis, scale, alpha, kernel_valid, normalized_train,
                    )
    selected = min(candidates, key=lambda row: (
        row["selected_fourth_layer_output_relative_l2_p95"], row["cartridge_bytes"],
    ))
    if selected["method"] == "quadratic_ridge":
        key = (selected["method"], selected["activation_rank"],
               selected["output_rank"], selected["ridge"])
        basis, scale, maps, design_valid, _ = trained[key]
        runtime_extra = {"expert_maps": maps.astype("<f4")}
    else:
        key = (selected["method"], selected["activation_rank"],
               selected["output_rank"], selected["ridge"],
               selected["gamma_multiplier"])
        basis, scale, maps, design_valid, normalized_train = trained[key]
        runtime_extra = {
            "expert_alpha": maps.astype("<f4"),
            "training_activation_coordinates": normalized_train.astype("<f4"),
            "gamma": np.asarray([selected["gamma"]], dtype="<f4"),
        }
    timings = []
    for index, row in enumerate(valid_rows):
        expert = int(row["route"][3]); gate = float(row["gates"][3])
        for _ in range(30):
            started = time.perf_counter_ns()
            coordinate = ((valid_x[index].astype(np.float64) - x_mean) @
                          activation_basis[:selected["activation_rank"]].T) / scale
            if selected["method"] == "quadratic_ridge":
                live_design = np.concatenate(([1.0], coordinate, coordinate ** 2))
            else:
                live_design = np.exp(-selected["gamma"] * np.sum(
                    (coordinate[None, :] - normalized_train) ** 2, axis=1,
                ))
            coefficient = live_design @ maps[expert]
            _ = gate * (coefficient @ basis + output_mean)
            timings.append((time.perf_counter_ns() - started) / 1e6)
    args.cartridge.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        args.cartridge, output_mean=output_mean.astype("<f4"),
        output_basis=basis.astype("<f4"), x_mean=x_mean.astype("<f4"),
        activation_basis=activation_basis[:selected["activation_rank"]].astype("<f4"),
        activation_scale=scale.astype("<f4"), **runtime_extra,
    )
    baseline_p95 = float(np.percentile([
        row["counterfactuals"]["3"]["output_relative_l2"] for row in valid_rows
    ], 95))
    accepted = {
        "beats_drop_fourth": selected["selected_fourth_layer_output_relative_l2_p95"] < baseline_p95,
        "under_two_percent_p95": selected["selected_fourth_layer_output_relative_l2_p95"] <= 0.02,
        "at_least_four_x_smaller_than_one_expert": args.cartridge.stat().st_size <= 13_893_632 / 4,
        "under_point_four_ms": float(np.median(timings)) <= 0.4,
    }
    report = {
        "schema": "aion.gptoss-120b-expert-function-atlas-layer-gate.v1",
        "status": "ADVANCE_EXPERT_FUNCTION_ATLAS" if all(accepted.values()) else "STOP_ATLAS_LOCAL_MAP",
        "created_at": datetime.now(timezone.utc).isoformat(), "quality_track": True,
        "exact_fallback_required": True, "layer": args.layer,
        "training_families": [root.name for root in args.train_captures],
        "unseen_validation_family": args.validation_captures.name,
        "training_activations": len(train_x), "validation_activations": len(valid_x),
        "experts_compiled": EXPERTS, "selected": selected,
        "drop_fourth_baseline_layer_output_relative_l2_p95": baseline_p95,
        "candidate_count": len(candidates), "candidates": candidates,
        "atlas_calculation_ms_p50": float(np.median(timings)),
        "atlas_calculation_ms_p95": float(np.percentile(timings, 95)),
        "exact_expert_calculation_ms_p50": float(np.median(exact_timings)),
        "cartridge_path": str(args.cartridge.resolve()),
        "cartridge_bytes_on_disk": args.cartridge.stat().st_size,
        "cartridge_sha256": digest(args.cartridge), "acceptance": accepted,
        "authorization_sha256": digest(args.authorization),
        "warehouse_manifest_sha256": digest(args.manifest),
        "reasoning_development_opened": "reasoning" in args.validation_captures.name,
        "blind_business_and_writing_opened": False,
        "claim_boundary": (
            "All 128 experts in one real layer were compiled from their original SD-backed "
            "weights on the declared training activations. Validation activations were not used to fit "
            "the atlas and provide the unseen-family numerical gate. This is not full-model "
            "quality or token-speed evidence."
        ),
    }
    report["canonical_sha256"] = canonical(report)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "status": report["status"], "selected": selected, "baseline_p95": baseline_p95,
        "atlas_ms_p50": report["atlas_calculation_ms_p50"],
        "cartridge_bytes_on_disk": report["cartridge_bytes_on_disk"],
        "acceptance": accepted, "canonical_sha256": report["canonical_sha256"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
