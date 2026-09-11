#!/usr/bin/env python3
"""Compile a compact correction for a selectively compact fourth expert."""
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

from backend.modules.aion_inference.gptoss_expert_frame_store import (
    GptOssExpertFrameStore, ctypes_component_pointer_array,
)
from backend.scripts.run_aion_expert_function_atlas_gate import digest, load_capture


WIDTH = 2880


def load_ffn(root: Path, rows: list[dict], layer: int) -> np.ndarray:
    values = []
    for row in rows:
        path = root / f"position-{row['position']}-layer-{layer}-ffn.bin"
        if digest(path) != row["ffn_sha256"]:
            raise SystemExit(f"capture hash mismatch: {path}")
        values.append(np.fromfile(path, dtype="<f4"))
    return np.stack(values)


def geometry(values: np.ndarray, rank: int) -> tuple[np.ndarray, np.ndarray]:
    mean = values.mean(axis=0, dtype=np.float64)
    _, _, basis = np.linalg.svd(values.astype(np.float64) - mean,
                                full_matrices=False)
    return mean, basis[:rank]


def fit_model(features: np.ndarray, residuals: np.ndarray, input_rank: int,
              output_rank: int, ridge: float) -> dict:
    input_rank = min(input_rank, len(features) - 1)
    output_rank = min(output_rank, len(residuals) - 1)
    input_mean, input_basis = geometry(features, input_rank)
    output_mean, output_basis = geometry(residuals, output_rank)
    x = (features - input_mean) @ input_basis.T
    y = (residuals - output_mean) @ output_basis.T
    design = np.concatenate((np.ones((len(x), 1)), x), axis=1)
    regularizer = ridge * np.eye(design.shape[1])
    regularizer[0, 0] = 0.0
    coefficients = np.linalg.solve(
        design.T @ design + regularizer, design.T @ y,
    )
    return {
        "input_mean": input_mean, "input_basis": input_basis,
        "output_mean": output_mean, "output_basis": output_basis,
        "coefficients": coefficients,
    }


def predict(model: dict, features: np.ndarray) -> np.ndarray:
    x = (features - model["input_mean"]) @ model["input_basis"].T
    design = np.concatenate((np.ones((len(x), 1)), x), axis=1)
    return model["output_mean"] + design @ model["coefficients"] @ model["output_basis"]


