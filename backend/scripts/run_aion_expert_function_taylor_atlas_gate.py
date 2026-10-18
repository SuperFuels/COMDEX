#!/usr/bin/env python3
"""Compile a one-layer, weight-derived local Taylor Expert Function Atlas."""
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
from sklearn.cluster import KMeans

from backend.modules.aion_inference.gptoss_expert_frame_store import GptOssExpertFrameStore
from backend.scripts.run_aion_expert_function_atlas_gate import load_capture


WIDTH = 2880
EXPERTS = 128


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(value: dict) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"),
    ).encode()).hexdigest()


def geometry(values: np.ndarray, rank: int, anchors: int) -> dict:
    mean = values.mean(0).astype(np.float64)
    _, _, basis = np.linalg.svd(values.astype(np.float64) - mean, full_matrices=False)
    basis = basis[:rank]
    projected = (values - mean) @ basis.T
    scale = np.maximum(projected.std(0), 1e-6)
    normalized = projected / scale
    centers = KMeans(n_clusters=anchors, random_state=1212, n_init=20).fit(normalized).cluster_centers_
    medoids = []
    for center in centers:
        medoids.append(int(np.argmin(np.sum((normalized - center) ** 2, axis=1))))
    return {
        "mean": mean, "basis": basis, "scale": scale,
        "anchors": values[medoids].astype(np.float32),
        "anchor_coordinates": normalized[medoids].astype(np.float64),
    }


def coordinates(values: np.ndarray, shape: dict) -> np.ndarray:
    return ((values - shape["mean"]) @ shape["basis"].T) / shape["scale"]


