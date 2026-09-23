#!/usr/bin/env python3
"""Screen lower-bit MXFP4 codebooks on frozen real GPT-OSS activations.

This is a simulation gate: weights remain in the original 17-byte MXFP4 block
layout while codes are restricted to codebooks representable in 3 or 2 bits.
No compact warehouse or kernel is claimed by this script.
"""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import itertools
import importlib.util
import json
import statistics
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

_STORE_PATH = Path(__file__).parents[1] / "modules/aion_inference/gptoss_expert_frame_store.py"
_STORE_SPEC = importlib.util.spec_from_file_location("aion_gptoss_expert_frame_store", _STORE_PATH)
if _STORE_SPEC is None or _STORE_SPEC.loader is None:
    raise RuntimeError("cannot load GPT-OSS expert frame store")
_STORE_MODULE = importlib.util.module_from_spec(_STORE_SPEC)
_STORE_SPEC.loader.exec_module(_STORE_MODULE)
GptOssExpertFrameStore = _STORE_MODULE.GptOssExpertFrameStore


WIDTH = 2880
KVALUES = np.asarray((0, 1, 2, 3, 4, 6, 8, 12, 0, -1, -2, -3, -4, -6, -8, -12), dtype=np.int16)


def percentile(values: list[float], fraction: float) -> float:
    return sorted(values)[int(fraction * (len(values) - 1))]


def code_histogram(weight_blobs: list[bytes]) -> np.ndarray:
    counts = np.zeros(16, dtype=np.int64)
    for blob in weight_blobs:
        raw = np.frombuffer(blob, dtype=np.uint8).reshape(-1, 17)[:, 1:]
        counts += np.bincount((raw & 15).ravel(), minlength=16)
        counts += np.bincount((raw >> 4).ravel(), minlength=16)
    return counts


def make_lut(magnitudes: tuple[int, ...]) -> np.ndarray:
    allowed_values = np.asarray((0, *magnitudes, *(-value for value in magnitudes)), dtype=np.int16)
    allowed_codes = []
    for value in allowed_values:
        matches = np.flatnonzero(KVALUES == value)
        allowed_codes.append(int(matches[0]))
    result = np.empty(16, dtype=np.uint8)
    for code, value in enumerate(KVALUES):
        result[code] = allowed_codes[int(np.argmin(np.abs(allowed_values - value)))]
    return result


def restrict_codes(blob: bytes, lut: np.ndarray) -> bytes:
    result = np.frombuffer(blob, dtype=np.uint8).copy().reshape(-1, 17)
    packed = result[:, 1:]
    packed[:] = lut[packed & 15] | (lut[packed >> 4] << 4)
    return result.reshape(-1).tobytes()


