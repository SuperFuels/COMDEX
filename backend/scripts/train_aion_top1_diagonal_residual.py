#!/usr/bin/env python3
"""Train a coordinate-aligned top-1 residual expert microcandidate."""
from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import math
import statistics
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from backend.modules.aion_inference.gptoss_expert_frame_store import GptOssExpertFrameStore


WIDTH = 2880
FEATURE_SETS = (
    ("top1",),
    ("top1", "ffn"),
    ("top1", "ffn", "router"),
    ("top1", "ffn", "router", "tail_mass", "gate_entropy"),
)
RIDGES = (1e-3, 1e-2, 1e-1, 1.0, 10.0)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(value: dict) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"),
    ).encode()).hexdigest()


def vector(path: str | Path) -> np.ndarray:
    value = np.fromfile(path, dtype="<f4").astype(np.float64)
    if value.size != WIDTH:
        raise SystemExit(f"capture width mismatch: {path}")
    return value


def relative_l2(candidate: np.ndarray, reference: np.ndarray) -> float:
    return float(np.linalg.norm(candidate - reference) /
                 max(np.linalg.norm(reference), np.finfo(np.float64).tiny))


def feature(row: dict, name: str) -> np.ndarray:
    if name in ("top1", "ffn", "router"):
        return row[name]
    if name == "tail_mass":
        return np.full(WIDTH, 1.0 - row["gates"][0], dtype=np.float64)
    if name == "gate_entropy":
        gates = np.asarray(row["gates"], dtype=np.float64)
        value = -float(np.sum(gates * np.log(np.maximum(gates, 1e-30))))
        return np.full(WIDTH, value, dtype=np.float64)
    raise ValueError(name)


def fit(rows: list[dict], names: tuple[str, ...], ridge: float) -> dict:
    # Shape is [sample, coordinate, feature].  Every output coordinate has its
    # own tiny regression, preserving the residual stream's native addressing.
    values = np.stack([
        np.stack([feature(row, name) for name in names], axis=-1) for row in rows
    ])
    targets = np.stack([row["omitted"] for row in rows])
    mean = values.mean(axis=0)
    scale = np.maximum(values.std(axis=0), 1e-6)
    normalized = (values - mean) / scale
    design = np.concatenate([
        np.ones((*normalized.shape[:2], 1), dtype=np.float64), normalized,
    ], axis=-1)
    dimensions = design.shape[-1]
    gram = np.einsum("nwd,nwe->wde", design, design)
    gram += ridge * np.eye(dimensions, dtype=np.float64)[None, :, :]
    right = np.einsum("nwd,nw->wd", design, targets)
    coefficients = np.linalg.solve(gram, right[..., None])[..., 0]
    return {"names": names, "ridge": ridge, "mean": mean, "scale": scale,
            "coefficients": coefficients}


def predict(model: dict, row: dict) -> np.ndarray:
    values = np.stack([feature(row, name) for name in model["names"]], axis=-1)
    normalized = (values - model["mean"]) / model["scale"]
    design = np.concatenate([
        np.ones((WIDTH, 1), dtype=np.float64), normalized,
    ], axis=-1)
    return np.sum(design * model["coefficients"], axis=-1)


def errors(model: dict, rows: list[dict]) -> tuple[list[float], list[float]]:
    output_errors, omitted_errors = [], []
    for row in rows:
        correction = predict(model, row)
        candidate = row["ffn"] + row["top1"] + correction
        reference = row["ffn"] + row["full"]
        output_errors.append(relative_l2(candidate, reference))
        omitted_errors.append(relative_l2(correction, row["omitted"]))
    return output_errors, omitted_errors


def percentile(values: list[float], fraction: float) -> float:
    return sorted(values)[int(fraction * (len(values) - 1))]


