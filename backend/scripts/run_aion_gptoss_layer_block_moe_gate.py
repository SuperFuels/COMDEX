#!/usr/bin/env python3
"""Execute an exact eight-position MoE layer with union-loaded experts."""

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


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(value: dict) -> str:
    body = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(body.encode()).hexdigest()


def union_schedule(tokens: list[dict], layer: int) -> list[int]:
    return sorted({expert for token in tokens for expert in token["layers"][layer]["route"]})


def compile_library(output: Path) -> None:
    source = Path(__file__).parents[1] / "modules/aion_inference/native/gptoss_persistent_moe_library.cpp"
    subprocess.run(["clang++", "-std=c++17", "-O3", "-dynamiclib",
                    "-I/opt/homebrew/include", str(source), "-L/opt/homebrew/lib",
                    "-lggml", "-lggml-base", "-ldl", "-o", str(output)], check=True)


def load_function(library_path: Path):
    loaded = ctypes.CDLL(str(library_path))
    function = loaded.aion_gptoss_moe_finish
    function.argtypes = [ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_float),
                         ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(ctypes.c_float),
                         ctypes.POINTER(ctypes.c_float), ctypes.c_int,
                         ctypes.POINTER(ctypes.c_double)]
    function.restype = ctypes.c_int
    return loaded, function


def calculate(function, values, gates, ffn: np.ndarray, router: np.ndarray,
              threads: int) -> tuple[np.ndarray, float]:
    gate_values = np.asarray([float(f"{value:.9g}") for value in gates], dtype=np.float32)
    output = np.empty(WIDTH, dtype=np.float32)
    elapsed = ctypes.c_double()
    blobs = [value[projection][kind] for value in values
             for projection in ("gate", "up", "down")
             for kind in ("weight", "bias")]
    references = [ctypes.c_char_p(blob) for blob in blobs]
    pointers = (ctypes.c_void_p * len(references))(
        *[ctypes.cast(reference, ctypes.c_void_p).value for reference in references])
    status = function(ffn.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                      router.ctypes.data_as(ctypes.POINTER(ctypes.c_float)), pointers,
                      gate_values.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                      output.ctypes.data_as(ctypes.POINTER(ctypes.c_float)), threads,
                      ctypes.byref(elapsed))
    if status:
        raise RuntimeError(f"persistent MoE failed: {status}")
    return output, elapsed.value