def restrict_codes_block_adaptive(blob: bytes, luts: list[np.ndarray]) -> bytes:
    """Choose the lowest code-space squared-error LUT independently per block."""
    result = np.frombuffer(blob, dtype=np.uint8).copy().reshape(-1, 17)
    for begin in range(0, len(result), 100_000):
        packed = result[begin:begin + 100_000, 1:]
        low = packed & 15; high = packed >> 4
        errors = np.empty((len(luts), len(packed)), dtype=np.int32)
        for index, lut in enumerate(luts):
            low_delta = KVALUES[low] - KVALUES[lut[low]]
            high_delta = KVALUES[high] - KVALUES[lut[high]]
            errors[index] = (np.square(low_delta).sum(axis=1)
                             + np.square(high_delta).sum(axis=1))
        choices = np.argmin(errors, axis=0)
        original_low = low.copy(); original_high = high.copy()
        for index, lut in enumerate(luts):
            selected = choices == index
            if np.any(selected):
                packed[selected] = lut[original_low[selected]] | (lut[original_high[selected]] << 4)
    return result.reshape(-1).tobytes()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--activations", type=Path, required=True)
    parser.add_argument("--threads", type=int, default=8)
    parser.add_argument("--max-captures", type=int)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("refusing to overwrite evidence")
    captures = sorted(args.activations.glob("position-*-layer-*.json"))
    if args.max_captures is not None:
        captures = captures[:args.max_captures]
    if not captures:
        raise SystemExit("no activation captures found")

    store = GptOssExpertFrameStore(args.manifest, 256 * 1024 * 1024)
    native = Path(__file__).parents[1] / "modules/aion_inference/native/gptoss_persistent_moe_library.cpp"
    observations = []
    selected_codebooks: dict[str, tuple[int, ...]] | None = None
    with tempfile.TemporaryDirectory(prefix="aion-gptoss-lowbit-") as temporary:
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

        for capture_index, capture_path in enumerate(captures):
            capture = json.loads(capture_path.read_text()); stem = capture_path.with_suffix("")
            ffn = np.fromfile(Path(str(stem) + "-ffn.bin"), dtype="<f4")
            router = np.fromfile(Path(str(stem) + "-router.bin"), dtype="<f4")
            values = store.get_layer_route_parallel(capture["layer"], capture["route"], workers=4)
            blobs = [value[projection][kind] for value in values
                     for projection in ("gate", "up", "down") for kind in ("weight", "bias")]
            weights = [blobs[index] for index in range(0, len(blobs), 2)]
            if selected_codebooks is None:
                histogram = code_histogram(weights)
                candidates = []
                for bits, count in ((3, 3), (2, 1)):
                    for magnitudes in itertools.combinations((1, 2, 3, 4, 6, 8, 12), count):
                        lut = make_lut(magnitudes)
                        error = float(np.sum(histogram * np.square(KVALUES - KVALUES[lut])))
                        candidates.append((bits, error, magnitudes))
                selected_codebooks = {}
                for bits, keep in ((3, 3), (2, 2)):
                    ranked = sorted(item for item in candidates if item[0] == bits)[:keep]
                    for rank, (_, _, magnitudes) in enumerate(ranked, 1):
                        selected_codebooks[f"q{bits}_rank{rank}_{'_'.join(map(str, magnitudes))}"] = magnitudes

            gates = np.asarray(capture["gates"], dtype=np.float32)
            full = calculate(ffn, router, blobs, gates)
            full_contribution = full.astype(np.float64) - ffn.astype(np.float64)
            candidates_out = {}
            candidate_specs = [(name, [make_lut(magnitudes)], magnitudes)
                               for name, magnitudes in selected_codebooks.items()]
            q3_sets = list(itertools.combinations((1, 2, 3, 4, 6, 8, 12), 3))
            q2_sets = [(value,) for value in (1, 2, 3, 4, 6, 8, 12)]
            candidate_specs.extend((("q3_blockadaptive35", [make_lut(x) for x in q3_sets], ()),
                                    ("q2_blockadaptive7", [make_lut(x) for x in q2_sets], ())))
            for name, luts, magnitudes in candidate_specs:
                candidate_blobs = [
                    (restrict_codes(blob, luts[0]) if len(luts) == 1
                     else restrict_codes_block_adaptive(blob, luts)) if index % 2 == 0 else blob
                    for index, blob in enumerate(blobs)]
                candidate = calculate(ffn, router, candidate_blobs, gates)
                delta = candidate.astype(np.float64) - full.astype(np.float64)
                contribution_delta = candidate.astype(np.float64) - ffn.astype(np.float64) - full_contribution
                bits = int(name[1])
                metadata_bits = 0 if len(luts) == 1 else (6 if bits == 3 else 3)
                packed_bytes_per_block = 1 + (32 * bits + metadata_bits) / 8
                candidates_out[name] = {
                    "bits_per_code": bits,
                    "magnitudes": list(magnitudes),
                    "per_block_codebooks": len(luts),
                    "projected_weight_reduction": 17 / packed_bytes_per_block,
                    "output_relative_l2": float(np.linalg.norm(delta) / np.linalg.norm(full)),
                    "contribution_relative_l2": float(np.linalg.norm(contribution_delta) / np.linalg.norm(full_contribution)),
                    "output_max_abs": float(np.abs(delta).max()),
                }
            observations.append({"position": capture["position"], "layer": capture["layer"],
                                 "route": capture["route"], "candidates": candidates_out})
            print(f"capture {capture_index + 1}/{len(captures)}", flush=True)

    summaries = {}
    for name in observations[0]["candidates"]:
        rows = [observation["candidates"][name] for observation in observations]
        summaries[name] = {
            "samples": len(rows), "bits_per_code": rows[0]["bits_per_code"],
            "magnitudes": rows[0]["magnitudes"],
            "projected_weight_reduction": rows[0]["projected_weight_reduction"],
            "output_relative_l2_p50": statistics.median(x["output_relative_l2"] for x in rows),
            "output_relative_l2_p95": percentile([x["output_relative_l2"] for x in rows], .95),
            "contribution_relative_l2_p50": statistics.median(x["contribution_relative_l2"] for x in rows),
            "contribution_relative_l2_p95": percentile([x["contribution_relative_l2"] for x in rows], .95),
            "output_max_abs_p95": percentile([x["output_max_abs"] for x in rows], .95),
        }
    advancing = [name for name, row in summaries.items()
                 if row["projected_weight_reduction"] >= 1.3
                 and row["output_relative_l2_p95"] <= .02
                 and row["contribution_relative_l2_p95"] <= .15]
    report = {
        "schema": "aion.gptoss-120b-mxfp4-lowbit-codebook-gate.v1",
        "status": "ADVANCE_LOWBIT_PACKED_KERNEL" if advancing else "STOP_LOWBIT_CODEBOOKS",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": "GPT-OSS 120B Q4_K_M/MXFP4", "quality_track": True,
        "observations": observations, "summaries": summaries, "advancing_candidates": advancing,
        "promotion_gate": {"minimum_projected_weight_reduction": 1.3,
                           "maximum_output_relative_l2_p95": .02,
                           "maximum_contribution_relative_l2_p95": .15},
        "warehouse_metrics": store.metrics(),
        "capture_file_hashes": {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                                for path in sorted(args.activations.iterdir())},
        "claim_boundary": (
            "This is a real-activation simulation using original MXFP4 blocks whose codes are "
            "restricted to small symmetric codebooks. The files and native kernel remain four-bit, "
            "so size reduction is projected from a future packed representation; no generated-token "
            "speed, compact warehouse, or model-quality promotion is claimed by this gate."),
    }
    body = json.dumps(report, sort_keys=True, separators=(",", ":"))
    report["canonical_sha256"] = hashlib.sha256(body.encode()).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": report["status"], "advancing_candidates": advancing,
                      "summaries": summaries, "canonical_sha256": report["canonical_sha256"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
