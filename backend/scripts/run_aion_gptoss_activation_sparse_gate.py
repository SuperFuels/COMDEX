#!/usr/bin/env python3
"""Screen activation-coordinate sparsity on frozen real GPT-OSS 120B routes."""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import importlib.util
import json
import statistics
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

_STORE_PATH = Path(__file__).parents[1] / "modules/aion_inference/gptoss_expert_frame_store.py"
_SPEC = importlib.util.spec_from_file_location("aion_gptoss_expert_frame_store", _STORE_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError("cannot load GPT-OSS expert frame store")
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
GptOssExpertFrameStore = _MODULE.GptOssExpertFrameStore

WIDTH = 2880


def percentile(values: list[float], fraction: float) -> float:
    return sorted(values)[int(fraction * (len(values) - 1))]


def retain_absolute_mass(values: np.ndarray, fraction: float) -> tuple[np.ndarray, int]:
    magnitudes = np.abs(values.astype(np.float64))
    order = np.argsort(magnitudes)[::-1]
    target = fraction * float(magnitudes.sum())
    keep = int(np.searchsorted(np.cumsum(magnitudes[order]), target, side="left") + 1)
    result = np.zeros_like(values)
    result[order[:keep]] = values[order[:keep]]
    return result, keep


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--activations", type=Path, required=True)
    parser.add_argument("--mass-fractions", default="0.5,0.75,0.9,0.95,0.99")
    parser.add_argument("--threads", type=int, default=8)
    parser.add_argument("--max-captures", type=int)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("refusing to overwrite evidence")
    fractions = [float(value) for value in args.mass_fractions.split(",")]
    if not fractions or any(value <= 0 or value >= 1 for value in fractions):
        raise SystemExit("mass fractions must be between zero and one")
    captures = sorted(args.activations.glob("position-*-layer-*.json"))
    if args.max_captures is not None:
        captures = captures[:args.max_captures]
    if not captures:
        raise SystemExit("no activation captures found")

    store = GptOssExpertFrameStore(args.manifest, 256 * 1024 * 1024)
    native = Path(__file__).parents[1] / "modules/aion_inference/native/gptoss_persistent_moe_library.cpp"
    observations = []
    with tempfile.TemporaryDirectory(prefix="aion-gptoss-activation-sparse-") as temporary:
        library_path = Path(temporary) / "moe.dylib"
        subprocess.run(["clang++", "-std=c++17", "-O3", "-dynamiclib",
                        "-I/opt/homebrew/include", str(native), "-L/opt/homebrew/lib",
                        "-lggml", "-lggml-base", "-ldl", "-o", str(library_path)], check=True)
        loaded = ctypes.CDLL(str(library_path)); function = loaded.aion_gptoss_moe_finish
        function.argtypes = [ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_float),
                             ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(ctypes.c_float),
                             ctypes.POINTER(ctypes.c_float), ctypes.c_int,
                             ctypes.POINTER(ctypes.c_double)]
        function.restype = ctypes.c_int

        def calculate(ffn: np.ndarray, router: np.ndarray, blobs: list[bytes],
                      gates: np.ndarray) -> np.ndarray:
            references = [ctypes.c_char_p(blob) for blob in blobs]
            pointers = (ctypes.c_void_p * len(references))(*[
                ctypes.cast(reference, ctypes.c_void_p).value for reference in references])
            output = np.empty(WIDTH, dtype=np.float32); elapsed = ctypes.c_double()
            status = function(ffn.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                              router.ctypes.data_as(ctypes.POINTER(ctypes.c_float)), pointers,
                              gates.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                              output.ctypes.data_as(ctypes.POINTER(ctypes.c_float)), args.threads,
                              ctypes.byref(elapsed))
            if status:
                raise RuntimeError(f"native MoE status {status}")
            return output

        for index, capture_path in enumerate(captures):
            capture = json.loads(capture_path.read_text()); stem = capture_path.with_suffix("")
            ffn = np.fromfile(Path(str(stem) + "-ffn.bin"), dtype="<f4")
            router = np.fromfile(Path(str(stem) + "-router.bin"), dtype="<f4")
            values = store.get_layer_route_parallel(capture["layer"], capture["route"], workers=4)
            blobs = [value[projection][kind] for value in values
                     for projection in ("gate", "up", "down") for kind in ("weight", "bias")]
            gates = np.asarray(capture["gates"], dtype=np.float32)
            full = calculate(ffn, router, blobs, gates)
            contribution = full.astype(np.float64) - ffn.astype(np.float64)
            candidates = {}
            for fraction in fractions:
                sparse_router, retained = retain_absolute_mass(router, fraction)
                candidate = calculate(ffn, sparse_router, blobs, gates)
                delta = candidate.astype(np.float64) - full.astype(np.float64)
                retained_fraction = retained / WIDTH
                # Gate and up can skip omitted input columns; down remains dense.
                projected_weight_fraction = (2 * retained_fraction + 1) / 3
                candidates[str(fraction)] = {
                    "retained_coordinates": retained,
                    "retained_coordinate_fraction": retained_fraction,
                    "projected_total_expert_weight_fraction": projected_weight_fraction,
                    "projected_expert_weight_traffic_reduction": 1 / projected_weight_fraction,
                    "output_relative_l2": float(np.linalg.norm(delta) / np.linalg.norm(full)),
                    "contribution_relative_l2": float(np.linalg.norm(delta) / np.linalg.norm(contribution)),
                    "output_max_abs": float(np.abs(delta).max()),
                }
            observations.append({"position": capture["position"], "layer": capture["layer"],
                                 "route": capture["route"], "candidates": candidates})
            print(f"capture {index + 1}/{len(captures)}", flush=True)

    summaries = {}
    for candidate_name in observations[0]["candidates"]:
        rows = [row["candidates"][candidate_name] for row in observations]
        summaries[candidate_name] = {
            "samples": len(rows),
            "retained_coordinate_fraction_p50": statistics.median(x["retained_coordinate_fraction"] for x in rows),
            "retained_coordinate_fraction_p95": percentile([x["retained_coordinate_fraction"] for x in rows], .95),
            "projected_traffic_reduction_p50": statistics.median(x["projected_expert_weight_traffic_reduction"] for x in rows),
            "projected_traffic_reduction_p05": min(x["projected_expert_weight_traffic_reduction"] for x in rows),
            "output_relative_l2_p50": statistics.median(x["output_relative_l2"] for x in rows),
            "output_relative_l2_p95": percentile([x["output_relative_l2"] for x in rows], .95),
            "contribution_relative_l2_p50": statistics.median(x["contribution_relative_l2"] for x in rows),
            "contribution_relative_l2_p95": percentile([x["contribution_relative_l2"] for x in rows], .95),
            "output_max_abs_p95": percentile([x["output_max_abs"] for x in rows], .95),
        }
    advancing = [candidate_name for candidate_name, row in summaries.items()
                 if row["projected_traffic_reduction_p05"] >= 1.5
                 and row["output_relative_l2_p95"] <= .02
                 and row["contribution_relative_l2_p95"] <= .15]
    report = {
        "schema": "aion.gptoss-120b-activation-sparse-expert-gate.v1",
        "status": "ADVANCE_SPARSE_COLUMN_KERNEL" if advancing else "STOP_ACTIVATION_SPARSE_COLUMNS",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": "GPT-OSS 120B Q4_K_M/MXFP4", "quality_track": True,
        "mass_fractions": fractions, "observations": observations, "summaries": summaries,
        "advancing_candidates": advancing,
        "promotion_gate": {"minimum_projected_traffic_reduction_p05": 1.5,
                           "maximum_output_relative_l2_p95": .02,
                           "maximum_contribution_relative_l2_p95": .15},
        "warehouse_metrics": store.metrics(),
        "capture_file_hashes": {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                                for path in sorted(args.activations.iterdir())},
        "claim_boundary": (
            "A real-activation simulation zeros low-absolute-mass expert input coordinates while preserving the unrestricted route, original weights, gates and residual. "
            "Traffic reduction assumes a future column-sparse gate/up kernel; the down projection remains dense. No compact store, sparse kernel, token speed or semantic quality is claimed."),
    }
    report["canonical_sha256"] = hashlib.sha256(
        json.dumps(report, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": report["status"], "advancing_candidates": advancing,
                      "summaries": summaries, "canonical_sha256": report["canonical_sha256"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
