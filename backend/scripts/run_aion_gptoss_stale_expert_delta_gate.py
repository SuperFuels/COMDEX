#!/usr/bin/env python3
"""Test stale-state expert arithmetic plus a tiny learned delta correction.

The candidate computes the real rank-four expert at layer L from the previous
layer's already-available post-attention state.  A compact shared linear map
then predicts only the difference to the same expert evaluated at the final
layer-L router input.  This is a quality-track microgate; uncertified rows must
fall back to the original expert calculation.
"""
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

from backend.modules.aion_inference.expert_frame_gguf_reader import ExpertFrameGGUFReader
from backend.modules.aion_inference.gguf_stream_index import read_gguf_stream_index
from backend.modules.aion_inference.gptoss_expert_frame_store import GptOssExpertFrameStore


WIDTH = 2880
EPSILON = np.float32(1.0e-5)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(value: dict) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
    ).encode()).hexdigest()


def rms_norm(values: np.ndarray, weight: np.ndarray) -> np.ndarray:
    mean_square = np.mean(values * values, dtype=np.float32)
    return values * np.float32(1.0 / np.sqrt(mean_square + EPSILON)) * weight


def load_norm(manifest_path: Path, layer: int) -> np.ndarray:
    manifest = json.loads(manifest_path.read_text())
    name = f"blk.{layer}.post_attention_norm.weight"
    for source in manifest["verified_sources"]:
        reader = ExpertFrameGGUFReader(manifest_path, source["name"], 64 * 1024 * 1024)
        index = read_gguf_stream_index(reader, int(source["size"]))
        for tensor in index["tensors"]:
            if tensor["name"] == name:
                if int(tensor["ggml_type"]) != 0:
                    raise SystemExit(f"{name} is not F32")
                raw = reader.read_at(int(tensor["absolute_offset"]), int(tensor["byte_length"]))
                return np.frombuffer(raw, dtype="<f4").copy()
    raise SystemExit(f"missing tensor {name}")


