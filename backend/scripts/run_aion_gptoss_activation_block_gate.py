#!/usr/bin/env python3
"""Test activation-addressed internal expert weight traffic on real states."""

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
BLOCK = 32


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
    with tempfile.TemporaryDirectory(prefix="aion-gptoss-activation-block-") as temporary:
        library_path = Path(temporary) / "moe.dylib"
        subprocess.run(["clang++", "-std=c++17", "-O3", "-dynamiclib",
                        "-I/opt/homebrew/include", str(native), "-L/opt/homebrew/lib",
                        "-lggml", "-lggml-base", "-ldl", "-o", str(library_path)],
                       check=True)
        loaded = ctypes.CDLL(str(library_path)); function = loaded.aion_gptoss_moe_finish
        function.argtypes = [ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_float),
                             ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(ctypes.c_float),
                             ctypes.POINTER(ctypes.c_float), ctypes.c_int,
                             ctypes.POINTER(ctypes.c_double)]
        function.restype = ctypes.c_int

        def calculate(ffn: np.ndarray, router: np.ndarray, pointers,
                      gates: np.ndarray) -> np.ndarray:
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
            capture = json.loads(capture_path.read_text()); stem = capture_path.with_suffix("")
            ffn = np.fromfile(Path(str(stem) + "-ffn.bin"), dtype="<f4")
            router = np.fromfile(Path(str(stem) + "-router.bin"), dtype="<f4")
            values = store.get_layer_route_parallel(capture["layer"], capture["route"], workers=4)
            blobs = [value[projection][kind] for value in values
                     for projection in ("gate", "up", "down")
                     for kind in ("weight", "bias")]
            references = [ctypes.c_char_p(blob) for blob in blobs]
            pointers = (ctypes.c_void_p * len(references))(*[
                ctypes.cast(reference, ctypes.c_void_p).value for reference in references])
            gates = np.asarray(capture["gates"], dtype=np.float32)
            full = calculate(ffn, router, pointers, gates)
            full_contribution = full.astype(np.float64) - ffn.astype(np.float64)
            block_energy = np.square(router.astype(np.float64).reshape(-1, BLOCK)).sum(axis=1)
            element_energy = np.square(router.astype(np.float64))
            candidates = {}
            for fraction in (.75, .50, .25, .125):
                for selection, energy in (("block32", block_energy), ("element", element_energy)):
                    keep = max(1, round(len(energy) * fraction))
                    chosen = np.argpartition(energy, -keep)[-keep:]
                    candidate_input = np.zeros_like(router)
                    if selection == "block32":
                        for index in chosen:
                            candidate_input[index * BLOCK:(index + 1) * BLOCK] = router[index * BLOCK:(index + 1) * BLOCK]
                    else:
                        candidate_input[chosen] = router[chosen]
                    candidate = calculate(ffn, candidate_input, pointers, gates)
                    delta = candidate.astype(np.float64) - full.astype(np.float64)
                    contribution_delta = (candidate.astype(np.float64) - ffn.astype(np.float64)) - full_contribution
                    # Gate/up consume two of the three packed matrices. Down remains dense.
                    retained_weight_fraction = (1 + 2 * fraction) / 3
                    key = f"{selection}_retain_{str(fraction).replace('.', '_')}"
                    candidates[key] = {
                        "retained_activation_fraction": fraction,
                        "retained_activation_energy": float(element_energy[candidate_input != 0].sum() / element_energy.sum()),
                        "theoretical_expert_weight_reduction": 1 / retained_weight_fraction,
                        "output_relative_l2": float(np.linalg.norm(delta) / np.linalg.norm(full)),
                        "contribution_relative_l2": float(np.linalg.norm(contribution_delta) / np.linalg.norm(full_contribution)),
                        "output_max_abs": float(np.abs(delta).max()),
                    }
            observations.append({"position": capture["position"], "layer": capture["layer"],
                                 "route": capture["route"], "candidates": candidates})
    summaries = {}
    for key in observations[0]["candidates"]:
        values = [observation["candidates"][key] for observation in observations]
        summaries[key] = {
            "samples": len(values),
            "retained_activation_fraction": values[0]["retained_activation_fraction"],
            "retained_energy_p50": statistics.median(x["retained_activation_energy"] for x in values),
            "theoretical_expert_weight_reduction": values[0]["theoretical_expert_weight_reduction"],
            "output_relative_l2_p50": statistics.median(x["output_relative_l2"] for x in values),
            "output_relative_l2_p95": percentile([x["output_relative_l2"] for x in values], .95),
            "contribution_relative_l2_p50": statistics.median(x["contribution_relative_l2"] for x in values),
            "contribution_relative_l2_p95": percentile([x["contribution_relative_l2"] for x in values], .95),
            "output_max_abs_p95": percentile([x["output_max_abs"] for x in values], .95),
        }
    advancing = [key for key, value in summaries.items()
                 if value["theoretical_expert_weight_reduction"] >= 2
                 and value["output_relative_l2_p95"] <= .02
                 and value["contribution_relative_l2_p95"] <= .15]
    report = {
        "schema": "aion.gptoss-120b-activation-block-gate.v1",
        "status": "ADVANCE_BLOCK_ADDRESSABLE_EXPERT" if advancing else "STOP_ACTIVATION_BLOCK_OMISSION",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": "GPT-OSS 120B Q4_K_M/MXFP4", "quality_track": True,
        "block_dimensions": BLOCK, "observations": observations, "summaries": summaries,
        "advancing_candidates": advancing,
        "promotion_gate": {"minimum_theoretical_expert_weight_reduction": 2.0,
                           "maximum_output_relative_l2_p95": .02,
                           "maximum_contribution_relative_l2_p95": .15},
        "warehouse_metrics": store.metrics(),
        "capture_file_hashes": {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                                for path in sorted(args.activations.iterdir())},
        "claim_boundary": (
            "This real-activation simulation zeros router-input dimensions before the four "
            "original experts. It estimates only gate/up column traffic; down-projection weights "
            "remain dense. All weights were loaded for measurement. No block-addressable warehouse "
            "or generated-token speed is claimed unless a candidate first passes this gate."
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
