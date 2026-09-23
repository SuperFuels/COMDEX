#!/usr/bin/env python3
"""Oracle bound for activation-addressed exact residual MXFP4 blocks."""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import importlib.util
import json
import math
import subprocess
import tempfile
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

import numpy as np
from sklearn.cluster import MiniBatchKMeans

from backend.modules.aion_inference.gptoss_expert_frame_store import (
    GptOssExpertFrameStore, ctypes_component_pointer_array,
)


WIDTH = 2880
BLOCKS_PER_ROW = WIDTH // 32
KVALUES = np.asarray((0, 1, 2, 3, 4, 6, 8, 12, 0, -1, -2, -3, -4, -6, -8, -12),
                     dtype=np.float32)


@lru_cache(maxsize=1)
def load_dictionary_helpers():
    path = Path(__file__).with_name("run_aion_gptoss_mxfp4_product_dictionary_gate.py")
    spec = importlib.util.spec_from_file_location("aion_product_dictionary", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load product dictionary helpers")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def activation_addressed_residual(original: bytes, approximate: bytes,
                                  activation: np.ndarray, fraction: float) -> bytes:
    helpers = load_dictionary_helpers()
    scales, original_codes = helpers.unpack_codes(original)
    _, approximate_codes = helpers.unpack_codes(approximate)
    delta = KVALUES[original_codes] - KVALUES[approximate_codes]
    # The common MXFP exponent scales every value in its 32-code block.  A
    # global factor would not change ordering, but per-block exponents do.
    exponents = scales.astype(np.int16) - 127
    scale_values = np.ldexp(np.ones(len(scales), dtype=np.float32), exponents)
    inputs = activation.reshape(BLOCKS_PER_ROW, 32)
    block_effect = np.abs(np.sum(
        delta.reshape(WIDTH, BLOCKS_PER_ROW, 32) * inputs[None, :, :], axis=2)
        * scale_values.reshape(WIDTH, BLOCKS_PER_ROW))
    retain = min(block_effect.size, math.ceil(block_effect.size * fraction))
    if retain:
        selected = np.argpartition(block_effect.reshape(-1), -retain)[-retain:]
        flat = approximate_codes.reshape(-1, 32)
        flat[selected] = original_codes.reshape(-1, 32)[selected]
    return helpers.pack_codes(scales, approximate_codes)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--activations", type=Path, required=True)
    parser.add_argument("--fractions", default="0.05,0.10,0.25")
    parser.add_argument("--train-captures", type=int, default=4)
    parser.add_argument("--holdout-captures", type=int, default=4)
    parser.add_argument("--samples-per-weight", type=int, default=1024)
    parser.add_argument("--seed", type=int, default=1200911)
    parser.add_argument("--threads", type=int, default=8)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("refusing to overwrite evidence")
    fractions = sorted({float(value) for value in args.fractions.split(",")})
    if not fractions or fractions[0] < 0 or fractions[-1] > 1:
        raise SystemExit("fractions must be within [0, 1]")
    helpers = load_dictionary_helpers()
    captures = sorted(args.activations.glob("position-*-layer-*.json"))
    required = args.train_captures + args.holdout_captures
    if len(captures) < required:
        raise SystemExit("insufficient captures")
    train_paths = captures[:args.train_captures]
    holdout_paths = captures[args.train_captures:required]
    rng = np.random.default_rng(args.seed)
    store = GptOssExpertFrameStore(args.manifest, 512 * 1024 * 1024)
    training_vectors = []
    training_experts = set()
    for capture_path in train_paths:
        capture = json.loads(capture_path.read_text())
        values = store.get_layer_route_parallel(capture["layer"], capture["route"], workers=4)
        for expert, value in zip(capture["route"], values, strict=True):
            training_experts.add((capture["layer"], expert))
            for projection in ("gate", "up", "down"):
                _, codes = helpers.unpack_codes(value[projection]["weight"])
                vectors = codes.reshape(-1, 16)
                selected = rng.choice(len(vectors), size=min(args.samples_per_weight, len(vectors)),
                                      replace=False)
                training_vectors.append(KVALUES[vectors[selected]])
    model = MiniBatchKMeans(n_clusters=256, random_state=args.seed, batch_size=4096,
                            max_iter=100, n_init=3, reassignment_ratio=.01).fit(
                                np.concatenate(training_vectors).astype(np.float32))
    dictionary_codes = helpers.nearest_mxfp4_codes(model.cluster_centers_)

    native = Path(__file__).parents[1] / "modules/aion_inference/native/gptoss_persistent_moe_library.cpp"
    observations = {str(fraction): [] for fraction in fractions}
    with tempfile.TemporaryDirectory(prefix="aion-activation-residual-oracle-") as temporary:
        library_path = Path(temporary) / "moe.dylib"
        subprocess.run(["clang++", "-std=c++17", "-O3", "-dynamiclib",
                        "-I/opt/homebrew/include", str(native), "-L/opt/homebrew/lib",
                        "-lggml", "-lggml-base", "-ldl", "-o", str(library_path)], check=True)
        library = ctypes.CDLL(str(library_path))
        finish = library.aion_gptoss_moe_finish
        finish.argtypes = [ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_float),
                           ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(ctypes.c_float),
                           ctypes.POINTER(ctypes.c_float), ctypes.c_int,
                           ctypes.POINTER(ctypes.c_double)]
        finish.restype = ctypes.c_int
        gate_up = library.aion_gptoss_expert_gate_up
        gate_up.argtypes = [ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_void_p),
                            ctypes.POINTER(ctypes.c_float), ctypes.c_int,
                            ctypes.POINTER(ctypes.c_double)]
        gate_up.restype = ctypes.c_int

        def calculate(ffn, router, blobs, gates):
            references, pointers = ctypes_component_pointer_array(blobs)
            output = np.empty(WIDTH, dtype=np.float32)
            elapsed = ctypes.c_double()
            status = finish(ffn.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                            router.ctypes.data_as(ctypes.POINTER(ctypes.c_float)), pointers,
                            gates.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                            output.ctypes.data_as(ctypes.POINTER(ctypes.c_float)), args.threads,
                            ctypes.byref(elapsed))
            if status:
                raise RuntimeError(f"finish status {status}")
            _ = references
            return output

        def calculate_hidden(router, expert_blobs):
            references, pointers = ctypes_component_pointer_array(expert_blobs[:4])
            hidden = np.empty(WIDTH, dtype=np.float32)
            elapsed = ctypes.c_double()
            status = gate_up(router.ctypes.data_as(ctypes.POINTER(ctypes.c_float)), pointers,
                             hidden.ctypes.data_as(ctypes.POINTER(ctypes.c_float)), args.threads,
                             ctypes.byref(elapsed))
            if status:
                raise RuntimeError(f"gate/up status {status}")
            _ = references
            return hidden

        for capture_path in holdout_paths:
            capture = json.loads(capture_path.read_text())
            if training_experts.intersection((capture["layer"], expert)
                                             for expert in capture["route"]):
                raise SystemExit("holdout overlaps training expert")
            stem = capture_path.with_suffix("")
            ffn = np.fromfile(Path(str(stem) + "-ffn.bin"), dtype="<f4")
            router = np.fromfile(Path(str(stem) + "-router.bin"), dtype="<f4")
            values = store.get_layer_route_parallel(capture["layer"], capture["route"], workers=4)
            original_blobs = [value[p][k] for value in values for p in ("gate", "up", "down")
                              for k in ("weight", "bias")]
            gates = np.asarray(capture["gates"], dtype=np.float32)
            reference = calculate(ffn, router, original_blobs, gates)
            raw_weight_bytes = sum(len(original_blobs[index])
                                   for index in range(0, len(original_blobs), 2))
            base_weights = [{projection: helpers.quantize_blob(
                value[projection]["weight"], dictionary_codes)[0]
                for projection in ("gate", "up", "down")} for value in values]
            for fraction in fractions:
                candidate_blobs = []
                for expert_index, value in enumerate(values):
                    expert_blobs = []
                    for projection in ("gate", "up"):
                        corrected = activation_addressed_residual(
                            value[projection]["weight"],
                            base_weights[expert_index][projection], router, fraction)
                        expert_blobs.extend((corrected, value[projection]["bias"]))
                    # The down residual is addressed by the candidate expert's
                    # actual non-linear hidden vector, not the router input.
                    hidden = calculate_hidden(router, expert_blobs)
                    corrected = activation_addressed_residual(
                        value["down"]["weight"], base_weights[expert_index]["down"],
                        hidden, fraction)
                    expert_blobs.extend((corrected, value["down"]["bias"]))
                    candidate_blobs.extend(expert_blobs)
                candidate = calculate(ffn, router, candidate_blobs, gates)
                delta = candidate.astype(np.float64) - reference.astype(np.float64)
                contribution = reference.astype(np.float64) - ffn.astype(np.float64)
                # Per 32-code block: two dictionary bytes, one retained scale,
                # one residual-bitmap bit, and 16 exact code bytes when selected.
                compact_per_block = 3.0 + 0.125 + 16.0 * fraction
                reduction = 17.0 / compact_per_block
                observations[str(fraction)].append({
                    "capture": capture_path.name, "layer": capture["layer"],
                    "route": capture["route"], "projected_weight_reduction": reduction,
                    "output_relative_l2": float(np.linalg.norm(delta) / np.linalg.norm(reference)),
                    "contribution_relative_l2": float(np.linalg.norm(delta)
                                                      / np.linalg.norm(contribution)),
                    "argmax_equal": int(np.argmax(candidate)) == int(np.argmax(reference)),
                    "raw_weight_bytes": raw_weight_bytes,
                })
            print(f"holdout {capture_path.name}", flush=True)

    summaries = {}
    advancing = []
    for fraction in fractions:
        rows = observations[str(fraction)]
        output_errors = [row["output_relative_l2"] for row in rows]
        contribution_errors = [row["contribution_relative_l2"] for row in rows]
        summary = {
            "fraction": fraction, "samples": len(rows),
            "projected_weight_reduction": rows[0]["projected_weight_reduction"],
            "output_relative_l2_max": max(output_errors),
            "contribution_relative_l2_max": max(contribution_errors),
            "all_argmax_equal": all(row["argmax_equal"] for row in rows),
        }
        summaries[str(fraction)] = summary
        if (summary["projected_weight_reduction"] >= 2.0
                and summary["output_relative_l2_max"] <= .02
                and summary["contribution_relative_l2_max"] <= .15
                and summary["all_argmax_equal"]):
            advancing.append(fraction)
    report = {
        "schema": "aion.gptoss-120b-activation-addressed-residual-oracle.v1",
        "status": "ADVANCE_ACTIVATION_RESIDUAL" if advancing else "STOP_ACTIVATION_RESIDUAL",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": "GPT-OSS 120B Q4_K_M/MXFP4", "quality_track": True,
        "oracle_bound": True, "fractions": fractions,
        "train_capture_paths": [str(path.resolve()) for path in train_paths],
        "holdout_capture_paths": [str(path.resolve()) for path in holdout_paths],
        "dictionary_sha256": hashlib.sha256(dictionary_codes.tobytes()).hexdigest(),
        "observations": observations, "summaries": summaries,
        "advancing_fractions": advancing,
        "promotion_gate": {"minimum_weight_reduction": 2.0,
                           "maximum_output_relative_l2": .02,
                           "maximum_contribution_relative_l2": .15,
                           "all_argmax_equal": True},
        "warehouse_metrics": store.metrics(),
        "claim_boundary": (
            "Optimistic oracle microgate only. Exact residual MXFP4 blocks are selected using "
            "their true dot-product error against each held-out activation. A deployable runtime "
            "cannot know this score without a predictor or residual sketch. Passing establishes "
            "an existence bound only; it does not establish a compact warehouse, selection cost, "
            "semantic quality, or generated-token speed."),
    }
    report["canonical_sha256"] = hashlib.sha256(json.dumps(
        report, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": report["status"], "summaries": summaries,
                      "canonical_sha256": report["canonical_sha256"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