def summarize(candidate: np.ndarray, target: np.ndarray) -> dict:
    errors = np.linalg.norm(candidate - target, axis=1) / np.maximum(
        np.linalg.norm(target, axis=1), 1e-30,
    )
    return {
        "rows": len(errors), "output_relative_l2_p50": float(np.median(errors)),
        "output_relative_l2_p95": float(np.percentile(errors, 95)),
        "output_relative_l2_max": float(np.max(errors)),
        "rows_at_or_below_two_percent": int(np.sum(errors <= 0.02)),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--authorization", type=Path, required=True)
    parser.add_argument("--fit-captures", type=Path, required=True)
    parser.add_argument("--selection-captures", type=Path, required=True)
    parser.add_argument("--development-captures", type=Path, required=True)
    parser.add_argument("--layer", type=int, default=12)
    parser.add_argument("--threads", type=int, default=6)
    parser.add_argument("--base-representation",
                        choices=("q2_0", "q3_k_gate_up"), default="q2_0")
    parser.add_argument("--cartridge", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.cartridge.exists():
        raise SystemExit("refusing to overwrite evidence")
    if json.loads(args.authorization.read_text()).get("authorized") is not True:
        raise SystemExit("explicit residual training authorization is absent")

    roots = (args.fit_captures, args.selection_captures, args.development_captures)
    loaded = [load_capture(root, args.layer) for root in roots]
    rows = [item[0] for item in loaded]
    routers = [item[1] for item in loaded]
    targets = [item[2] for item in loaded]
    ffn = [load_ffn(root, family_rows, args.layer)
           for root, family_rows in zip(roots, rows)]
    compact_outputs = [np.empty_like(target) for target in targets]
    compact_ms = []

    store = GptOssExpertFrameStore(args.manifest, 512 * 1024 * 1024)
    native = Path(__file__).parents[1] / "modules/aion_inference/native"
    with tempfile.TemporaryDirectory(prefix="aion-q2-error-correction-") as temporary:
        temporary_root = Path(temporary)
        converter = temporary_root / "convert"
        library_path = temporary_root / "moe.dylib"
        common = ["clang++", "-std=c++17", "-O3", "-I/opt/homebrew/include"]
        libraries = ["-L/opt/homebrew/lib", "-lggml", "-lggml-base", "-ldl"]
        converter_source = ("gptoss_mxfp4_to_q2_0.cpp"
                            if args.base_representation == "q2_0"
                            else "gptoss_mxfp4_to_padded_k.cpp")
        subprocess.run([*common, str(native / converter_source),
                        *libraries, "-o", str(converter)], check=True)
        subprocess.run([*common, "-dynamiclib",
                        str(native / "gptoss_persistent_moe_library.cpp"),
                        *libraries, "-o", str(library_path)], check=True)
        loaded_library = ctypes.CDLL(str(library_path))
        function = (loaded_library.aion_gptoss_moe_finish_top3_mxfp4_q2_0
                    if args.base_representation == "q2_0" else
                    loaded_library.aion_gptoss_moe_finish_top3_mxfp4_q3_k)
        signature = [
            ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_float),
            ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(ctypes.c_float),
            ctypes.POINTER(ctypes.c_float), ctypes.c_int,
            ctypes.POINTER(ctypes.c_double),
        ]
        function.argtypes = (signature if args.base_representation == "q2_0"
                             else signature[:4] + [ctypes.c_int] + signature[4:])
        function.restype = ctypes.c_int
        converted: dict[tuple[int, str], bytes] = {}
        for family_index, family_rows in enumerate(rows):
            for row_index, row in enumerate(family_rows):
                experts = store.get_layer_route_parallel(
                    args.layer, row["route"], workers=4,
                )
                blobs = []
                for route_position, (expert_id, expert) in enumerate(
                        zip(row["route"], experts)):
                    for projection in ("gate", "up", "down"):
                        weight = expert[projection]["weight"]
                        compact_projection = (route_position == 3 and
                                              (args.base_representation == "q2_0"
                                               or projection in ("gate", "up")))
                        if compact_projection:
                            key = (int(expert_id), projection)
                            if key not in converted:
                                source = temporary_root / f"e{key[0]}-{projection}-mxfp4.bin"
                                suffix = ("q2" if args.base_representation == "q2_0"
                                          else "q3k")
                                destination = temporary_root / f"e{key[0]}-{projection}-{suffix}.bin"
                                source.write_bytes(weight)
                                converter_arguments = ([
                                    str(converter), str(source), str(destination),
                                    str(WIDTH), str(args.threads),
                                ] if args.base_representation == "q2_0" else [
                                    str(converter), str(source), str(destination),
                                    "q3_k", str(WIDTH), str(args.threads),
                                ])
                                subprocess.run(converter_arguments, check=True,
                                               stdout=subprocess.DEVNULL)
                                converted[key] = destination.read_bytes()
                            weight = converted[key]
                        bias = expert[projection]["bias"]
                        if compact_projection and args.base_representation == "q3_k_gate_up":
                            bias = bytes(bias) + bytes((3072 - WIDTH) * 4)
                        blobs.extend((weight, bias))
                references, pointers = ctypes_component_pointer_array(blobs)
                gates = np.asarray(row["gates"], dtype=np.float32)
                elapsed = ctypes.c_double()
                output = compact_outputs[family_index][row_index]
                prefix = [ffn[family_index][row_index].ctypes.data_as(
                              ctypes.POINTER(ctypes.c_float)),
                          routers[family_index][row_index].ctypes.data_as(
                              ctypes.POINTER(ctypes.c_float)), pointers,
                          gates.ctypes.data_as(ctypes.POINTER(ctypes.c_float))]
                suffix = [output.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                          args.threads, ctypes.byref(elapsed)]
                status = function(*prefix,
                                  *([3] if args.base_representation == "q3_k_gate_up"
                                    else []), *suffix)
                if status:
                    raise RuntimeError(f"top3/Q2 native status {status}")
                compact_ms.append(elapsed.value)
                _ = references

    # The correction sees only values already available on this path: router
    # activation, compact layer output, and four original router gates.
    features = [np.concatenate((router, compact,
                               np.asarray([row["gates"] for row in family_rows])), axis=1)
                for router, compact, family_rows in zip(routers, compact_outputs, rows)]
    residuals = [target.astype(np.float64) - compact.astype(np.float64)
                 for target, compact in zip(targets, compact_outputs)]
    baselines = [summarize(compact, target)
                 for compact, target in zip(compact_outputs, targets)]
    configurations = [(4, 4, 1e-3), (8, 8, 1e-3), (16, 8, 1e-3),
                      (16, 16, 1e-3), (24, 16, 1e-2), (32, 24, 1e-2)]
    candidates = []
    for input_rank, output_rank, ridge in configurations:
        model = fit_model(features[0], residuals[0], input_rank, output_rank, ridge)
        corrected = compact_outputs[1] + predict(model, features[1])
        candidates.append({
            "input_rank": input_rank, "output_rank": output_rank, "ridge": ridge,
            **summarize(corrected, targets[1]),
        })
    passing = [item for item in candidates if item["output_relative_l2_max"] <= 0.02]
    selected = (min(passing, key=lambda item: (item["input_rank"] + item["output_rank"]))
                if passing else min(candidates,
                                    key=lambda item: item["output_relative_l2_p95"]))
    combined_features = np.concatenate((features[0], features[1]))
    combined_residuals = np.concatenate((residuals[0], residuals[1]))
    model = fit_model(combined_features, combined_residuals,
                      int(selected["input_rank"]), int(selected["output_rank"]),
                      float(selected["ridge"]))
    development_prediction = predict(model, features[2])
    development = summarize(
        compact_outputs[2] + development_prediction, targets[2],
    )
    selection_improvement = (baselines[1]["output_relative_l2_p95"] /
                             selected["output_relative_l2_p95"])
    development_improvement = (baselines[2]["output_relative_l2_p95"] /
                               development["output_relative_l2_p95"])
    timing = []
    for _ in range(200):
        started = time.perf_counter_ns()
        _ = predict(model, features[2][:1])
        timing.append((time.perf_counter_ns() - started) / 1e6)
    np.savez_compressed(args.cartridge, **{
        key: np.asarray(value, dtype="<f4") for key, value in model.items()
    })
    accepted = {
        "selection_max_at_or_below_two_percent":
            selected["output_relative_l2_max"] <= 0.02,
        "development_p95_at_or_below_two_percent":
            development["output_relative_l2_p95"] <= 0.02,
        "development_max_at_or_below_two_percent":
            development["output_relative_l2_max"] <= 0.02,
        "selection_p95_improves_by_ten_percent": selection_improvement >= 1.10,
        "development_p95_improves_by_ten_percent": development_improvement >= 1.10,
        "correction_under_point_four_ms": float(np.median(timing)) <= 0.4,
        "cartridge_under_four_mib": args.cartridge.stat().st_size <= 4 * 1024 * 1024,
    }
    report = {
        "schema": "aion.gptoss-120b-compact-error-correction-gate.v2",
        "status": "ADVANCE_COMPACT_ERROR_CORRECTION" if all(accepted.values())
                  else "STOP_COMPACT_ERROR_CORRECTION",
        "created_at": datetime.now(timezone.utc).isoformat(), "quality_track": True,
        "layer": args.layer, "retained_original_experts": 3,
        "base_representation": args.base_representation,
        "compact_experts": 1, "candidates": candidates, "selected": selected,
        "baseline_summaries": {roots[index].name: baseline
                               for index, baseline in enumerate(baselines)},
        "selection_p95_improvement": selection_improvement,
        "development_p95_improvement": development_improvement,
        "development": development, "acceptance": accepted,
        "compact_route_ms_p50": float(np.median(compact_ms)),
        "correction_ms_p50": float(np.median(timing)),
        "correction_ms_p95": float(np.percentile(timing, 95)),
        "cartridge_bytes": args.cartridge.stat().st_size,
        "cartridge_sha256": digest(args.cartridge),
        "fit_family": roots[0].name, "selection_family": roots[1].name,
        "development_family": roots[2].name,
        "blind_business_and_writing_opened": False,
        "exact_fallback_required": True,
        "authorization_sha256": digest(args.authorization),
        "warehouse_manifest_sha256": digest(args.manifest),
        "claim_boundary": (
            "Layer-12 changed-weight quality microgate. Three experts remain original MXFP4; "
            "the fourth uses the declared compact representation plus a correction trained "
            "only on that representation's error. Extraction "
            "selects capacity and reasoning is unseen development. This is not full-model "
            "quality or generated-token speed evidence."
        ),
    }
    report["canonical_sha256"] = hashlib.sha256(json.dumps(
        report, sort_keys=True, separators=(",", ":"),
    ).encode()).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "status": report["status"], "selected": selected,
        "development": development, "acceptance": accepted,
        "canonical_sha256": report["canonical_sha256"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
