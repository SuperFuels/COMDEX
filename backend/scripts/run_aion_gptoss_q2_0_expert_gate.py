#!/usr/bin/env python3
"""Evaluate direct Q2_0 requantisation on held-out real GPT-OSS routes."""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import math
import statistics
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from backend.modules.aion_inference.gptoss_expert_frame_store import (
    GptOssExpertFrameStore, ctypes_component_pointer_array,
)

WIDTH = 2880


def percentile(values: list[float], fraction: float) -> float:
    return sorted(values)[max(0, math.ceil(fraction * len(values)) - 1)]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--activations", type=Path, required=True)
    parser.add_argument("--holdout-captures", type=int, default=4)
    parser.add_argument("--representation", choices=("q2_0", "top1_mxfp4_q2_0",
                                                       "top3_mxfp4_q2_0",
                                                       "top3_mxfp4_q3_k",
                                                       "mixed_mxfp4_q3_k",
                                                       "mixed_mxfp4_q2_0",
                                                       "padded_q2_k", "padded_q3_k",
                                                       "padded_mixed_k"),
                        default="q2_0")
    parser.add_argument("--compact-expert-mask", type=int, default=14,
                        help="route-position mask for mixed_mxfp4_q3_k")
    parser.add_argument("--layer", type=int)
    parser.add_argument("--threads", type=int, default=8)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("refusing to overwrite evidence")
    pattern = (f"position-*-layer-{args.layer}.json" if args.layer is not None
               else "position-*-layer-*.json")
    captures = sorted(args.activations.glob(pattern))
    if len(captures) < args.holdout_captures:
        raise SystemExit("insufficient captures")
    # Use the final captures so this gate remains disjoint from the captures
    # used to derive earlier dictionaries and exploratory transforms.
    captures = captures[-args.holdout_captures:]
    store = GptOssExpertFrameStore(args.manifest, 512 * 1024 * 1024)
    observations = []
    with tempfile.TemporaryDirectory(prefix="aion-gptoss-q2-0-") as temporary:
        root = Path(temporary)
        converter = root / "convert"
        library_path = root / "moe.dylib"
        native = Path(__file__).parents[1] / "modules/aion_inference/native"
        common = ["clang++", "-std=c++17", "-O3", "-I/opt/homebrew/include"]
        libraries = ["-L/opt/homebrew/lib", "-lggml", "-lggml-base", "-ldl"]
        converter_source = ("gptoss_mxfp4_to_q2_0.cpp" if args.representation in
                            ("q2_0", "top1_mxfp4_q2_0", "top3_mxfp4_q2_0",
                             "mixed_mxfp4_q2_0")
                            else "gptoss_mxfp4_to_padded_k.cpp")
        subprocess.run([*common, str(native / converter_source),
                        *libraries, "-o", str(converter)], check=True)
        subprocess.run([*common, "-dynamiclib",
                        str(native / "gptoss_persistent_moe_library.cpp"),
                        *libraries, "-o", str(library_path)], check=True)
        library = ctypes.CDLL(str(library_path))
        reference_function = library.aion_gptoss_moe_finish
        candidate_function = (library.aion_gptoss_moe_finish_q2_0
                              if args.representation == "q2_0" else
                              library.aion_gptoss_moe_finish_top1_mxfp4_q2_0
                              if args.representation == "top1_mxfp4_q2_0"
                              else library.aion_gptoss_moe_finish_top3_mxfp4_q2_0
                              if args.representation == "top3_mxfp4_q2_0"
                              else library.aion_gptoss_moe_finish_top3_mxfp4_q3_k
                              if args.representation == "top3_mxfp4_q3_k"
                              else library.aion_gptoss_moe_finish_mixed_mxfp4_q3_k
                              if args.representation == "mixed_mxfp4_q3_k"
                              else library.aion_gptoss_moe_finish_mixed_mxfp4_q2_0
                              if args.representation == "mixed_mxfp4_q2_0"
                              else library.aion_gptoss_moe_finish_padded_k)
        signature = [ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_float),
                     ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(ctypes.c_float),
                     ctypes.POINTER(ctypes.c_float), ctypes.c_int,
                     ctypes.POINTER(ctypes.c_double)]
        reference_function.argtypes = signature
        reference_function.restype = ctypes.c_int
        candidate_function.argtypes = (signature if args.representation in
                                       ("top1_mxfp4_q2_0", "top3_mxfp4_q2_0") else
                                       signature[:4] + [ctypes.c_int] + signature[4:]
                                       if args.representation in
                                       ("q2_0", "top3_mxfp4_q3_k") else
                                       signature[:4] + [ctypes.c_int, ctypes.c_int] + signature[4:])
        candidate_function.restype = ctypes.c_int

        def calculate(function, ffn, router, blobs, gates, mask=None):
            references, pointers = ctypes_component_pointer_array(blobs)
            output = np.empty(WIDTH, dtype=np.float32)
            elapsed = ctypes.c_double()
            prefix = [ffn.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                      router.ctypes.data_as(ctypes.POINTER(ctypes.c_float)), pointers,
                      gates.ctypes.data_as(ctypes.POINTER(ctypes.c_float))]
            suffix = [output.ctypes.data_as(ctypes.POINTER(ctypes.c_float)), args.threads,
                      ctypes.byref(elapsed)]
            candidate_arguments = []
            if mask is not None:
                if args.representation in ("q2_0", "top3_mxfp4_q3_k"):
                    candidate_arguments = [mask]
                elif args.representation in ("mixed_mxfp4_q3_k", "mixed_mxfp4_q2_0"):
                    candidate_arguments = [args.compact_expert_mask, mask]
                else:
                    q2_mask = (7 if args.representation == "padded_q2_k" else 0
                               if args.representation == "padded_q3_k" else mask)
                    candidate_arguments = [q2_mask, 7]
            status = function(*prefix, *candidate_arguments, *suffix)
            if status:
                raise RuntimeError(f"native MoE status {status}")
            _ = references
            return output, elapsed.value

        converted: dict[tuple[int, int, str, str], bytes] = {}
        for capture_path in captures:
            capture = json.loads(capture_path.read_text())
            stem = capture_path.with_suffix("")
            ffn = np.fromfile(Path(str(stem) + "-ffn.bin"), dtype="<f4")
            router = np.fromfile(Path(str(stem) + "-router.bin"), dtype="<f4")
            values = store.get_layer_route_parallel(capture["layer"], capture["route"], workers=4)
            original_blobs = []
            projection_blobs = []
            original_weight_bytes = 0
            q2_0_weight_bytes = 0
            for expert, value in zip(capture["route"], values, strict=True):
                for projection in ("gate", "up", "down"):
                    weight = value[projection]["weight"]
                    original_blobs.extend((weight, value[projection]["bias"]))
                    base_key = (capture["layer"], expert, projection)
                    formats = (("q2_0",) if args.representation in
                            ("q2_0", "top1_mxfp4_q2_0", "top3_mxfp4_q2_0",
                             "mixed_mxfp4_q2_0") else
                               ("q2_k", "q3_k") if args.representation == "padded_mixed_k" else
                               ("q2_k",) if args.representation == "padded_q2_k" else ("q3_k",))
                    for compact_format in formats:
                        key = (*base_key, compact_format)
                        if key in converted:
                            continue
                        source = root / f"l{key[0]}-e{key[1]}-{projection}-mxfp4.bin"
                        target = root / f"l{key[0]}-e{key[1]}-{projection}-{compact_format}.bin"
                        source.write_bytes(weight)
                        converter_arguments = ([str(converter), str(source), str(target),
                                                str(WIDTH), str(args.threads)]
                                               if args.representation in
                                               ("q2_0", "top1_mxfp4_q2_0",
                                                "top3_mxfp4_q2_0", "mixed_mxfp4_q2_0") else
                                               [str(converter), str(source), str(target),
                                                compact_format, str(WIDTH), str(args.threads)])
                        subprocess.run(converter_arguments, check=True,
                                       stdout=subprocess.DEVNULL)
                        converted[key] = target.read_bytes()
                    original_bias = value[projection]["bias"]
                    bias = original_bias
                    if args.representation not in (
                            "q2_0", "top1_mxfp4_q2_0", "top3_mxfp4_q2_0",
                            "mixed_mxfp4_q2_0"):
                        bias = bias + bytes((3072 - WIDTH) * 4)
                    q2_format = ("q2_0" if args.representation in
                                 ("q2_0", "top1_mxfp4_q2_0",
                                  "top3_mxfp4_q2_0", "mixed_mxfp4_q2_0") else "q2_k")
                    q2 = converted.get((*base_key, q2_format))
                    q3 = converted.get((*base_key, "q3_k"))
                    q2 = q2 if q2 is not None else q3
                    q3 = q3 if q3 is not None else q2
                    if q2 is None or q3 is None:
                        raise RuntimeError("compact projection conversion missing")
                    projection_blobs.append((weight, q2, q3, original_bias, bias))
                    original_weight_bytes += len(weight)
                    q2_0_weight_bytes += len(q2)
            gates = np.asarray(capture["gates"], dtype=np.float32)
            reference, reference_ms = calculate(
                reference_function, ffn, router, original_blobs, gates)
            masks = ((None,) if args.representation in
                     ("top1_mxfp4_q2_0", "top3_mxfp4_q2_0") else
                     range(1, 8) if args.representation in
                     ("top3_mxfp4_q3_k", "mixed_mxfp4_q3_k",
                      "mixed_mxfp4_q2_0") else
                     range(1, 8) if args.representation == "q2_0" else
                     range(0, 8) if args.representation == "padded_mixed_k" else (7,))
            for mask in masks:
                candidate_blobs = []
                candidate_weight_bytes = 0
                for index, (original, q2, q3, original_bias, padded_bias) in enumerate(
                        projection_blobs):
                    projection_bit = 1 << (index % 3)
                    if args.representation == "top1_mxfp4_q2_0":
                        selected = original if index // 3 == 0 else q2
                    elif args.representation == "top3_mxfp4_q2_0":
                        selected = original if index // 3 < 3 else q2
                    elif args.representation == "top3_mxfp4_q3_k":
                        selected = (original if index // 3 < 3 or not mask & projection_bit
                                    else q3)
                    elif args.representation == "mixed_mxfp4_q3_k":
                        selected = (q3 if (args.compact_expert_mask & (1 << (index // 3))
                                           and mask & projection_bit) else original)
                    elif args.representation == "mixed_mxfp4_q2_0":
                        selected = (q2 if (args.compact_expert_mask & (1 << (index // 3))
                                           and mask & projection_bit) else original)
                    elif args.representation == "q2_0":
                        selected = q2 if mask & projection_bit else original
                    elif args.representation == "padded_q2_k":
                        selected = q2
                    elif args.representation == "padded_q3_k":
                        selected = q3
                    else:
                        selected = q2 if mask & projection_bit else q3
                    bias = (original_bias if args.representation in
                            ("q2_0", "top1_mxfp4_q2_0", "top3_mxfp4_q2_0",
                             "mixed_mxfp4_q2_0")
                            or (args.representation == "top3_mxfp4_q3_k"
                                and (index // 3 < 3 or not mask & projection_bit))
                            or (args.representation == "mixed_mxfp4_q3_k"
                                and (not args.compact_expert_mask & (1 << (index // 3))
                                     or not mask & projection_bit))
                            else padded_bias)
                    candidate_blobs.extend((selected, bias))
                    candidate_weight_bytes += len(selected)
                candidate, candidate_ms = calculate(
                    candidate_function, ffn, router, candidate_blobs, gates, mask)
                delta = candidate.astype(np.float64) - reference.astype(np.float64)
                contribution = reference.astype(np.float64) - ffn.astype(np.float64)
                observations.append({
                    "capture": capture_path.name, "layer": capture["layer"],
                    "route": capture["route"], "q2_projection_mask": mask,
                    "reference_compute_ms": reference_ms, "candidate_compute_ms": candidate_ms,
                    "compute_speedup": reference_ms / candidate_ms,
                    "original_weight_bytes": original_weight_bytes,
                    "candidate_weight_bytes": candidate_weight_bytes,
                    "weight_reduction": original_weight_bytes / candidate_weight_bytes,
                    "output_relative_l2": float(np.linalg.norm(delta) / np.linalg.norm(reference)),
                    "contribution_relative_l2": float(np.linalg.norm(delta)
                                                      / np.linalg.norm(contribution)),
                    "output_max_abs": float(np.abs(delta).max()),
                    "argmax_equal": int(np.argmax(candidate)) == int(np.argmax(reference)),
                })
            print(f"holdout {capture_path.name}", flush=True)
    summaries = {}
    advancing_masks = []
    output_error_limit = (0.02 if args.representation in
                          ("top3_mxfp4_q2_0", "top3_mxfp4_q3_k",
                           "mixed_mxfp4_q3_k", "mixed_mxfp4_q2_0")
                          else 0.05)
    minimum_weight_reduction = (1.005 if args.representation in
                                ("top3_mxfp4_q3_k", "mixed_mxfp4_q3_k",
                                 "mixed_mxfp4_q2_0")
                                else 1.15)
    masks = ((None,) if args.representation in
             ("top1_mxfp4_q2_0", "top3_mxfp4_q2_0") else
             range(1, 8) if args.representation in
             ("top3_mxfp4_q3_k", "mixed_mxfp4_q3_k", "mixed_mxfp4_q2_0") else
             range(1, 8) if args.representation == "q2_0" else
             range(0, 8) if args.representation == "padded_mixed_k" else (7,))
    for mask in masks:
        rows = [row for row in observations if row["q2_projection_mask"] == mask]
        output_errors = [row["output_relative_l2"] for row in rows]
        contribution_errors = [row["contribution_relative_l2"] for row in rows]
        summary = {"mask": mask, "samples": len(rows),
                   "weight_reduction": min(row["weight_reduction"] for row in rows),
                   "compute_speedup_p50": statistics.median(
                       row["compute_speedup"] for row in rows),
                   "output_relative_l2_p50": statistics.median(output_errors),
                   "output_relative_l2_p95": percentile(output_errors, .95),
                   "contribution_relative_l2_p50": statistics.median(contribution_errors),
                   "contribution_relative_l2_p95": percentile(contribution_errors, .95),
                   "all_argmax_equal": all(row["argmax_equal"] for row in rows)}
        summaries[str(mask)] = summary
        if (summary["weight_reduction"] >= minimum_weight_reduction
                and summary["output_relative_l2_p95"] <= output_error_limit
                and summary["contribution_relative_l2_p95"] <= .25
                and summary["all_argmax_equal"]):
            advancing_masks.append(mask)
    passed = bool(advancing_masks)
    report = {
        "schema": "aion.gptoss-120b-q2-0-expert-gate.v1",
        "status": "ADVANCE_COMPACT_EXPERTS" if passed else "STOP_COMPACT_EXPERTS",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": "GPT-OSS 120B Q4_K_M/MXFP4", "quality_track": True,
        "candidate_representation": args.representation,
        "compact_expert_mask": (args.compact_expert_mask
                                if args.representation in
                                ("mixed_mxfp4_q3_k", "mixed_mxfp4_q2_0") else None),
        "capture_paths": [str(path.resolve()) for path in captures],
        "capture_hashes": {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                           for path in captures},
        "observations": observations, "summaries": summaries,
        "advancing_masks": advancing_masks,
        "projection_mask_bits": {"1": "gate", "2": "up", "4": "down"},
        "promotion_gate": {"minimum_weight_reduction": minimum_weight_reduction,
                           "maximum_output_relative_l2_p95": output_error_limit,
                           "maximum_contribution_relative_l2_p95": .25,
                           "all_argmax_equal": True},
        "warehouse_metrics": store.metrics(),
        "claim_boundary": (
            "Held-out real layer routes use the unrestricted selected experts, original gates "
            "and biases. The selected quality-track representation changes only the declared "
            "expert matrices to the declared compact representation. This is "
            "a directly executable one-layer quality microgate, not a full compact warehouse, "
            "semantic-quality result, or generated-token speed claim."),
    }
    report["canonical_sha256"] = hashlib.sha256(json.dumps(
        report, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": report["status"], "summaries": summaries,
                      "advancing_masks": advancing_masks,
                      "canonical_sha256": report["canonical_sha256"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
