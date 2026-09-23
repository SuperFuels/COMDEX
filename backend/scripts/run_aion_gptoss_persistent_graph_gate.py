#!/usr/bin/env python3
"""ABBA-test graph reconstruction versus a reusable exact four-expert graph."""

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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--trace", type=Path, required=True)
    parser.add_argument("--position", type=int, default=26)
    parser.add_argument("--layer", type=int, default=0)
    parser.add_argument("--threads", type=int, default=6)
    parser.add_argument("--rounds", type=int, default=40)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("refusing to overwrite evidence")
    trace = json.loads(args.trace.read_text())
    layer = trace["run_a"]["tokens"][args.position]["layers"][args.layer]
    route, gates = layer["route"], layer["gates"]
    store = GptOssExpertFrameStore(args.manifest, 64 * 1024 * 1024)
    values = store.get_layer_route_parallel(args.layer, route, workers=4)
    blobs = [value[projection][kind] for value in values
             for projection in ("gate", "up", "down")
             for kind in ("weight", "bias")]
    references = [ctypes.c_char_p(blob) for blob in blobs]
    pointers = (ctypes.c_void_p * len(references))(*[
        ctypes.cast(reference, ctypes.c_void_p).value for reference in references
    ])
    width = 2880
    ffn = np.cos(np.arange(width, dtype=np.float32) * np.float32(.002))
    router = np.sin(np.arange(width, dtype=np.float32) * np.float32(.00390625))
    gate_values = np.asarray([float(f"{value:.9g}") for value in gates], dtype=np.float32)
    native = Path(__file__).parents[1] / "modules/aion_inference/native/gptoss_persistent_moe_library.cpp"
    with tempfile.TemporaryDirectory(prefix="aion-gptoss-persistent-graph-") as temporary:
        library = Path(temporary) / "moe.dylib"
        subprocess.run([
            "clang++", "-std=c++17", "-O3", "-dynamiclib", "-I/opt/homebrew/include",
            str(native), "-L/opt/homebrew/lib", "-lggml", "-lggml-base", "-ldl",
            "-o", str(library),
        ], check=True)
        loaded = ctypes.CDLL(str(library))
        functions = {
            "rebuild": loaded.aion_gptoss_moe_finish,
            "reuse": loaded.aion_gptoss_moe_finish_reuse_graph,
        }
        signature = [ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_float),
                     ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(ctypes.c_float),
                     ctypes.POINTER(ctypes.c_float), ctypes.c_int,
                     ctypes.POINTER(ctypes.c_double)]
        for function in functions.values():
            function.argtypes = signature
            function.restype = ctypes.c_int
        samples = {name: [] for name in functions}
        outputs = {name: [] for name in functions}
        order = ("rebuild", "reuse", "reuse", "rebuild")
        for _ in range(args.rounds):
            for name in order:
                output = np.empty(width, dtype=np.float32)
                elapsed = ctypes.c_double()
                started = time.perf_counter_ns()
                status = functions[name](
                    ffn.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                    router.ctypes.data_as(ctypes.POINTER(ctypes.c_float)), pointers,
                    gate_values.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                    output.ctypes.data_as(ctypes.POINTER(ctypes.c_float)), args.threads,
                    ctypes.byref(elapsed),
                )
                wall_ms = (time.perf_counter_ns() - started) / 1_000_000
                if status:
                    raise RuntimeError(f"{name} native status {status}")
                samples[name].append({"wall_ms": wall_ms, "native_ms": elapsed.value})
                outputs[name].append(output.tobytes())
    summaries = {}
    for name, values_for_name in samples.items():
        wall = [value["wall_ms"] for value in values_for_name]
        native_ms = [value["native_ms"] for value in values_for_name]
        summaries[name] = {
            "samples": len(wall),
            "wall_p50_ms": statistics.median(wall),
            "wall_p95_ms": sorted(wall)[int(.95 * (len(wall) - 1))],
            "native_p50_ms": statistics.median(native_ms),
            "native_p95_ms": sorted(native_ms)[int(.95 * (len(native_ms) - 1))],
        }
    all_equal = len(set(outputs["rebuild"] + outputs["reuse"])) == 1
    speedup = summaries["rebuild"]["wall_p50_ms"] / summaries["reuse"]["wall_p50_ms"]
    result = {
        "schema": "aion.gptoss-120b-persistent-moe-graph-gate.v1",
        "status": "PROMOTE_REUSABLE_EXACT_GRAPH" if all_equal and speedup >= 1.10
                  else "NOT_PROMOTED",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": "GPT-OSS 120B Q4_K_M/MXFP4",
        "trace_path": str(args.trace.resolve()),
        "trace_file_sha256": hashlib.sha256(args.trace.read_bytes()).hexdigest(),
        "position": args.position,
        "layer": args.layer,
        "route": route,
        "normalized_gates": gates,
        "threads": args.threads,
        "summaries": summaries,
        "wall_speedup": speedup,
        "all_outputs_bitwise_equal": all_equal,
        "warehouse_metrics": store.metrics(),
        "claim_boundary": (
            "One real four-expert route was repeatedly evaluated with fixed activation and "
            "weights. This isolates reusable graph metadata and preserves exact output, but "
            "does not measure full-token speed, changing routes, or SD misses."
        ),
    }
    result["canonical_sha256"] = hashlib.sha256(json.dumps(
        result, sort_keys=True, separators=(",", ":"),
    ).encode()).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: result[key] for key in (
        "status", "wall_speedup", "all_outputs_bitwise_equal", "summaries",
        "canonical_sha256",
    )}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
