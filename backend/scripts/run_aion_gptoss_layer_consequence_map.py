#!/usr/bin/env python3
"""Build a cross-family per-layer consequence map for selected-expert omission."""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import statistics
import subprocess
import tempfile
from collections import defaultdict
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path

import numpy as np

from backend.modules.aion_inference.gptoss_expert_frame_store import GptOssExpertFrameStore

WIDTH = 2880


def percentile(values: list[float], fraction: float) -> float:
    return sorted(values)[int(fraction * (len(values) - 1))]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--activations", type=Path, action="append", required=True)
    parser.add_argument("--threads", type=int, default=8)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("refusing to overwrite evidence")
    captures = [(root.name, path) for root in args.activations
                for path in sorted(root.glob("position-*-layer-*.json"))]
    if not captures:
        raise SystemExit("no captures")
    store = GptOssExpertFrameStore(args.manifest, 512 * 1024 * 1024)
    native = Path(__file__).parents[1] / "modules/aion_inference/native/gptoss_persistent_moe_library.cpp"
    observations = []
    with tempfile.TemporaryDirectory(prefix="aion-layer-consequence-") as temporary:
        library_path = Path(temporary) / "moe.dylib"
        subprocess.run(["clang++", "-std=c++17", "-O3", "-dynamiclib",
                        "-I/opt/homebrew/include", str(native), "-L/opt/homebrew/lib",
                        "-lggml", "-lggml-base", "-ldl", "-o", str(library_path)], check=True)
        loaded = ctypes.CDLL(str(library_path))
        function = loaded.aion_gptoss_one_expert_contribution_reuse_graph
        function.argtypes = [ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_void_p),
                             ctypes.c_float, ctypes.POINTER(ctypes.c_float), ctypes.c_int,
                             ctypes.POINTER(ctypes.c_double)]
        function.restype = ctypes.c_int
        for family, capture_path in captures:
            capture = json.loads(capture_path.read_text()); stem = capture_path.with_suffix("")
            ffn = np.fromfile(Path(str(stem) + "-ffn.bin"), dtype="<f4")
            router = np.fromfile(Path(str(stem) + "-router.bin"), dtype="<f4")
            experts = store.get_layer_route_parallel(capture["layer"], capture["route"], workers=4)
            contributions = []
            for gate, expert in zip(capture["gates"], experts):
                blobs = [expert[projection][kind] for projection in ("gate", "up", "down")
                         for kind in ("weight", "bias")]
                refs = [ctypes.c_char_p(blob) for blob in blobs]
                ptrs = (ctypes.c_void_p * len(refs))(*[
                    ctypes.cast(ref, ctypes.c_void_p).value for ref in refs])
                output = np.empty(WIDTH, dtype=np.float32); elapsed = ctypes.c_double()
                status = function(router.ctypes.data_as(ctypes.POINTER(ctypes.c_float)), ptrs,
                                  ctypes.c_float(gate),
                                  output.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                                  args.threads, ctypes.byref(elapsed))
                if status:
                    raise RuntimeError(f"contribution status {status}")
                contributions.append(output.astype(np.float64))
            full_contribution = sum(contributions, np.zeros(WIDTH, dtype=np.float64))
            full = ffn.astype(np.float64) + full_contribution
            candidates = {}
            for retained in (1, 2, 3):
                candidate_contribution = sum(contributions[:retained],
                                             np.zeros(WIDTH, dtype=np.float64))
                delta = candidate_contribution - full_contribution
                candidates[str(retained)] = {
                    "output_relative_l2": float(np.linalg.norm(delta) / np.linalg.norm(full)),
                    "contribution_relative_l2": float(
                        np.linalg.norm(delta) / np.linalg.norm(full_contribution)),
                    "retained_gate_mass": float(sum(capture["gates"][:retained])),
                }
            oracle = {}
            for retained in (1, 2, 3):
                best = None
                for chosen in combinations(range(4), retained):
                    candidate_contribution = sum(
                        (contributions[index] for index in chosen),
                        np.zeros(WIDTH, dtype=np.float64))
                    delta = candidate_contribution - full_contribution
                    row = {
                        "chosen_positions": list(chosen),
                        "output_relative_l2": float(
                            np.linalg.norm(delta) / np.linalg.norm(full)),
                        "contribution_relative_l2": float(
                            np.linalg.norm(delta) / np.linalg.norm(full_contribution)),
                    }
                    if best is None or row["output_relative_l2"] < best["output_relative_l2"]:
                        best = row
                oracle[str(retained)] = best
            observations.append({"family": family, "capture": capture_path.name,
                                 "position": capture["position"], "layer": capture["layer"],
                                 "route": capture["route"], "candidates": candidates,
                                 "oracle_best_subsets": oracle})

    by_layer = defaultdict(list)
    for row in observations:
        by_layer[row["layer"]].append(row)
    layer_map = {}
    selected_counts = {}
    for layer, rows in sorted(by_layer.items()):
        candidates = {}
        selected = 4
        for retained in (1, 2, 3):
            values = [row["candidates"][str(retained)] for row in rows]
            summary = {
                "samples": len(values),
                "families": sorted({row["family"] for row in rows}),
                "output_relative_l2_p95": percentile(
                    [x["output_relative_l2"] for x in values], .95),
                "output_relative_l2_max": max(x["output_relative_l2"] for x in values),
                "contribution_relative_l2_p95": percentile(
                    [x["contribution_relative_l2"] for x in values], .95),
                "retained_gate_mass_min": min(x["retained_gate_mass"] for x in values),
            }
            candidates[str(retained)] = summary
            if (selected == 4 and summary["output_relative_l2_p95"] <= .02
                    and summary["output_relative_l2_max"] <= .025
                    and summary["contribution_relative_l2_p95"] <= .15):
                selected = retained
        layer_map[str(layer)] = {"selected_experts": selected, "candidates": candidates}
        selected_counts[str(selected)] = selected_counts.get(str(selected), 0) + 1
    baseline_expert_evaluations = 4 * len(layer_map)
    selected_expert_evaluations = sum(row["selected_experts"] for row in layer_map.values())
    reduction = baseline_expert_evaluations / selected_expert_evaluations
    oracle_counts = {"1": 0, "2": 0, "3": 0, "4": 0}
    for row in observations:
        selected = 4
        for retained in (1, 2, 3):
            candidate = row["oracle_best_subsets"][str(retained)]
            if (candidate["output_relative_l2"] <= .02
                    and candidate["contribution_relative_l2"] <= .15):
                selected = retained
                break
        oracle_counts[str(selected)] += 1
    oracle_evaluations = sum(int(key) * value for key, value in oracle_counts.items())
    oracle_reduction = 4 * len(observations) / oracle_evaluations
    status = ("ADVANCE_LAYER_CONDITIONED_GENERATION_GATE" if reduction >= 1.15
              else "ADVANCE_CONSEQUENCE_PREDICTOR" if oracle_reduction >= 1.50
              else "STOP_LAYER_CONDITIONED_OMISSION")
    report = {
        "schema": "aion.gptoss-120b-layer-consequence-map.v1",
        "status": status,
        "created_at": datetime.now(timezone.utc).isoformat(), "quality_track": True,
        "observations": observations, "layer_map": layer_map,
        "selected_layer_counts": selected_counts,
        "baseline_expert_evaluations_per_token": baseline_expert_evaluations,
        "selected_expert_evaluations_per_token": selected_expert_evaluations,
        "theoretical_expert_work_reduction": reduction,
        "impossible_oracle_selected_counts": oracle_counts,
        "impossible_oracle_expert_work_reduction": oracle_reduction,
        "promotion_gate": {"minimum_theoretical_expert_work_reduction": 1.15,
                           "maximum_layer_output_relative_l2_p95": .02,
                           "maximum_layer_output_relative_l2_max": .025,
                           "maximum_layer_contribution_relative_l2_p95": .15},
        "warehouse_metrics": store.metrics(),
        "capture_hashes": {str(path): hashlib.sha256(path.read_bytes()).hexdigest()
                           for _, path in captures},
        "claim_boundary": (
            "Offline cross-family layer-output consequence map using original selected experts, "
            "gates and weights. Omission is changed arithmetic. The work reduction is a theoretical "
            "bound until the frozen layer plan survives full causal generation and semantic gates. "
            "The best-subset result is an impossible oracle that uses the teacher output and only "
            "bounds whether a future consequence predictor is worth building."),
    }
    body = json.dumps(report, sort_keys=True, separators=(",", ":"))
    report["canonical_sha256"] = hashlib.sha256(body.encode()).hexdigest()
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": report["status"], "selected_layer_counts": selected_counts,
                      "theoretical_expert_work_reduction": reduction,
                      "impossible_oracle_selected_counts": oracle_counts,
                      "impossible_oracle_expert_work_reduction": oracle_reduction,
                      "canonical_sha256": report["canonical_sha256"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
