#!/usr/bin/env python3
"""Compare exact scalar and batched execution of one real resident expert."""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import statistics
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from backend.modules.aion_inference.gptoss_expert_frame_store import GptOssExpertFrameStore


WIDTH = 2880


def deterministic_inputs(batch: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    columns = np.arange(WIDTH, dtype=np.float32)
    ffn = np.stack([np.cos(columns * np.float32(0.002 + row * 0.00001))
                    for row in range(batch)]).astype(np.float32)
    router = np.stack([np.sin(columns * np.float32(0.00390625 + row * 0.00001))
                       for row in range(batch)]).astype(np.float32)
    gates = np.asarray([0.2 + 0.6 * (row + 1) / (batch + 1)
                        for row in range(batch)], dtype=np.float32)
    return ffn, router, gates


def p95(values: list[float]) -> float:
    ordered = sorted(values)
    return ordered[int(0.95 * (len(ordered) - 1))]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--layer", type=int, default=0)
    parser.add_argument("--expert", type=int, default=0)
    parser.add_argument("--threads", type=int, default=6)
    parser.add_argument("--rounds", type=int, default=12)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("refusing to overwrite evidence")
    store = GptOssExpertFrameStore(args.manifest, 64 * 1024 * 1024)
    value = store.get(args.layer, args.expert)
    blobs = [value[projection][kind] for projection in ("gate", "up", "down")
             for kind in ("weight", "bias")]
    references = [ctypes.c_char_p(blob) for blob in blobs]
    pointers = (ctypes.c_void_p * 6)(*[
        ctypes.cast(reference, ctypes.c_void_p).value for reference in references
    ])
    native = Path(__file__).parents[1] / "modules/aion_inference/native/gptoss_persistent_moe_library.cpp"
    with tempfile.TemporaryDirectory(prefix="aion-gptoss-exact-batch-") as temporary:
        library = Path(temporary) / "moe.dylib"
        subprocess.run([
            "clang++", "-std=c++17", "-O3", "-dynamiclib", "-I/opt/homebrew/include",
            str(native), "-L/opt/homebrew/lib", "-lggml", "-lggml-base", "-ldl",
            "-o", str(library),
        ], check=True)
        loaded = ctypes.CDLL(str(library))
        scalar = loaded.aion_gptoss_moe_finish_active
        scalar.argtypes = [ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_float),
                           ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(ctypes.c_float),
                           ctypes.c_int, ctypes.POINTER(ctypes.c_float), ctypes.c_int,
                           ctypes.POINTER(ctypes.c_double)]
        batch_function = loaded.aion_gptoss_moe_finish_one_expert_batch
        batch_function.argtypes = [ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_float),
                                   ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(ctypes.c_float),
                                   ctypes.c_int, ctypes.POINTER(ctypes.c_float), ctypes.c_int,
                                   ctypes.POINTER(ctypes.c_double)]
        samples = []
        for batch in (1, 2, 4, 8, 16, 32):
            ffn, router, gates = deterministic_inputs(batch)
            scalar_times: list[float] = []
            batch_times: list[float] = []
            exact = True
            for _ in range(args.rounds):
                scalar_outputs = []
                scalar_started = time.perf_counter_ns()
                for row in range(batch):
                    output = np.empty(WIDTH, dtype=np.float32)
                    elapsed = ctypes.c_double()
                    status = scalar(
                        ffn[row].ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                        router[row].ctypes.data_as(ctypes.POINTER(ctypes.c_float)), pointers,
                        gates[row:].ctypes.data_as(ctypes.POINTER(ctypes.c_float)), 1,
                        output.ctypes.data_as(ctypes.POINTER(ctypes.c_float)), args.threads,
                        ctypes.byref(elapsed),
                    )
                    if status:
                        raise RuntimeError(f"scalar native status {status}")
                    scalar_outputs.append(output)
                scalar_times.append((time.perf_counter_ns() - scalar_started) / 1_000_000)
                output = np.empty((batch, WIDTH), dtype=np.float32)
                elapsed = ctypes.c_double()
                batch_started = time.perf_counter_ns()
                status = batch_function(
                    ffn.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                    router.ctypes.data_as(ctypes.POINTER(ctypes.c_float)), pointers,
                    gates.ctypes.data_as(ctypes.POINTER(ctypes.c_float)), batch,
                    output.ctypes.data_as(ctypes.POINTER(ctypes.c_float)), args.threads,
                    ctypes.byref(elapsed),
                )
                if status:
                    raise RuntimeError(f"batch native status {status}")
                batch_times.append((time.perf_counter_ns() - batch_started) / 1_000_000)
                exact = exact and output.tobytes() == np.stack(scalar_outputs).tobytes()
            scalar_p50 = statistics.median(scalar_times)
            batch_p50 = statistics.median(batch_times)
            samples.append({
                "batch": batch,
                "all_outputs_bitwise_equal": exact,
                "scalar_wall_p50_ms": scalar_p50,
                "scalar_wall_p95_ms": p95(scalar_times),
                "batch_wall_p50_ms": batch_p50,
                "batch_wall_p95_ms": p95(batch_times),
                "wall_speedup": scalar_p50 / batch_p50,
                "batch_activations_per_second": 1000.0 * batch / batch_p50,
            })
        _ = references
    result = {
        "schema": "aion.gptoss-120b-exact-one-expert-batch-gate.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": "GPT-OSS 120B Q4_K_M/MXFP4",
        "layer": args.layer,
        "expert": args.expert,
        "threads": args.threads,
        "rounds": args.rounds,
        "samples": samples,
        "all_outputs_bitwise_equal": all(sample["all_outputs_bitwise_equal"] for sample in samples),
        "status": "ADVANCE_GROUPED_EXACT_BLOCK" if (
            all(sample["all_outputs_bitwise_equal"] for sample in samples)
            and max(sample["wall_speedup"] for sample in samples if sample["batch"] >= 2) >= 1.5
        ) else "NOT_PROMOTED",
        "warehouse_metrics": store.metrics(),
        "claim_boundary": (
            "One real original-weight resident expert was evaluated over independent synthetic "
            "activation rows. This is an exact arithmetic microgate, not full-model speculative "
            "acceptance or generated tokens-per-second evidence."
        ),
    }
    result["canonical_sha256"] = hashlib.sha256(json.dumps(
        result, sort_keys=True, separators=(",", ":"),
    ).encode()).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": result["status"], "samples": samples,
                      "canonical_sha256": result["canonical_sha256"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