def predict(atlas: np.ndarray, shape: dict, values: np.ndarray,
            expert_ids: np.ndarray) -> np.ndarray:
    live = coordinates(values, shape)
    distances = np.sum(
        (live[:, None, :] - shape["anchor_coordinates"][None, :, :]) ** 2, axis=2,
    )
    nearest = np.argmin(distances, axis=1)
    delta = live - shape["anchor_coordinates"][nearest]
    result = np.empty((len(values), WIDTH), dtype=np.float32)
    for index, expert in enumerate(expert_ids):
        local = atlas[int(expert), nearest[index]]
        result[index] = local[0] + delta[index] @ local[1:]
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--authorization", type=Path, required=True)
    parser.add_argument("--fit-captures", type=Path, required=True)
    parser.add_argument("--selection-captures", type=Path, required=True)
    parser.add_argument("--development-captures", type=Path, required=True)
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
    fit_rows, fit_x, _ = load_capture(args.fit_captures, args.layer)
    selection_rows, selection_x, selection_outputs = load_capture(
        args.selection_captures, args.layer,
    )
    development_rows, development_x, development_outputs = load_capture(
        args.development_captures, args.layer,
    )
    combined_x = np.concatenate((fit_x, selection_x))
    configurations = [(1, 4, 0.05), (2, 4, 0.05), (2, 8, 0.05),
                      (4, 8, 0.05), (4, 12, 0.05), (4, 16, 0.025)]
    fit_shapes = [geometry(fit_x, rank, anchors) for anchors, rank, _ in configurations]
    combined_shapes = [geometry(combined_x, rank, anchors)
                       for anchors, rank, _ in configurations]
    fit_atlases = [np.empty((EXPERTS, anchors, rank + 1, WIDTH), dtype=np.float32)
                   for anchors, rank, _ in configurations]
    combined_atlases = [np.empty((EXPERTS, anchors, rank + 1, WIDTH), dtype=np.float32)
                        for anchors, rank, _ in configurations]
    exact_selection = np.empty((len(selection_x), WIDTH), dtype=np.float32)
    exact_development = np.empty((len(development_x), WIDTH), dtype=np.float32)
    selection_experts = np.asarray([int(row["route"][3]) for row in selection_rows])
    development_experts = np.asarray([int(row["route"][3]) for row in development_rows])
    exact_timings = []
    source = Path(__file__).parents[1] / "modules/aion_inference/native/gptoss_persistent_moe_library.cpp"
    store = GptOssExpertFrameStore(args.manifest, 512 * 1024 * 1024)
    with tempfile.TemporaryDirectory(prefix="aion-expert-taylor-atlas-") as temporary:
        library_path = Path(temporary) / "moe.dylib"
        subprocess.run([
            "clang++", "-std=c++17", "-O3", "-dynamiclib",
            "-I/opt/homebrew/include", str(source), "-L/opt/homebrew/lib",
            "-lggml", "-lggml-base", "-ldl", "-o", str(library_path),
        ], check=True)
        library = ctypes.CDLL(str(library_path))
        # Use the already-validated bounded batch primitive with batch=1.  The
        # experimental reusable graph currently conflates GGML graph metadata
        # and compute scratch in one arena, so it is not an admissible source
        # of numerical evidence for this compiler gate.
        function = library.aion_gptoss_one_expert_contribution_batch
        function.argtypes = [
            ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_void_p),
            ctypes.POINTER(ctypes.c_float), ctypes.c_int,
            ctypes.POINTER(ctypes.c_float), ctypes.c_int,
            ctypes.POINTER(ctypes.c_double),
        ]
        function.restype = ctypes.c_int

        def evaluate(activation: np.ndarray, pointers: ctypes.Array) -> np.ndarray:
            activation = np.ascontiguousarray(activation, dtype=np.float32)
            output = np.empty(WIDTH, dtype=np.float32)
            elapsed = ctypes.c_double()
            gate = np.asarray([1.0], dtype=np.float32)
            status = function(
                activation.ctypes.data_as(ctypes.POINTER(ctypes.c_float)), pointers,
                gate.ctypes.data_as(ctypes.POINTER(ctypes.c_float)), 1,
                output.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                args.threads, ctypes.byref(elapsed),
            )
            if status:
                raise RuntimeError(f"expert contribution status {status}")
            exact_timings.append(elapsed.value)
            return output

        for expert_id in range(EXPERTS):
            expert = store.get_layer_route_parallel(args.layer, [expert_id], workers=1)[0]
            blobs = [expert[projection][kind] for projection in ("gate", "up", "down")
                     for kind in ("weight", "bias")]
            references = [ctypes.c_char_p(blob) for blob in blobs]
            pointers = (ctypes.c_void_p * 6)(*[
                ctypes.cast(reference, ctypes.c_void_p).value for reference in references
            ])
            for index, value in enumerate(selection_x):
                if selection_experts[index] == expert_id:
                    exact_selection[index] = evaluate(value, pointers)
            for index, value in enumerate(development_x):
                if development_experts[index] == expert_id:
                    exact_development[index] = evaluate(value, pointers)
            for atlases, shapes in ((fit_atlases, fit_shapes),
                                    (combined_atlases, combined_shapes)):
                for config_index, ((_, rank, step), shape) in enumerate(
                        zip(configurations, shapes)):
                    for anchor_index, anchor in enumerate(shape["anchors"]):
                        atlases[config_index][expert_id, anchor_index, 0] = evaluate(anchor, pointers)
                        for direction in range(rank):
                            displacement = (step * shape["scale"][direction] *
                                            shape["basis"][direction]).astype(np.float32)
                            plus = evaluate(anchor + displacement, pointers)
                            minus = evaluate(anchor - displacement, pointers)
                            atlases[config_index][expert_id, anchor_index, direction + 1] = (
                                plus - minus
                            ) / (2.0 * step)
            _ = references

    candidates = []
    for config, shape, atlas in zip(configurations, fit_shapes, fit_atlases):
        prediction = predict(atlas, shape, selection_x, selection_experts)
        errors = []
        for index, row in enumerate(selection_rows):
            gate = float(row["gates"][3])
            errors.append(np.linalg.norm(gate * (prediction[index] - exact_selection[index])) /
                          max(np.linalg.norm(selection_outputs[index]), 1e-30))
        anchors, rank, step = config
        bytes_f32 = atlas.size * 4 + shape["basis"].size * 4 + shape["anchors"].size * 4
        candidates.append({
            "anchors": anchors, "activation_rank": rank, "finite_difference_step": step,
            "selection_output_relative_l2_p50": float(np.median(errors)),
            "selection_output_relative_l2_p95": float(np.percentile(errors, 95)),
            "selection_output_relative_l2_max": float(np.max(errors)),
            "layer_atlas_bytes_f32": bytes_f32,
        })
    selected_index = min(range(len(candidates)),
                         key=lambda index: candidates[index]["selection_output_relative_l2_p95"])
    selected = candidates[selected_index]
    atlas = combined_atlases[selected_index]
    shape = combined_shapes[selected_index]
    prediction = predict(atlas, shape, development_x, development_experts)
    development_errors = []
    for index, row in enumerate(development_rows):
        gate = float(row["gates"][3])
        development_errors.append(
            np.linalg.norm(gate * (prediction[index] - exact_development[index])) /
            max(np.linalg.norm(development_outputs[index]), 1e-30)
        )
    timings = []
    for index, row in enumerate(development_rows):
        for _ in range(50):
            started = time.perf_counter_ns()
            _ = predict(atlas, shape, development_x[index:index + 1],
                        development_experts[index:index + 1]) * float(row["gates"][3])
            timings.append((time.perf_counter_ns() - started) / 1e6)
    args.cartridge.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        args.cartridge, atlas=atlas.astype("<f4"), mean=shape["mean"].astype("<f4"),
        activation_basis=shape["basis"].astype("<f4"),
        activation_scale=shape["scale"].astype("<f4"),
        anchors=shape["anchors"].astype("<f4"),
        anchor_coordinates=shape["anchor_coordinates"].astype("<f4"),
    )
    baseline_p95 = float(np.percentile([
        row["counterfactuals"]["3"]["output_relative_l2"] for row in development_rows
    ], 95))
    result_p95 = float(np.percentile(development_errors, 95))
    per_expert_bytes = selected["layer_atlas_bytes_f32"] / EXPERTS
    accepted = {
        "beats_drop_fourth": result_p95 < baseline_p95,
        "under_two_percent_p95": result_p95 <= 0.02,
        "at_least_four_x_smaller_per_expert": per_expert_bytes <= 13_893_632 / 4,
        "under_point_four_ms": float(np.median(timings)) <= 0.4,
    }
    report = {
        "schema": "aion.gptoss-120b-expert-function-taylor-atlas-gate.v1",
        "status": "ADVANCE_TAYLOR_ATLAS" if all(accepted.values()) else "STOP_TAYLOR_ATLAS",
        "created_at": datetime.now(timezone.utc).isoformat(), "quality_track": True,
        "exact_fallback_required": True, "layer": args.layer,
        "fit_family": args.fit_captures.name,
        "selection_family": args.selection_captures.name,
        "development_family": args.development_captures.name,
        "experts_compiled": EXPERTS, "candidates": candidates, "selected": selected,
        "development_output_relative_l2_p50": float(np.median(development_errors)),
        "development_output_relative_l2_p95": result_p95,
        "development_output_relative_l2_max": float(np.max(development_errors)),
        "drop_fourth_development_baseline_p95": baseline_p95,
        "atlas_calculation_ms_p50": float(np.median(timings)),
        "atlas_calculation_ms_p95": float(np.percentile(timings, 95)),
        "exact_expert_calculation_ms_p50": float(np.median(exact_timings)),
        "per_expert_atlas_bytes_f32": per_expert_bytes,
        "projected_36_layer_atlas_bytes_f32": selected["layer_atlas_bytes_f32"] * 36,
        "cartridge_path": str(args.cartridge.resolve()),
        "cartridge_bytes_on_disk": args.cartridge.stat().st_size,
        "cartridge_sha256": digest(args.cartridge), "acceptance": accepted,
        "authorization_sha256": digest(args.authorization),
        "warehouse_manifest_sha256": digest(args.manifest),
        "blind_business_and_writing_opened": False,
        "claim_boundary": (
            "A local Taylor atlas was derived by querying every original SD-backed layer-12 "
            "expert at real activation anchors and finite-difference directions. Configuration "
            "selection used extraction; reasoning was held out for development. This is not "
            "full-model quality or token-speed evidence."
        ),
    }
    report["canonical_sha256"] = canonical(report)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "status": report["status"], "selected": selected,
        "development_p95": result_p95, "baseline_p95": baseline_p95,
        "atlas_ms_p50": report["atlas_calculation_ms_p50"],
        "per_expert_bytes_f32": per_expert_bytes,
        "acceptance": accepted, "canonical_sha256": report["canonical_sha256"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
