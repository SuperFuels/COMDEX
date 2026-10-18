#!/usr/bin/env python3
"""Test reuse of prior-token expert contributions on real paired states."""

from __future__ import annotations

import argparse, ctypes, hashlib, json, statistics, subprocess, tempfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from backend.modules.aion_inference.gptoss_expert_frame_store import (
    GptOssExpertFrameStore, ctypes_component_pointer_array,
)

WIDTH = 2880


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--activations", type=Path, required=True)
    parser.add_argument("--threads", type=int, default=8)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("refusing to overwrite evidence")
    pairs = defaultdict(dict)
    for path in args.activations.glob("position-*-layer-*.json"):
        row = json.loads(path.read_text()); pairs[int(row["layer"])][int(row["position"])] = (path, row)
    pairs = {layer: rows for layer, rows in pairs.items() if 0 in rows and 1 in rows}
    store = GptOssExpertFrameStore(args.manifest, 256 * 1024 * 1024)
    native = Path(__file__).parents[1] / "modules/aion_inference/native/gptoss_persistent_moe_library.cpp"
    observations = []
    with tempfile.TemporaryDirectory(prefix="aion-temporal-contribution-") as temporary:
        library_path = Path(temporary) / "moe.dylib"
        subprocess.run(["clang++", "-std=c++17", "-O3", "-dynamiclib", "-I/opt/homebrew/include",
                        str(native), "-L/opt/homebrew/lib", "-lggml", "-lggml-base", "-ldl",
                        "-o", str(library_path)], check=True)
        library = ctypes.CDLL(str(library_path))
        one = library.aion_gptoss_one_expert_contribution_batch
        one.argtypes = [ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_void_p),
                        ctypes.POINTER(ctypes.c_float), ctypes.c_int,
                        ctypes.POINTER(ctypes.c_float), ctypes.c_int, ctypes.POINTER(ctypes.c_double)]
        one.restype = ctypes.c_int

        def contribution(router, value, gate):
            blobs = [value[p][k] for p in ("gate", "up", "down") for k in ("weight", "bias")]
            refs, pointers = ctypes_component_pointer_array(blobs)
            output = np.empty(WIDTH, dtype=np.float32); elapsed = ctypes.c_double()
            gates = np.asarray([gate], dtype=np.float32)
            status = one(router.ctypes.data_as(ctypes.POINTER(ctypes.c_float)), pointers,
                         gates.ctypes.data_as(ctypes.POINTER(ctypes.c_float)), 1,
                         output.ctypes.data_as(ctypes.POINTER(ctypes.c_float)), args.threads,
                         ctypes.byref(elapsed))
            if status: raise RuntimeError(f"native status {status}")
            _ = refs
            return output

        for layer, rows in sorted(pairs.items()):
            previous_path, previous = rows[0]; current_path, current = rows[1]
            previous_router = np.fromfile(Path(str(previous_path.with_suffix("")) + "-router.bin"), dtype="<f4")
            current_stem = current_path.with_suffix("")
            current_router = np.fromfile(Path(str(current_stem) + "-router.bin"), dtype="<f4")
            current_ffn = np.fromfile(Path(str(current_stem) + "-ffn.bin"), dtype="<f4")
            common = set(previous["route"]) & set(current["route"])
            values = store.get_layer_route_parallel(layer, current["route"], workers=4)
            exact_parts = []; candidate_parts = []
            for index, (expert, gate, value) in enumerate(zip(current["route"], current["gates"], values)):
                exact = contribution(current_router, value, gate); exact_parts.append(exact)
                candidate_parts.append(contribution(previous_router, value, gate) if expert in common else exact)
            reference = current_ffn.copy(); candidate = current_ffn.copy()
            for exact, approximate in zip(exact_parts, candidate_parts):
                reference += exact; candidate += approximate
            delta = candidate.astype(np.float64) - reference.astype(np.float64)
            cosine = float(np.dot(previous_router, current_router) /
                           (np.linalg.norm(previous_router) * np.linalg.norm(current_router)))
            observations.append({"layer": layer, "common_experts": sorted(common),
                                 "reused_experts": len(common), "cosine": cosine,
                                 "traffic_reduction": 4 / (4 - len(common)) if len(common) < 4 else None,
                                 "output_relative_l2": float(np.linalg.norm(delta) / np.linalg.norm(reference)),
                                 "output_max_abs": float(np.abs(delta).max())})
    candidates = [row for row in observations if row["reused_experts"]]
    summaries = {}
    for threshold in (0.90, 0.95, 0.98, 0.99, 0.995):
        accepted = [row for row in candidates if row["cosine"] >= threshold]
        errors = [row["output_relative_l2"] for row in accepted]
        summaries[str(threshold)] = {"accepted_layers": len(accepted),
                                     "reused_experts": sum(row["reused_experts"] for row in accepted),
                                     "output_relative_l2_max": max(errors) if errors else None,
                                     "output_relative_l2_p50": statistics.median(errors) if errors else None}
    advancing = [key for key, row in summaries.items() if row["accepted_layers"] >= 2
                 and row["output_relative_l2_max"] <= .02]
    report = {"schema": "aion.gptoss-120b-temporal-contribution-reuse-gate.v1",
              "status": "ADVANCE_TEMPORAL_REUSE" if advancing else "STOP_TEMPORAL_REUSE",
              "created_at": datetime.now(timezone.utc).isoformat(), "quality_track": True,
              "model": "GPT-OSS 120B Q4_K_M/MXFP4", "observations": observations,
              "summaries": summaries, "advancing_candidates": advancing,
              "claim_boundary": "Two-position real-activation microgate only. Prior-token expert outputs replace current calculations only for repeated expert IDs; all weights were fetched for comparison. Traffic reduction and generated-token speed are not claimed unless a confidence gate advances."}
    report["canonical_sha256"] = hashlib.sha256(json.dumps(report, sort_keys=True,
        separators=(",", ":")).encode()).hexdigest()
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": report["status"], "summaries": summaries,
                      "canonical_sha256": report["canonical_sha256"]}, sort_keys=True))
    return 0


if __name__ == "__main__": raise SystemExit(main())