def capture_rows(root: Path, layer: int, norm: np.ndarray) -> list[dict]:
    rows = []
    paths = sorted(root.glob(f"position-*-layer-{layer}.json"),
                   key=lambda path: int(path.name.split("-")[1]))
    for path in paths:
        metadata = json.loads(path.read_text())
        position = int(metadata["position"])
        actual_path = path.with_name(path.stem + "-router.bin")
        previous_path = root / f"position-{position}-layer-{layer - 1}-ffn.bin"
        output_path = path.with_name(path.stem + "-output.bin")
        for binary in (actual_path, previous_path, output_path):
            if not binary.exists():
                raise SystemExit(f"missing capture {binary}")
        actual = np.fromfile(actual_path, dtype="<f4")
        previous = np.fromfile(previous_path, dtype="<f4")
        output = np.fromfile(output_path, dtype="<f4")
        if actual.size != WIDTH or previous.size != WIDTH or output.size != WIDTH:
            raise SystemExit(f"capture width mismatch at {path}")
        rows.append({
            "metadata_path": path, "metadata": metadata,
            "actual": actual, "stale": rms_norm(previous, norm), "output": output,
        })
    if not rows:
        raise SystemExit(f"no layer {layer} captures in {root}")
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--authorization", type=Path, required=True)
    parser.add_argument("--train-captures", type=Path, required=True)
    parser.add_argument("--holdout-captures", type=Path, required=True)
    parser.add_argument("--layer", type=int, default=12)
    parser.add_argument("--rank", type=int, default=4)
    parser.add_argument("--threads", type=int, default=6)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("refusing to overwrite evidence")
    authorization = json.loads(args.authorization.read_text())
    if authorization.get("authorized") is not True:
        raise SystemExit("explicit residual training authorization is absent")
    if args.layer <= 0 or args.rank < 1:
        raise SystemExit("layer must be positive and rank must be positive")

    norm = load_norm(args.manifest, args.layer)
    train = capture_rows(args.train_captures, args.layer, norm)
    holdout = capture_rows(args.holdout_captures, args.layer, norm)
    store = GptOssExpertFrameStore(args.manifest, 512 * 1024 * 1024)
    source = Path(__file__).parents[1] / "modules/aion_inference/native/gptoss_persistent_moe_library.cpp"

    with tempfile.TemporaryDirectory(prefix="aion-stale-expert-delta-") as temporary:
        library_path = Path(temporary) / "moe.dylib"
        subprocess.run([
            "clang++", "-std=c++17", "-O3", "-dynamiclib", "-I/opt/homebrew/include",
            str(source), "-L/opt/homebrew/lib", "-lggml", "-lggml-base", "-ldl",
            "-o", str(library_path),
        ], check=True)
        library = ctypes.CDLL(str(library_path))
        function = library.aion_gptoss_one_expert_contribution_reuse_graph
        function.argtypes = [
            ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_void_p),
            ctypes.c_float, ctypes.POINTER(ctypes.c_float), ctypes.c_int,
            ctypes.POINTER(ctypes.c_double),
        ]
        function.restype = ctypes.c_int

        def calculate(activation: np.ndarray, expert_id: int) -> tuple[np.ndarray, float]:
            expert = store.get_layer_route_parallel(args.layer, [expert_id], workers=1)[0]
            blobs = [expert[projection][kind] for projection in ("gate", "up", "down")
                     for kind in ("weight", "bias")]
            references = [ctypes.c_char_p(blob) for blob in blobs]
            pointers = (ctypes.c_void_p * 6)(*[
                ctypes.cast(reference, ctypes.c_void_p).value for reference in references
            ])
            destination = np.empty(WIDTH, dtype=np.float32)
            elapsed = ctypes.c_double()
            status = function(
                activation.ctypes.data_as(ctypes.POINTER(ctypes.c_float)), pointers,
                ctypes.c_float(1.0),
                destination.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                args.threads, ctypes.byref(elapsed),
            )
            if status:
                raise RuntimeError(f"expert contribution status {status}")
            _ = references
            return destination, elapsed.value

        timings = []
        for row in train + holdout:
            expert_id = int(row["metadata"]["route"][3])
            row["stale_y"], stale_time = calculate(row["stale"], expert_id)
            row["actual_y"], actual_time = calculate(row["actual"], expert_id)
            timings.extend((stale_time, actual_time))

    train_dx = np.stack([row["actual"] - row["stale"] for row in train]).astype(np.float64)
    train_dy = np.stack([row["actual_y"] - row["stale_y"] for row in train]).astype(np.float64)
    holdout_dx = np.stack([row["actual"] - row["stale"] for row in holdout]).astype(np.float64)
    effective_rank = min(args.rank, len(train) - 1, WIDTH)
    x_mean = train_dx.mean(0)
    y_mean = train_dy.mean(0)
    _, _, x_basis = np.linalg.svd(train_dx - x_mean, full_matrices=False)
    _, _, y_basis = np.linalg.svd(train_dy - y_mean, full_matrices=False)
    x_basis = x_basis[:effective_rank]
    y_basis = y_basis[:effective_rank]
    design = np.concatenate([
        np.ones((len(train), 1)), (train_dx - x_mean) @ x_basis.T,
    ], axis=1)
    target = (train_dy - y_mean) @ y_basis.T
    ridge = 1e-3
    mapping = np.linalg.solve(
        design.T @ design + ridge * np.eye(design.shape[1]), design.T @ target,
    )

    started = time.perf_counter()
    holdout_design = np.concatenate([
        np.ones((len(holdout), 1)), (holdout_dx - x_mean) @ x_basis.T,
    ], axis=1)
    predicted_delta = holdout_design @ mapping @ y_basis + y_mean
    correction_ms = (time.perf_counter() - started) * 1000.0 / len(holdout)

    observations = []
    for row, correction in zip(holdout, predicted_delta, strict=True):
        gate = float(row["metadata"]["gates"][3])
        baseline_delta = gate * (row["stale_y"].astype(np.float64)
                                 - row["actual_y"].astype(np.float64))
        corrected_delta = gate * (row["stale_y"].astype(np.float64) + correction
                                  - row["actual_y"].astype(np.float64))
        denominator = max(float(np.linalg.norm(row["output"])), 1e-30)
        observations.append({
            "capture": row["metadata_path"].name,
            "expert": int(row["metadata"]["route"][3]), "gate": gate,
            "stale_input_relative_l2": float(np.linalg.norm(
                row["actual"] - row["stale"]) / max(np.linalg.norm(row["actual"]), 1e-30)),
            "uncorrected_layer_output_relative_l2": float(np.linalg.norm(baseline_delta) / denominator),
            "corrected_layer_output_relative_l2": float(np.linalg.norm(corrected_delta) / denominator),
        })

    uncorrected = [row["uncorrected_layer_output_relative_l2"] for row in observations]
    corrected = [row["corrected_layer_output_relative_l2"] for row in observations]
    certified = [value <= .02 for value in corrected]
    cartridge_bytes = int((x_mean.size + y_mean.size + x_basis.size + y_basis.size
                           + mapping.size) * 4)
    p95 = float(np.percentile(corrected, 95))
    coverage = float(np.mean(certified))
    status = "ADVANCE_STALE_DELTA" if p95 <= .02 and coverage >= .5 else "STOP_STALE_DELTA"
    report = {
        "schema": "aion.gptoss-120b-stale-expert-delta-gate.v1",
        "created_at": datetime.now(timezone.utc).isoformat(), "status": status,
        "model": "GPT-OSS 120B Q4_K_M", "quality_track": True,
        "layer": args.layer, "selected_expert_rank": 4,
        "train_capture": str(args.train_captures.resolve()),
        "holdout_capture": str(args.holdout_captures.resolve()),
        "train_samples": len(train), "holdout_samples": len(holdout),
        "requested_rank": args.rank, "effective_rank": effective_rank,
        "cartridge_bytes": cartridge_bytes,
        "median_original_expert_calculation_ms": float(np.median(timings) * 1000.0),
        "correction_calculation_ms_per_row": correction_ms,
        "uncorrected_p50": float(np.median(uncorrected)),
        "uncorrected_p95": float(np.percentile(uncorrected, 95)),
        "corrected_p50": float(np.median(corrected)),
        "corrected_p95": p95, "corrected_max": float(np.max(corrected)),
        "certified_rows": int(sum(certified)), "coverage": coverage,
        "promotion_gate": {"maximum_corrected_p95": .02, "minimum_coverage": .5},
        "observations": observations,
        "warehouse_metrics": store.metrics(),
        "claim_boundary": (
            "Layer-12 rank-four quality-track microgate only. The stale expert uses the "
            "previous layer post-attention state and original selected expert weights. The "
            "small delta map is trained only on the declared development family. A failed or "
            "uncertified row requires exact fallback. This is not generated-token throughput, "
            "full-model quality, or unrestricted exact inference evidence."
        ),
    }
    report["canonical_sha256"] = canonical(report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: report[key] for key in (
        "status", "cartridge_bytes", "uncorrected_p95", "corrected_p95",
        "certified_rows", "coverage", "canonical_sha256",
    )}, indent=2))


if __name__ == "__main__":
    main()