def grouped_cv(rows: list[dict], names: tuple[str, ...], ridge: float) -> tuple[float, float]:
    output_errors, omitted_errors = [], []
    for family in sorted({row["family_id"] for row in rows}):
        training = [row for row in rows if row["family_id"] != family]
        validation = [row for row in rows if row["family_id"] == family]
        if len(training) <= len(names) + 1:
            continue
        model = fit(training, names, ridge)
        output, omitted = errors(model, validation)
        output_errors.extend(output); omitted_errors.extend(omitted)
    if not output_errors:
        return math.inf, math.inf
    return percentile(output_errors, .95), percentile(omitted_errors, .95)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--captures", type=Path, required=True)
    parser.add_argument("--authorization", type=Path, required=True)
    parser.add_argument("--cartridge", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--threads", type=int, default=6)
    args = parser.parse_args()
    if args.output.exists() or args.cartridge.exists():
        raise SystemExit("refusing to overwrite evidence")
    authorization = json.loads(args.authorization.read_text())
    if (authorization.get("schema") !=
            "aion.gptoss-120b-residual-training-authorization.v1"
            or authorization.get("authorized") is not True):
        raise SystemExit("explicit residual training authorization is absent")
    captures = json.loads(args.captures.read_text())
    if captures.get("status") != "READY_FOR_AUTHORIZED_TRAINING":
        raise SystemExit("capture manifest is not training-ready")
    split_by_family = {
        family: split for split, families in captures["family_disjoint_split"].items()
        for family in families
    }

    native = (Path(__file__).parents[1] /
              "modules/aion_inference/native/gptoss_persistent_moe_library.cpp")
    store = GptOssExpertFrameStore(args.manifest, 512 * 1024 * 1024)
    rows = []
    with tempfile.TemporaryDirectory(prefix="aion-diagonal-residual-") as temporary:
        library_path = Path(temporary) / "moe.dylib"
        subprocess.run([
            "clang++", "-std=c++17", "-O3", "-dynamiclib",
            "-I/opt/homebrew/include", str(native), "-L/opt/homebrew/lib",
            "-lggml", "-lggml-base", "-ldl", "-o", str(library_path),
        ], check=True)
        loaded = ctypes.CDLL(str(library_path))
        function = loaded.aion_gptoss_moe_finish_active
        function.argtypes = [
            ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_float),
            ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(ctypes.c_float),
            ctypes.c_int, ctypes.POINTER(ctypes.c_float), ctypes.c_int,
            ctypes.POINTER(ctypes.c_double),
        ]
        function.restype = ctypes.c_int
        for family in captures["families"]:
            for record in family["records"]:
                for name in ("ffn", "router", "residual"):
                    path = Path(record[f"{name}_path"])
                    if digest(path) != record[f"{name}_sha256"]:
                        raise SystemExit(f"{name} hash mismatch: {path}")
                ffn = vector(record["ffn_path"])
                router = vector(record["router_path"])
                full = vector(record["residual_path"])
                value = store.get_layer_route_parallel(
                    record["layer"], record["route"][:1], workers=1,
                )[0]
                blobs = [value[projection][kind]
                         for projection in ("gate", "up", "down")
                         for kind in ("weight", "bias")]
                references = [ctypes.c_char_p(blob) for blob in blobs]
                pointers = (ctypes.c_void_p * len(references))(*[
                    ctypes.cast(reference, ctypes.c_void_p).value
                    for reference in references
                ])
                gates = np.asarray(record["gates"][:1], dtype=np.float32)
                top1_output = np.empty(WIDTH, dtype=np.float32)
                elapsed = ctypes.c_double()
                status = function(
                    ffn.astype(np.float32).ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                    router.astype(np.float32).ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                    pointers, gates.ctypes.data_as(ctypes.POINTER(ctypes.c_float)), 1,
                    top1_output.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                    args.threads, ctypes.byref(elapsed),
                )
                if status:
                    raise RuntimeError(f"native top-1 status {status}")
                top1 = top1_output.astype(np.float64) - ffn
                rows.append({
                    "family_id": family["family_id"],
                    "split": split_by_family[family["family_id"]],
                    "position": record["position"], "layer": record["layer"],
                    "route": record["route"], "gates": record["gates"],
                    "ffn": ffn, "router": router, "top1": top1,
                    "full": full, "omitted": full - top1,
                    "top1_compute_ms": elapsed.value,
                })

    selections, observations, models, timings = [], [], {}, []
    for layer in sorted({row["layer"] for row in rows}):
        training = [row for row in rows if row["layer"] == layer and row["split"] == "train"]
        best = min(
            ((grouped_cv(training, names, ridge), names, ridge)
             for names in FEATURE_SETS for ridge in RIDGES),
            key=lambda item: item[0],
        )
        cv_score, names, ridge = best
        model = fit(training, names, ridge); models[layer] = model
        selections.append({
            "layer": layer, "features": list(names), "ridge": ridge,
            "training_group_cv_output_relative_l2_p95": cv_score[0],
            "training_group_cv_omitted_relative_l2_p95": cv_score[1],
        })
        for row in [item for item in rows if item["layer"] == layer]:
            output, omitted = errors(model, [row])
            top1_output = relative_l2(row["ffn"] + row["top1"], row["ffn"] + row["full"])
            observations.append({
                "layer": layer, "family_id": row["family_id"],
                "split": row["split"], "position": row["position"],
                "route": row["route"], "top1_output_relative_l2": top1_output,
                "corrected_output_relative_l2": output[0],
                "corrected_omitted_relative_l2": omitted[0],
            })
        sample = training[0]
        for _ in range(100):
            began = time.perf_counter_ns(); predict(model, sample)
            timings.append((time.perf_counter_ns() - began) / 1e6)

    holdout = [row for row in observations if row["split"] in
               ("numerical_holdout", "semantic_holdout")]
    calibration = [row for row in observations if row["split"] == "calibration"]
    holdout_output = [row["corrected_output_relative_l2"] for row in holdout]
    holdout_omitted = [row["corrected_omitted_relative_l2"] for row in holdout]
    holdout_top1 = [row["top1_output_relative_l2"] for row in holdout]
    output_p95 = percentile(holdout_output, .95)
    omitted_p95 = percentile(holdout_omitted, .95)
    improvement = statistics.median(holdout_top1) / statistics.median(holdout_output)
    strict_pass = output_p95 <= .02 and omitted_p95 <= .15
    development_advance = output_p95 <= .05 and improvement >= 1.30
    status = ("ADVANCE_CAUSAL_INTEGRATION" if strict_pass else
              "ADVANCE_RESIDUAL_CAPACITY" if development_advance else
              "STOP_DIAGONAL_RESIDUAL")

    args.cartridge.mkdir(parents=True, exist_ok=False)
    files = {}
    for layer, model in models.items():
        for name in ("mean", "scale", "coefficients"):
            path = args.cartridge / f"layer-{layer}-{name}-f32.bin"
            np.asarray(model[name], dtype=np.float32).tofile(path)
            files[path.name] = {"sha256": digest(path),
                                "shape": list(np.asarray(model[name]).shape)}
    receipt = {
        "schema": "aion.top1-diagonal-residual-cartridge.v1",
        "quality_track": True, "exact_fallback_required": True,
        "source_manifest_canonical_sha256": captures["canonical_sha256"],
        "authorization_sha256": digest(args.authorization),
        "selections": selections, "files": files,
    }
    receipt["canonical_sha256"] = canonical(receipt)
    receipt_path = args.cartridge / "cartridge.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    report = {
        "schema": "aion.gptoss-120b-top1-diagonal-residual-gate.v1",
        "status": status, "created_at": datetime.now(timezone.utc).isoformat(),
        "model": "GPT-OSS 120B Q4_K_M/MXFP4", "quality_track": True,
        "exact_fallback_required": True,
        "source_manifest_canonical_sha256": captures["canonical_sha256"],
        "authorization_sha256": digest(args.authorization),
        "selection_used_training_group_cv_only": True,
        "training_rows": sum(row["split"] == "train" for row in rows),
        "calibration_rows": len(calibration), "holdout_rows": len(holdout),
        "selection": selections, "observations": observations,
        "holdout_output_relative_l2_p50": statistics.median(holdout_output),
        "holdout_output_relative_l2_p95": output_p95,
        "holdout_omitted_relative_l2_p95": omitted_p95,
        "holdout_median_improvement_over_top1": improvement,
        "calculation_ms_p50": statistics.median(timings),
        "calculation_ms_p95": percentile(timings, .95),
        "cartridge_bytes": sum(Path(args.cartridge, name).stat().st_size for name in files),
        "cartridge_receipt_sha256": digest(receipt_path),
        "warehouse_metrics": store.metrics(),
        "promotion_gate": {
            "maximum_holdout_output_relative_l2_p95": .02,
            "maximum_holdout_omitted_relative_l2_p95": .15,
            "development_maximum_output_relative_l2_p95": .05,
            "development_minimum_median_improvement_over_top1": 1.30,
        },
        "claim_boundary": (
            "Authorized training-only coordinate-aligned residual microgate over "
            "twelve sampled layers. One original top-1 expert is calculated and a "
            "small learned correction approximates the combined contribution of "
            "experts two through four. Disjoint family holdouts are never used for "
            "selection. This is changed arithmetic, not generated-token speed, "
            "semantic quality, or exact GPT-OSS 120B evidence."
        ),
    }
    report["canonical_sha256"] = canonical(report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "status": status, "holdout_output_p95": output_p95,
        "holdout_omitted_p95": omitted_p95, "improvement": improvement,
        "calculation_ms_p50": report["calculation_ms_p50"],
        "cartridge_bytes": report["cartridge_bytes"],
        "canonical_sha256": report["canonical_sha256"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
