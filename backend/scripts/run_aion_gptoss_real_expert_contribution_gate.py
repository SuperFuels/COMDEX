#!/usr/bin/env python3
"""Measure top-k expert omission on captured real GPT-OSS 120B activations."""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import statistics
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from backend.modules.aion_inference.gptoss_expert_frame_store import GptOssExpertFrameStore


WIDTH = 2880


def percentile(values: list[float], fraction: float) -> float:
    return sorted(values)[int(fraction * (len(values) - 1))]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--activations", type=Path, required=True)
    parser.add_argument("--threads", type=int, default=8)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("refusing to overwrite evidence")
    captures = sorted(args.activations.glob("position-*-layer-*.json"))
    if not captures:
        raise SystemExit("no activation captures found")
    store = GptOssExpertFrameStore(args.manifest, 256 * 1024 * 1024)
    native = Path(__file__).parents[1] / "modules/aion_inference/native/gptoss_persistent_moe_library.cpp"
    observations = []
    with tempfile.TemporaryDirectory(prefix="aion-gptoss-contribution-") as temporary:
        library_path = Path(temporary) / "moe.dylib"
        subprocess.run([
            "clang++", "-std=c++17", "-O3", "-dynamiclib", "-I/opt/homebrew/include",
            str(native), "-L/opt/homebrew/lib", "-lggml", "-lggml-base", "-ldl",
            "-o", str(library_path),
        ], check=True)
        loaded = ctypes.CDLL(str(library_path))
        function = loaded.aion_gptoss_moe_finish
        function.argtypes = [ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_float),
                             ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(ctypes.c_float),
                             ctypes.POINTER(ctypes.c_float), ctypes.c_int,
                             ctypes.POINTER(ctypes.c_double)]
        function.restype = ctypes.c_int

        def calculate(ffn: np.ndarray, router: np.ndarray, pointers, gates: np.ndarray) -> np.ndarray:
            output = np.empty(WIDTH, dtype=np.float32); elapsed = ctypes.c_double()
            status = function(ffn.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                              router.ctypes.data_as(ctypes.POINTER(ctypes.c_float)), pointers,
                              gates.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                              output.ctypes.data_as(ctypes.POINTER(ctypes.c_float)), args.threads,
                              ctypes.byref(elapsed))
            if status:
                raise RuntimeError(f"native MoE status {status}")
            return output

        for capture_path in captures:
            capture = json.loads(capture_path.read_text())
            stem = capture_path.with_suffix("")
            ffn = np.fromfile(Path(str(stem) + "-ffn.bin"), dtype="<f4")
            router = np.fromfile(Path(str(stem) + "-router.bin"), dtype="<f4")
            if ffn.size != WIDTH or router.size != WIDTH:
                raise RuntimeError("capture width mismatch")
            if hashlib.sha256(ffn.tobytes()).hexdigest() != capture["ffn_sha256"]:
                raise RuntimeError("FFN capture hash mismatch")
            if hashlib.sha256(router.tobytes()).hexdigest() != capture["router_sha256"]:
                raise RuntimeError("router capture hash mismatch")
            values = store.get_layer_route_parallel(capture["layer"], capture["route"], workers=4)
            blobs = [value[projection][kind] for value in values
                     for projection in ("gate", "up", "down")
                     for kind in ("weight", "bias")]
            references = [ctypes.c_char_p(blob) for blob in blobs]
            pointers = (ctypes.c_void_p * len(references))(*[
                ctypes.cast(reference, ctypes.c_void_p).value for reference in references])
            full_gates = np.asarray(capture["gates"], dtype=np.float32)
            full = calculate(ffn, router, pointers, full_gates)
            full_contribution = full.astype(np.float64) - ffn.astype(np.float64)
            candidates = {}
            for retained in (1, 2, 3):
                for mode in ("original", "renormalized"):
                    gates = full_gates.copy(); gates[retained:] = 0
                    if mode == "renormalized":
                        gates[:retained] /= gates[:retained].sum()
                    candidate = calculate(ffn, router, pointers, gates)
                    contribution = candidate.astype(np.float64) - ffn.astype(np.float64)
                    output_delta = candidate.astype(np.float64) - full.astype(np.float64)
                    contribution_delta = contribution - full_contribution
                    key = f"top{retained}_{mode}"
                    candidates[key] = {
                        "output_relative_l2": float(np.linalg.norm(output_delta) / np.linalg.norm(full)),
                        "contribution_relative_l2": float(np.linalg.norm(contribution_delta) / np.linalg.norm(full_contribution)),
                        "output_max_abs": float(np.abs(output_delta).max()),
                        "retained_gate_mass": float(full_gates[:retained].sum()),
                        "expert_byte_reduction": 4 / retained,
                    }
            observations.append({"position": capture["position"], "layer": capture["layer"],
                                 "route": capture["route"], "gates": capture["gates"],
                                 "candidates": candidates})
    summaries = {}
    for key in observations[0]["candidates"]:
        output_l2 = [item["candidates"][key]["output_relative_l2"] for item in observations]
        contribution_l2 = [item["candidates"][key]["contribution_relative_l2"] for item in observations]
        max_abs = [item["candidates"][key]["output_max_abs"] for item in observations]
        mass = [item["candidates"][key]["retained_gate_mass"] for item in observations]
        summaries[key] = {
            "samples": len(observations),
            "output_relative_l2_p50": statistics.median(output_l2),
            "output_relative_l2_p95": percentile(output_l2, .95),
            "contribution_relative_l2_p50": statistics.median(contribution_l2),
            "contribution_relative_l2_p95": percentile(contribution_l2, .95),
            "output_max_abs_p95": percentile(max_abs, .95),
            "retained_gate_mass_p50": statistics.median(mass),
            "expert_byte_reduction": observations[0]["candidates"][key]["expert_byte_reduction"],
        }
    advancing = [key for key, value in summaries.items()
                 if key.startswith(("top1_", "top2_"))
                 and value["output_relative_l2_p95"] <= .02
                 and value["contribution_relative_l2_p95"] <= .15]
    report = {
        "schema": "aion.gptoss-120b-real-expert-contribution-gate.v1",
        "status": "ADVANCE_REDUCED_EXPERT_SEMANTIC_GATE" if advancing else "STOP_TOPK_EXPERT_OMISSION",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": "GPT-OSS 120B Q4_K_M/MXFP4",
        "quality_track": True,
        "activation_capture_dir": str(args.activations.resolve()),
        "capture_file_hashes": {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                                for path in sorted(args.activations.iterdir())},
        "observations": observations,
        "summaries": summaries,
        "advancing_candidates": advancing,
        "promotion_gate": {"maximum_output_relative_l2_p95": .02,
                           "maximum_contribution_relative_l2_p95": .15,
                           "minimum_expert_byte_reduction": 2.0},
        "warehouse_metrics": store.metrics(),
        "claim_boundary": (
            "Top-k omission was simulated on 16 real activation/route pairs from two genuine "
            "token positions across eight layers. All four original experts were loaded for the "
            "measurement, so byte reductions are theoretical until a candidate passes a frozen "
            "full-model semantic gate. This is changed arithmetic, not exact GPT-OSS 120B."
        ),
    }
    body = json.dumps(report, sort_keys=True, separators=(",", ":"))
    report["canonical_sha256"] = hashlib.sha256(body.encode()).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": report["status"], "advancing_candidates": advancing,
                      "summaries": summaries, "canonical_sha256": report["canonical_sha256"]},
                     sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
