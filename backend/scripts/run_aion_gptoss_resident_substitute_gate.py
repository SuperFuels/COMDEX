#!/usr/bin/env python3
"""Screen a confidence-gated resident fifth-expert substitution on real states."""

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

from backend.modules.aion_inference.expert_frame_gguf_reader import ExpertFrameGGUFReader
from backend.modules.aion_inference.gguf_stream_index import read_gguf_stream_index
from backend.modules.aion_inference.gptoss_expert_frame_store import GptOssExpertFrameStore

WIDTH = 2880
EXPERTS = 128


def percentile(values: list[float], fraction: float) -> float:
    return sorted(values)[int(fraction * (len(values) - 1))]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--activations", type=Path, required=True)
    parser.add_argument("--expert-pool", type=Path, required=True)
    parser.add_argument("--threads", type=int, default=8)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("refusing to overwrite evidence")
    captures = sorted(args.activations.glob("position-*-layer-*.json"))
    if not captures:
        raise SystemExit("no captures")
    pool = json.loads(args.expert_pool.read_text())
    manifest = json.loads(args.manifest.read_text())
    readers = {}; tensors = {}
    for source in manifest["verified_sources"]:
        reader = ExpertFrameGGUFReader(args.manifest, source["name"], 64 * 1024 * 1024)
        readers[source["name"]] = reader
        for tensor in read_gguf_stream_index(reader, int(source["size"]))["tensors"]:
            tensors[tensor["name"]] = (source["name"], tensor)

    def read_tensor(name: str) -> bytes:
        source, tensor = tensors[name]
        return readers[source].read_at(int(tensor["absolute_offset"]), int(tensor["byte_length"]))

    store = GptOssExpertFrameStore(args.manifest, 256 * 1024 * 1024)
    native = Path(__file__).parents[1] / "modules/aion_inference/native/gptoss_persistent_moe_library.cpp"
    observations = []
    with tempfile.TemporaryDirectory(prefix="aion-gptoss-substitute-") as temporary:
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

        def calculate(ffn, router, values, gates):
            blobs = [value[projection][kind] for value in values
                     for projection in ("gate", "up", "down") for kind in ("weight", "bias")]
            refs = [ctypes.c_char_p(blob) for blob in blobs]
            pointers = (ctypes.c_void_p * len(refs))(*[
                ctypes.cast(ref, ctypes.c_void_p).value for ref in refs])
            output = np.empty(WIDTH, dtype=np.float32); elapsed = ctypes.c_double()
            status = function(ffn.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                              router.ctypes.data_as(ctypes.POINTER(ctypes.c_float)), pointers,
                              gates.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                              output.ctypes.data_as(ctypes.POINTER(ctypes.c_float)), args.threads,
                              ctypes.byref(elapsed))
            if status:
                raise RuntimeError(f"native status {status}")
            return output

        for capture_path in captures:
            capture = json.loads(capture_path.read_text()); layer = int(capture["layer"])
            stem = capture_path.with_suffix("")
            ffn = np.fromfile(Path(str(stem) + "-ffn.bin"), dtype="<f4")
            router = np.fromfile(Path(str(stem) + "-router.bin"), dtype="<f4")
            weight = np.frombuffer(read_tensor(f"blk.{layer}.ffn_gate_inp.weight"), dtype="<f4").reshape(EXPERTS, WIDTH)
            bias = np.frombuffer(read_tensor(f"blk.{layer}.ffn_gate_inp.bias"), dtype="<f4")
            logits = weight @ router + bias
            order = np.argsort(logits, kind="stable")[::-1]
            route = order[:4].astype(int).tolist()
            if route != capture["route"]:
                raise RuntimeError("captured route does not match reconstructed router")
            selected = logits[route].astype(np.float64); selected -= selected.max()
            gates = np.exp(selected); gates /= gates.sum(); gates = gates.astype(np.float32)
            original_values = store.get_layer_route_parallel(layer, route, workers=4)
            full = calculate(ffn, router, original_values, gates)
            resident = set(pool["layers"][str(layer)])
            substitute = next((int(expert) for expert in order[4:] if int(expert) in resident), None)
            eligible = (substitute is not None and route[3] not in resident
                        and all(expert in resident for expert in route[:3]))
            row = {"position": capture["position"], "layer": layer, "route": route,
                   "eligible": eligible, "original_fourth_resident": route[3] in resident,
                   "top_three_resident": all(expert in resident for expert in route[:3])}
            if eligible:
                replacement_route = route[:3] + [substitute]
                replacement_values = original_values[:3] + [store.get(layer, substitute)]
                gap = float(logits[route[3]] - logits[substitute])
                candidate = calculate(ffn, router, replacement_values, gates)
                replacement_logits = logits[replacement_route].astype(np.float64)
                replacement_logits -= replacement_logits.max()
                replacement_gates = np.exp(replacement_logits); replacement_gates /= replacement_gates.sum()
                renorm = calculate(ffn, router, replacement_values, replacement_gates.astype(np.float32))
                row.update({"substitute": substitute, "logit_gap": gap})
                for name, value in (("preserved_fourth_gate", candidate), ("renormalized", renorm)):
                    delta = value.astype(np.float64) - full.astype(np.float64)
                    row[name] = {"output_relative_l2": float(np.linalg.norm(delta) / np.linalg.norm(full)),
                                 "output_max_abs": float(np.abs(delta).max())}
            pool_route = [int(expert) for expert in order if int(expert) in resident][:4]
            row["pool_top4_route"] = pool_route
            row["pool_top4_changed"] = pool_route != route
            if pool_route != route:
                pool_values = store.get_layer_route_parallel(layer, pool_route, workers=4)
                rank_gaps = [float(logits[route[index]] - logits[pool_route[index]])
                             for index in range(4)]
                pool_selected = logits[pool_route].astype(np.float64); pool_selected -= pool_selected.max()
                pool_gates = np.exp(pool_selected); pool_gates /= pool_gates.sum()
                for name, candidate_gates in (("pool_top4_preserved_rank_gates", gates),
                                              ("pool_top4_renormalized", pool_gates.astype(np.float32))):
                    candidate = calculate(ffn, router, pool_values, candidate_gates)
                    delta = candidate.astype(np.float64) - full.astype(np.float64)
                    row[name] = {"output_relative_l2": float(np.linalg.norm(delta) / np.linalg.norm(full)),
                                 "output_max_abs": float(np.abs(delta).max())}
                row["pool_top4_max_rank_logit_gap"] = max(rank_gaps)
                row["pool_top4_sum_rank_logit_gap"] = sum(rank_gaps)
            observations.append(row)

    summaries = {}
    for threshold in (0.01, 0.02, 0.05, 0.10, 0.20):
        accepted = [row for row in observations if row["eligible"] and row["logit_gap"] <= threshold]
        for mode in ("preserved_fourth_gate", "renormalized"):
            errors = [row[mode]["output_relative_l2"] for row in accepted]
            summaries[f"gap_{threshold:.2f}_{mode}"] = {
                "accepted": len(accepted), "total": len(observations),
                "accepted_fraction": len(accepted) / len(observations),
                "output_relative_l2_p50": statistics.median(errors) if errors else None,
                "output_relative_l2_p95": percentile(errors, .95) if errors else None,
                "output_relative_l2_max": max(errors) if errors else None,
            }
    advancing = [name for name, row in summaries.items()
                 if row["accepted"] >= 2 and row["output_relative_l2_p95"] <= .02
                 and row["output_relative_l2_max"] <= .05]
    for threshold in (0.02, 0.05, 0.10, 0.20, 0.50, 1.00):
        accepted = [row for row in observations if row["pool_top4_changed"]
                    and row["pool_top4_max_rank_logit_gap"] <= threshold]
        for mode in ("pool_top4_preserved_rank_gates", "pool_top4_renormalized"):
            errors = [row[mode]["output_relative_l2"] for row in accepted]
            key = f"pool_max_gap_{threshold:.2f}_{mode}"
            summaries[key] = {"accepted": len(accepted), "total": len(observations),
                              "accepted_fraction": len(accepted) / len(observations),
                              "output_relative_l2_p50": statistics.median(errors) if errors else None,
                              "output_relative_l2_p95": percentile(errors, .95) if errors else None,
                              "output_relative_l2_max": max(errors) if errors else None}
            if len(accepted) >= 2 and summaries[key]["output_relative_l2_p95"] <= .02 \
                    and summaries[key]["output_relative_l2_max"] <= .05:
                advancing.append(key)
    report = {"schema": "aion.gptoss-120b-resident-substitute-gate.v1",
              "status": "ADVANCE_RESIDENT_SUBSTITUTE" if advancing else "STOP_RESIDENT_SUBSTITUTE",
              "created_at": datetime.now(timezone.utc).isoformat(), "quality_track": True,
              "model": "GPT-OSS 120B Q4_K_M/MXFP4", "observations": observations,
              "summaries": summaries, "advancing_candidates": advancing,
              "promotion_gate": {"minimum_accepted_samples": 2,
                                  "maximum_output_relative_l2_p95": .02,
                                  "maximum_output_relative_l2": .05},
              "claim_boundary": "Real-activation microgate only. Every candidate expert was fetched for numerical comparison; accepted fractions project only opportunities to replace a missing fourth expert with the closest-logit resident expert. No generated-token speed or semantic quality is claimed."}
    report["canonical_sha256"] = hashlib.sha256(json.dumps(
        report, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": report["status"], "advancing_candidates": advancing,
                      "summaries": summaries, "canonical_sha256": report["canonical_sha256"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
