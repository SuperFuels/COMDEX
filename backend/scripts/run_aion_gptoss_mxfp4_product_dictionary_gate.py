#!/usr/bin/env python3
"""Holdout gate for a shared product dictionary over real MXFP4 weight blocks.

The immutable source weights are not rewritten.  A dictionary is derived from
training-only expert blocks, then applied to disjoint routed experts and real
activations.  Compact size is projected; no packed kernel or model speed is
claimed.
"""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import importlib.util
import json
import math
import statistics
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from sklearn.cluster import MiniBatchKMeans


_STORE_PATH = Path(__file__).parents[1] / "modules/aion_inference/gptoss_expert_frame_store.py"
_SPEC = importlib.util.spec_from_file_location("aion_gptoss_expert_frame_store", _STORE_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError("cannot load GPT-OSS expert frame store")
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
GptOssExpertFrameStore = _MODULE.GptOssExpertFrameStore


WIDTH = 2880
KVALUES = np.asarray((0, 1, 2, 3, 4, 6, 8, 12, 0, -1, -2, -3, -4, -6, -8, -12),
                     dtype=np.float32)


def percentile(values: list[float], fraction: float) -> float:
    return sorted(values)[max(0, math.ceil(fraction * len(values)) - 1)]


def unpack_codes(blob: bytes) -> tuple[np.ndarray, np.ndarray]:
    blocks = np.frombuffer(blob, dtype=np.uint8).reshape(-1, 17)
    packed = blocks[:, 1:]
    codes = np.empty((len(blocks), 32), dtype=np.uint8)
    codes[:, 0::2] = packed & 15
    codes[:, 1::2] = packed >> 4
    return blocks[:, 0].copy(), codes


def pack_codes(scales: np.ndarray, codes: np.ndarray) -> bytes:
    result = np.empty((len(scales), 17), dtype=np.uint8)
    result[:, 0] = scales
    result[:, 1:] = codes[:, 0::2] | (codes[:, 1::2] << 4)
    return result.tobytes()


def nearest_mxfp4_codes(centers: np.ndarray) -> np.ndarray:
    distances = np.abs(centers[:, :, None] - KVALUES[None, None, :])
    return np.argmin(distances, axis=2).astype(np.uint8)


def quantize_blob(blob: bytes, dictionary_codes: np.ndarray,
                  exact_residual_fraction: float = 0.0,
                  chunk_vectors: int = 8192) -> tuple[bytes, np.ndarray, int]:
    scales, codes = unpack_codes(blob)
    vector_codes = dictionary_codes.shape[1]
    vectors = codes.reshape(-1, vector_codes)
    dictionary_values = KVALUES[dictionary_codes].astype(np.float32)
    dictionary_norm = np.square(dictionary_values).sum(axis=1)
    indices = np.empty(len(vectors), dtype=np.uint8)
    reconstructed = np.empty_like(vectors)
    for begin in range(0, len(vectors), chunk_vectors):
        batch_codes = vectors[begin:begin + chunk_vectors]
        batch = KVALUES[batch_codes].astype(np.float32)
        distance = (np.square(batch).sum(axis=1, keepdims=True)
                    + dictionary_norm[None, :] - 2.0 * batch @ dictionary_values.T)
        selected = np.argmin(distance, axis=1).astype(np.uint8)
        indices[begin:begin + len(batch)] = selected
        reconstructed[begin:begin + len(batch)] = dictionary_codes[selected]
    residual_count = min(len(vectors), math.ceil(len(vectors) * exact_residual_fraction))
    if residual_count:
        errors = np.square(KVALUES[vectors] - KVALUES[reconstructed]).sum(axis=1)
        exact = np.argpartition(errors, -residual_count)[-residual_count:]
        reconstructed[exact] = vectors[exact]
    return pack_codes(scales, reconstructed.reshape(-1, 32)), indices, residual_count


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--activations", type=Path, required=True)
    parser.add_argument("--train-captures", type=int, default=4)
    parser.add_argument("--holdout-captures", type=int, default=2)
    parser.add_argument("--samples-per-weight", type=int, default=1024)
    parser.add_argument("--dictionary-size", type=int, default=256)
    parser.add_argument("--subvector-codes", type=int, choices=(4, 8, 16), default=16)
    parser.add_argument("--minimum-reduction", type=float, default=5.0)
    parser.add_argument("--exact-residual-fraction", type=float, default=0.0)
    parser.add_argument("--threads", type=int, default=8)
    parser.add_argument("--seed", type=int, default=1200911)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("refusing to overwrite evidence")
    if args.dictionary_size != 256:
        raise SystemExit("this gate requires a one-byte 256-entry dictionary")
    if not 0.0 <= args.exact_residual_fraction <= 1.0:
        raise SystemExit("exact residual fraction must be within [0, 1]")
    captures = sorted(args.activations.glob("position-*-layer-*.json"))
    required = args.train_captures + args.holdout_captures
    if len(captures) < required:
        raise SystemExit("insufficient activation captures")
    train_paths = captures[:args.train_captures]
    holdout_paths = captures[args.train_captures:required]
    rng = np.random.default_rng(args.seed)
    store = GptOssExpertFrameStore(args.manifest, 512 * 1024 * 1024)

    training_vectors = []
    training_experts: set[tuple[int, int]] = set()
    for capture_path in train_paths:
        capture = json.loads(capture_path.read_text())
        values = store.get_layer_route_parallel(capture["layer"], capture["route"], workers=4)
        for expert, value in zip(capture["route"], values, strict=True):
            training_experts.add((capture["layer"], expert))
            for projection in ("gate", "up", "down"):
                _, codes = unpack_codes(value[projection]["weight"])
                vectors = codes.reshape(-1, args.subvector_codes)
                count = min(args.samples_per_weight, len(vectors))
                selected = rng.choice(len(vectors), size=count, replace=False)
                training_vectors.append(KVALUES[vectors[selected]])
    training = np.concatenate(training_vectors).astype(np.float32)
    model = MiniBatchKMeans(
        n_clusters=args.dictionary_size, random_state=args.seed,
        batch_size=4096, max_iter=100, n_init=3, reassignment_ratio=0.01,
    ).fit(training)
    dictionary_codes = nearest_mxfp4_codes(model.cluster_centers_)
    dictionary_sha256 = hashlib.sha256(dictionary_codes.tobytes()).hexdigest()

    native = Path(__file__).parents[1] / "modules/aion_inference/native/gptoss_persistent_moe_library.cpp"
    observations = []
    with tempfile.TemporaryDirectory(prefix="aion-gptoss-product-dictionary-") as temporary:
        library_path = Path(temporary) / "moe.dylib"
        subprocess.run([
            "clang++", "-std=c++17", "-O3", "-dynamiclib", "-I/opt/homebrew/include",
            str(native), "-L/opt/homebrew/lib", "-lggml", "-lggml-base", "-ldl",
            "-o", str(library_path),
        ], check=True)
        library = ctypes.CDLL(str(library_path))
        function = library.aion_gptoss_moe_finish
        function.argtypes = [
            ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_float),
            ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(ctypes.c_float),
            ctypes.POINTER(ctypes.c_float), ctypes.c_int, ctypes.POINTER(ctypes.c_double),
        ]
        function.restype = ctypes.c_int

        def calculate(ffn: np.ndarray, router: np.ndarray, blobs: list[bytes],
                      gates: np.ndarray) -> tuple[np.ndarray, float]:
            references = [ctypes.c_char_p(blob) for blob in blobs]
            pointers = (ctypes.c_void_p * len(references))(*[
                ctypes.cast(reference, ctypes.c_void_p).value for reference in references])
            output = np.empty(WIDTH, dtype=np.float32)
            elapsed = ctypes.c_double()
            status = function(
                ffn.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                router.ctypes.data_as(ctypes.POINTER(ctypes.c_float)), pointers,
                gates.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                output.ctypes.data_as(ctypes.POINTER(ctypes.c_float)), args.threads,
                ctypes.byref(elapsed),
            )
            if status:
                raise RuntimeError(f"native MoE status {status}")
            return output, elapsed.value

        for capture_path in holdout_paths:
            capture = json.loads(capture_path.read_text())
            stem = capture_path.with_suffix("")
            ffn = np.fromfile(Path(str(stem) + "-ffn.bin"), dtype="<f4")
            router = np.fromfile(Path(str(stem) + "-router.bin"), dtype="<f4")
            values = store.get_layer_route_parallel(capture["layer"], capture["route"], workers=4)
            holdout_experts = {(capture["layer"], expert) for expert in capture["route"]}
            if training_experts.intersection(holdout_experts):
                raise SystemExit("holdout contains an expert used to build the dictionary")
            original_blobs = [
                value[projection][kind] for value in values
                for projection in ("gate", "up", "down") for kind in ("weight", "bias")
            ]
            compact_indices = []
            residual_counts = []
            candidate_blobs = []
            for index, blob in enumerate(original_blobs):
                if index % 2:
                    candidate_blobs.append(blob)
                else:
                    reconstructed, indices, residual_count = quantize_blob(
                        blob, dictionary_codes, args.exact_residual_fraction)
                    candidate_blobs.append(reconstructed)
                    compact_indices.append(indices)
                    residual_counts.append(residual_count)
            gates = np.asarray(capture["gates"], dtype=np.float32)
            reference, reference_ms = calculate(ffn, router, original_blobs, gates)
            candidate, candidate_ms = calculate(ffn, router, candidate_blobs, gates)
            delta = candidate.astype(np.float64) - reference.astype(np.float64)
            reference_contribution = reference.astype(np.float64) - ffn.astype(np.float64)
            raw_weight_bytes = sum(len(original_blobs[index])
                                   for index in range(0, len(original_blobs), 2))
            compact_weight_bytes = sum(indices.nbytes for indices in compact_indices)
            compact_weight_bytes += raw_weight_bytes // 17  # one E8M0 scale per block
            compact_weight_bytes += dictionary_codes.nbytes
            compact_weight_bytes += sum(math.ceil(len(indices) / 8)
                                        for indices in compact_indices)  # residual bitmaps
            compact_weight_bytes += sum(residual_counts) * (args.subvector_codes // 2)
            observations.append({
                "capture": capture_path.name, "layer": capture["layer"],
                "route": capture["route"], "reference_compute_ms": reference_ms,
                "candidate_reconstructed_compute_ms": candidate_ms,
                "raw_weight_bytes": raw_weight_bytes,
                "projected_compact_weight_bytes": compact_weight_bytes,
                "projected_weight_reduction": raw_weight_bytes / compact_weight_bytes,
                "exact_residual_vectors": sum(residual_counts),
                "output_relative_l2": float(np.linalg.norm(delta) / np.linalg.norm(reference)),
                "contribution_relative_l2": float(np.linalg.norm(delta)
                                                  / np.linalg.norm(reference_contribution)),
                "output_max_abs": float(np.abs(delta).max()),
                "argmax_equal": int(np.argmax(candidate)) == int(np.argmax(reference)),
            })
            print(f"holdout {len(observations)}/{len(holdout_paths)}", flush=True)

    output_errors = [row["output_relative_l2"] for row in observations]
    contribution_errors = [row["contribution_relative_l2"] for row in observations]
    reduction = min(row["projected_weight_reduction"] for row in observations)
    passed = (reduction >= args.minimum_reduction and percentile(output_errors, .95) <= .02
              and percentile(contribution_errors, .95) <= .15
              and all(row["argmax_equal"] for row in observations))
    report = {
        "schema": "aion.gptoss-120b-mxfp4-product-dictionary-gate.v1",
        "status": "ADVANCE_PRODUCT_DICTIONARY" if passed else "STOP_PRODUCT_DICTIONARY",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": "GPT-OSS 120B Q4_K_M/MXFP4", "quality_track": True,
        "train_capture_paths": [str(path.resolve()) for path in train_paths],
        "holdout_capture_paths": [str(path.resolve()) for path in holdout_paths],
        "training_experts": sorted([list(value) for value in training_experts]),
        "training_vectors": len(training), "dictionary_entries": len(dictionary_codes),
        "dictionary_vector_codes": args.subvector_codes,
        "exact_residual_fraction": args.exact_residual_fraction,
        "dictionary_sha256": dictionary_sha256,
        "observations": observations,
        "summary": {
            "samples": len(observations), "projected_weight_reduction_min": reduction,
            "output_relative_l2_p50": statistics.median(output_errors),
            "output_relative_l2_p95": percentile(output_errors, .95),
            "contribution_relative_l2_p50": statistics.median(contribution_errors),
            "contribution_relative_l2_p95": percentile(contribution_errors, .95),
        },
        "promotion_gate": {
            "minimum_projected_weight_reduction": args.minimum_reduction,
            "maximum_output_relative_l2_p95": .02,
            "maximum_contribution_relative_l2_p95": .15,
            "all_output_argmax_equal": True,
        },
        "warehouse_metrics": store.metrics(),
        "capture_file_hashes": {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in (*train_paths, *holdout_paths)
        },
        "claim_boundary": (
            f"A training-only shared 256-entry product dictionary represents each "
            f"{args.subvector_codes}-code MXFP4 subvector with one byte while retaining every "
            "E8M0 block scale. Evaluation "
            f"retains the highest-error {args.exact_residual_fraction:.1%} of subvectors exactly "
            "behind a residual bitmap. "
            "uses disjoint routed experts and real activations. Original-format matrices are "
            "reconstructed only to reuse the frozen reference kernel; compact size is projected. "
            "No compact warehouse, direct dictionary kernel, full-model quality, or token-speed "
            "claim is made."
        ),
    }
    report["canonical_sha256"] = hashlib.sha256(json.dumps(
        report, sort_keys=True, separators=(",", ":"),
    ).encode()).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": report["status"], "summary": report["summary"],
                      "canonical_sha256": report["canonical_sha256"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
