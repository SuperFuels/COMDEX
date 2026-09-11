#!/usr/bin/env python3
"""Measure activation-addressed down-projection blocks on real 120B routes."""

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
    parser.add_argument("--activations", type=Path, action="append", required=True)
    parser.add_argument("--threads", type=int, default=8)
    parser.add_argument("--fractions", default="0.25,0.5,0.75,0.9")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("refusing to overwrite evidence")
    fractions = [float(value) for value in args.fractions.split(",")]
    if any(value <= 0 or value >= 1 for value in fractions):
        raise SystemExit("fractions must be between zero and one")
    captures = [(root.name, path) for root in args.activations
                for path in sorted(root.glob("position-*-layer-*.json"))]
    if not captures:
        raise SystemExit("no captures")

    store = GptOssExpertFrameStore(args.manifest, 512 * 1024 * 1024)
    native = Path(__file__).parents[1] / "modules/aion_inference/native/gptoss_persistent_moe_library.cpp"
    observations = []
    with tempfile.TemporaryDirectory(prefix="aion-intermediate-block-") as temporary:
        library_path = Path(temporary) / "moe.dylib"
        subprocess.run([
            "clang++", "-std=c++17", "-O3", "-dynamiclib", "-I/opt/homebrew/include",
            str(native), "-L/opt/homebrew/lib", "-lggml", "-lggml-base", "-ldl",
            "-o", str(library_path),
        ], check=True)
        loaded = ctypes.CDLL(str(library_path))
        gate_up = loaded.aion_gptoss_expert_gate_up
        gate_up.argtypes = [ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_void_p),
                            ctypes.POINTER(ctypes.c_float), ctypes.c_int,
                            ctypes.POINTER(ctypes.c_double)]
        gate_up.restype = ctypes.c_int
        down = loaded.aion_gptoss_expert_down_contribution
        down.argtypes = [ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_void_p),
                         ctypes.c_float, ctypes.POINTER(ctypes.c_float), ctypes.c_int,
                         ctypes.POINTER(ctypes.c_double)]
        down.restype = ctypes.c_int

        def pointers(blobs: list[bytes]):
            refs = [ctypes.c_char_p(blob) for blob in blobs]
            ptrs = (ctypes.c_void_p * len(refs))(*[
                ctypes.cast(ref, ctypes.c_void_p).value for ref in refs])
            return refs, ptrs

        for family, capture_path in captures:
            capture = json.loads(capture_path.read_text())
            stem = capture_path.with_suffix("")
            ffn = np.fromfile(Path(str(stem) + "-ffn.bin"), dtype="<f4")
            router = np.fromfile(Path(str(stem) + "-router.bin"), dtype="<f4")
            values = store.get_layer_route_parallel(capture["layer"], capture["route"], workers=4)
            full_contributions = []
            candidates = {str(fraction): [] for fraction in fractions}
            retained_energies = {str(fraction): [] for fraction in fractions}
            for gate_value, expert in zip(capture["gates"], values):
                first_refs, first_ptrs = pointers([
                    expert[projection][kind] for projection in ("gate", "up")
                    for kind in ("weight", "bias")])
                hidden = np.empty(WIDTH, dtype=np.float32); elapsed = ctypes.c_double()
                status = gate_up(router.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                                 first_ptrs,
                                 hidden.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                                 args.threads, ctypes.byref(elapsed))
                if status:
                    raise RuntimeError(f"gate/up status {status}")
                down_refs, down_ptrs = pointers([
                    expert["down"]["weight"], expert["down"]["bias"]])

                def finish(values_: np.ndarray) -> np.ndarray:
                    result = np.empty(WIDTH, dtype=np.float32); timing = ctypes.c_double()
                    code = down(values_.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                                down_ptrs, ctypes.c_float(gate_value),
                                result.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                                args.threads, ctypes.byref(timing))
                    if code:
                        raise RuntimeError(f"down status {code}")
                    return result

                full_contributions.append(finish(hidden))
                block_energy = np.square(hidden.astype(np.float64).reshape(-1, BLOCK)).sum(axis=1)
                total_energy = float(block_energy.sum())
                for fraction in fractions:
                    keep = max(1, round(len(block_energy) * fraction))
                    chosen = np.argpartition(block_energy, -keep)[-keep:]
                    masked = np.zeros_like(hidden)
                    for index in chosen:
                        masked[index * BLOCK:(index + 1) * BLOCK] = hidden[index * BLOCK:(index + 1) * BLOCK]
                    candidates[str(fraction)].append(finish(masked))
                    retained_energies[str(fraction)].append(
                        float(block_energy[chosen].sum() / total_energy))
                del first_refs, down_refs
            full = ffn.astype(np.float64)
            for contribution in full_contributions:
                full = full + contribution.astype(np.float64)
            full_delta = full - ffn.astype(np.float64)
            rows = {}
            for fraction in fractions:
                candidate = ffn.astype(np.float64)
                for contribution in candidates[str(fraction)]:
                    candidate = candidate + contribution.astype(np.float64)
                delta = candidate - full
                rows[str(fraction)] = {
                    "retained_intermediate_energy_min": min(retained_energies[str(fraction)]),
                    "retained_intermediate_energy_mean": statistics.mean(retained_energies[str(fraction)]),
                    "output_relative_l2": float(np.linalg.norm(delta) / np.linalg.norm(full)),
                    "contribution_relative_l2": float(np.linalg.norm(delta) / np.linalg.norm(full_delta)),
                    "theoretical_expert_traffic_reduction": 3 / (2 + fraction),
                }
            observations.append({"family": family, "capture": capture_path.name,
                                 "layer": capture["layer"], "candidates": rows})

    summaries = {}
    for fraction in fractions:
        rows = [row["candidates"][str(fraction)] for row in observations]
        summaries[str(fraction)] = {
            "samples": len(rows),
            "retained_intermediate_energy_p05": min(x["retained_intermediate_energy_min"] for x in rows),
            "output_relative_l2_p50": statistics.median(x["output_relative_l2"] for x in rows),
            "output_relative_l2_p95": percentile([x["output_relative_l2"] for x in rows], .95),
            "contribution_relative_l2_p95": percentile(
                [x["contribution_relative_l2"] for x in rows], .95),
            "theoretical_expert_traffic_reduction": rows[0]["theoretical_expert_traffic_reduction"],
        }
    advancing = [key for key, row in summaries.items()
                 if row["theoretical_expert_traffic_reduction"] >= 1.25
                 and row["output_relative_l2_p95"] <= .02
                 and row["contribution_relative_l2_p95"] <= .15]
    report = {
        "schema": "aion.gptoss-120b-intermediate-block-gate.v1",
        "status": "ADVANCE_BLOCK_ADDRESSABLE_DOWN" if advancing
                  else "STOP_INTERMEDIATE_BLOCK_OMISSION",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "quality_track": True, "block_width": BLOCK,
        "observations": observations, "summaries": summaries,
        "advancing_candidates": advancing,
        "promotion_gate": {"minimum_traffic_reduction": 1.25,
                           "maximum_output_relative_l2_p95": .02,
                           "maximum_contribution_relative_l2_p95": .15},
        "warehouse_metrics": store.metrics(),
        "capture_hashes": {str(path): hashlib.sha256(path.read_bytes()).hexdigest()
                           for _, path in captures},
        "claim_boundary": (
            "Real selected experts and exact gate/up intermediates were used. Low-energy "
            "32-coordinate SwiGLU blocks were zeroed only before each down projection. "
            "Traffic reduction assumes a future block-addressable down warehouse; this probe "
            "loaded all original weights and makes no generated-token speed claim."),
    }
    body = json.dumps(report, sort_keys=True, separators=(",", ":"))
    report["canonical_sha256"] = hashlib.sha256(body.encode()).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": report["status"], "advancing_candidates": advancing,
                      "summaries": summaries,
                      "canonical_sha256": report["canonical_sha256"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