def run_mode(mode: str, manifest: Path, tokens: list[dict], capture_root: Path,
             layer: int, function, threads: int) -> dict:
    store = GptOssExpertFrameStore(manifest, 0)
    started = time.perf_counter()
    compute_ms = []
    exact = []
    if mode == "union":
        experts = union_schedule(tokens, layer)
        loaded = store.get_layer_route_parallel(layer, experts, workers=4)
        bank = dict(zip(experts, loaded, strict=True))
        peak_live_bytes = sum(store._value_size(value) for value in loaded)
    else:
        bank = None
        peak_live_bytes = 4 * 13_897_728
    load_finished = time.perf_counter()
    for position, token in enumerate(tokens):
        record = token["layers"][layer]
        if bank is None:
            values = store.get_layer_route_parallel(layer, record["route"], workers=4)
        else:
            values = [bank[expert] for expert in record["route"]]
        stem = capture_root / f"position-{position}-layer-{layer}"
        ffn = np.fromfile(f"{stem}-ffn.bin", dtype="<f4")
        router = np.fromfile(f"{stem}-router.bin", dtype="<f4")
        expected = Path(f"{stem}-output.bin").read_bytes()
        output, elapsed = calculate(function, values, record["gates"], ffn, router, threads)
        compute_ms.append(elapsed)
        exact.append(output.tobytes() == expected)
    wall = time.perf_counter() - started
    metrics = store.metrics()
    return {"mode": mode, "wall_seconds": wall,
            "initial_union_load_seconds": load_finished - started if mode == "union" else None,
            "compute_ms_total": sum(compute_ms), "all_outputs_bitwise_exact": all(exact),
            "exact_positions": sum(exact), "positions": len(tokens),
            "peak_live_expert_bytes": peak_live_bytes, "store_metrics": metrics}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--case", action="append", required=True,
                        help="TRACE_JSON=CAPTURE_DIRECTORY")
    parser.add_argument("--layer", type=int, default=12)
    parser.add_argument("--threads", type=int, default=8)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("refusing to overwrite evidence")
    cases = []
    parsed = []
    for value in args.case:
        trace_text, separator, capture_text = value.partition("=")
        if not separator:
            raise SystemExit("case must be TRACE_JSON=CAPTURE_DIRECTORY")
        trace_path = Path(trace_text)
        trace = json.loads(trace_path.read_text())
        tokens = trace.get("run_a", {}).get("tokens", [])
        if len(tokens) != 8 or not trace.get("routes_repeatable") or not trace.get(
                "final_hidden_and_logits_bitwise_repeatable"):
            raise SystemExit("case must be an exact repeatable eight-position trace")
        parsed.append((trace_path, Path(capture_text), tokens))
    with tempfile.TemporaryDirectory(prefix="aion-gptoss-block-moe-") as temporary:
        library_path = Path(temporary) / "libaion-gptoss-moe.dylib"
        compile_library(library_path)
        loaded, function = load_function(library_path)
        for index, (trace_path, capture_root, tokens) in enumerate(parsed):
            order = ("sequential", "union") if index % 2 == 0 else ("union", "sequential")
            runs = {mode: run_mode(mode, args.manifest, tokens, capture_root,
                                   args.layer, function, args.threads) for mode in order}
            sequential = runs["sequential"]; union = runs["union"]
            cases.append({"trace_path": str(trace_path.resolve()),
                          "trace_sha256": digest(trace_path), "capture_root": str(capture_root.resolve()),
                          "order": list(order), "layer": args.layer,
                          "unique_experts": len(union_schedule(tokens, args.layer)),
                          "sequential": sequential, "union": union,
                          "compressed_traffic_reduction": (
                              sequential["store_metrics"]["compressed_bytes_read"] /
                              union["store_metrics"]["compressed_bytes_read"]),
                          "wall_speedup": sequential["wall_seconds"] / union["wall_seconds"]})
        _ = loaded
    exact = all(case[mode]["all_outputs_bitwise_exact"] for case in cases
                for mode in ("sequential", "union"))
    traffic = [case["compressed_traffic_reduction"] for case in cases]
    speedups = [case["wall_speedup"] for case in cases]
    report = {"schema": "aion.gptoss-120b-layer-block-moe-gate.v1",
              "created_at": datetime.now(timezone.utc).isoformat(),
              "track": "exact_120b_layer_microgate", "layer": args.layer,
              "cases": cases, "all_outputs_bitwise_exact": exact,
              "compressed_traffic_reduction_p50": statistics.median(traffic),
              "wall_speedup_p50": statistics.median(speedups),
              "peak_live_expert_bytes_max": max(case["union"]["peak_live_expert_bytes"]
                                                 for case in cases),
              "acceptance": {"all_outputs_bitwise_exact": exact,
                             "traffic_reduction_above_1_10x": min(traffic) > 1.10,
                             "peak_live_experts_below_512MiB": max(
                                 case["union"]["peak_live_expert_bytes"] for case in cases)
                                 < 512 * 1024 * 1024},
              "claim_boundary": ("Real SD-backed exact layer-12 MoE microgate only. It excludes "
                                  "batched attention, draft generation, rejection, remaining layers "
                                  "and full generated-token throughput.")}
    report["status"] = ("ADVANCE_EXACT_BLOCK_RUNTIME" if all(report["acceptance"].values())
                        else "STOP_LAYER_BLOCK_MOE")
    report["canonical_sha256"] = canonical(report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": report["status"], "traffic_reduction_p50":
                      report["compressed_traffic_reduction_p50"], "wall_speedup_p50":
                      report["wall_speedup_p50"], "bitwise_exact": exact,
                      "peak_live_expert_bytes": report["peak_live_expert_bytes_max"],
                      "canonical_sha256": report["canonical_sha256"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
