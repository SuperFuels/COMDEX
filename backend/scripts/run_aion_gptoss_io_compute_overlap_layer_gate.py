#!/usr/bin/env python3
"""Measure exact overlap of internal-L2 expert reads with packed CPU compute."""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import statistics
import subprocess
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from backend.modules.aion_inference.gptoss_expert_frame_store import (
    GptOssExpertFrameStore,
    GptOssReusableArenaPersistentL2ExpertFrameStore,
    ctypes_component_pointer_array,
)


WIDTH = 2880


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    return ordered[int(fraction * (len(ordered) - 1))]


def summary(values: list[float]) -> dict[str, float | int]:
    return {
        "samples": len(values),
        "p50_ms": statistics.median(values),
        "p95_ms": percentile(values, 0.95),
        "mean_ms": statistics.mean(values),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--capture-dir", type=Path, required=True)
    parser.add_argument("--l2-root", type=Path, required=True)
    parser.add_argument("--l2-gib", type=float, default=20.0)
    parser.add_argument("--threads", type=int, default=6)
    parser.add_argument("--repeats", type=int, default=4)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("refusing to overwrite evidence")
    if args.repeats < 2 or args.threads < 1:
        raise SystemExit("repeats must be >=2 and threads must be positive")

    captures = []
    for metadata_path in sorted(args.capture_dir.glob("position-*-layer-*.json")):
        metadata = json.loads(metadata_path.read_text())
        stem = metadata_path.with_suffix("")
        ffn = np.fromfile(Path(str(stem) + "-ffn.bin"), dtype="<f4")
        router = np.fromfile(Path(str(stem) + "-router.bin"), dtype="<f4")
        if ffn.shape != (WIDTH,) or router.shape != (WIDTH,):
            raise SystemExit(f"invalid activation width: {metadata_path}")
        if len(metadata["route"]) != 4 or len(set(metadata["route"])) != 4:
            raise SystemExit(f"invalid route: {metadata_path}")
        captures.append((metadata_path, metadata, ffn, router))
    if not captures:
        raise SystemExit("capture directory contains no real activation records")

    native = Path(__file__).parents[1] / "modules/aion_inference/native"
    with tempfile.TemporaryDirectory(prefix="aion-gptoss-overlap-") as temporary:
        library_path = Path(temporary) / "libaion-gptoss-moe.dylib"
        subprocess.run([
            "clang++", "-std=c++17", "-O3", "-dynamiclib",
            "-I/opt/homebrew/include",
            str(native / "gptoss_persistent_moe_library.cpp"),
            "-L/opt/homebrew/lib", "-lggml", "-lggml-base", "-ldl",
            "-o", str(library_path),
        ], check=True)
        library = ctypes.CDLL(str(library_path))
        full = library.aion_gptoss_moe_finish
        full.argtypes = [ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_float),
                         ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(ctypes.c_float),
                         ctypes.POINTER(ctypes.c_float), ctypes.c_int,
                         ctypes.POINTER(ctypes.c_double)]
        full.restype = ctypes.c_int
        contribution = library.aion_gptoss_one_expert_contribution_batch
        contribution.argtypes = [ctypes.POINTER(ctypes.c_float),
                                 ctypes.POINTER(ctypes.c_void_p),
                                 ctypes.POINTER(ctypes.c_float), ctypes.c_int,
                                 ctypes.POINTER(ctypes.c_float), ctypes.c_int,
                                 ctypes.POINTER(ctypes.c_double)]
        contribution.restype = ctypes.c_int
        combine = library.aion_gptoss_combine_four_contributions
        combine.argtypes = [ctypes.POINTER(ctypes.c_float),
                            ctypes.POINTER(ctypes.c_float), ctypes.c_int,
                            ctypes.POINTER(ctypes.c_float)]
        combine.restype = ctypes.c_int

        store = GptOssReusableArenaPersistentL2ExpertFrameStore(
            args.manifest, 0, args.l2_root, int(args.l2_gib * 1024 ** 3))

        def pointers(value):
            blobs = [value[projection][kind]
                     for projection in ("gate", "up", "down")
                     for kind in ("weight", "bias")]
            return ctypes_component_pointer_array(blobs)

        def baseline(layer, route, gates, ffn, router):
            started = time.perf_counter()
            values = store.get_layer_route_parallel(layer, route, workers=4)
            refs, ptrs = ctypes_component_pointer_array([
                value[projection][kind] for value in values
                for projection in ("gate", "up", "down")
                for kind in ("weight", "bias")])
            output = np.empty(WIDTH, dtype=np.float32)
            elapsed = ctypes.c_double()
            status = full(
                ffn.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                router.ctypes.data_as(ctypes.POINTER(ctypes.c_float)), ptrs,
                gates.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                output.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                args.threads, ctypes.byref(elapsed))
            if status:
                raise RuntimeError(f"baseline native function failed: {status}")
            _ = refs
            return output, (time.perf_counter() - started) * 1000, elapsed.value

        def overlapped(layer, route, gates, ffn, router):
            started = time.perf_counter()
            outputs = np.empty((4, WIDTH), dtype=np.float32)
            native_ms = 0.0
            with ThreadPoolExecutor(max_workers=4,
                                    thread_name_prefix="aion-overlap-read") as pool:
                futures = {
                    pool.submit(store._read_l2_into_slot, layer, expert, slot): slot
                    for slot, expert in enumerate(route)
                }
                for future in as_completed(futures):
                    slot = futures[future]
                    value = future.result()
                    if value is None:
                        store.sd_fallbacks += 1
                        value = GptOssExpertFrameStore._load_value(
                            store, layer, route[slot])
                        store._write_l2(layer, route[slot], value)
                    refs, ptrs = pointers(value)
                    elapsed = ctypes.c_double()
                    gate = np.asarray([gates[slot]], dtype=np.float32)
                    status = contribution(
                        router.ctypes.data_as(ctypes.POINTER(ctypes.c_float)), ptrs,
                        gate.ctypes.data_as(ctypes.POINTER(ctypes.c_float)), 1,
                        outputs[slot].ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                        args.threads, ctypes.byref(elapsed))
                    if status:
                        raise RuntimeError(
                            f"overlap contribution function failed: {status}")
                    native_ms += elapsed.value
                    _ = refs
            output = np.empty(WIDTH, dtype=np.float32)
            status = combine(
                ffn.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                outputs.ctypes.data_as(ctypes.POINTER(ctypes.c_float)), 1,
                output.ctypes.data_as(ctypes.POINTER(ctypes.c_float)))
            if status:
                raise RuntimeError(f"overlap combine failed: {status}")
            return output, (time.perf_counter() - started) * 1000, native_ms

        rows = []
        for capture_index, (path, metadata, ffn, router) in enumerate(captures):
            gates = np.asarray(metadata["gates"], dtype=np.float32)
            route = [int(value) for value in metadata["route"]]
            observations = {"baseline": [], "overlap": []}
            reference = None
            exact = True
            for repeat in range(args.repeats):
                order = ("baseline", "overlap") if (capture_index + repeat) % 2 == 0 \
                    else ("overlap", "baseline")
                for mode in order:
                    output, wall_ms, native_ms = (
                        baseline(metadata["layer"], route, gates, ffn, router)
                        if mode == "baseline" else
                        overlapped(metadata["layer"], route, gates, ffn, router))
                    digest = hashlib.sha256(output.tobytes()).hexdigest()
                    reference = digest if reference is None else reference
                    exact = exact and digest == reference
                    observations[mode].append({
                        "wall_ms": wall_ms, "native_ms": native_ms,
                        "output_sha256": digest,
                    })
            rows.append({
                "capture_path": str(path.resolve()),
                "capture_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "layer": metadata["layer"], "position": metadata["position"],
                "route": route, "all_outputs_bitwise_equal": exact,
                "baseline": observations["baseline"],
                "overlap": observations["overlap"],
            })

    baseline_ms = [item["wall_ms"] for row in rows for item in row["baseline"]]
    overlap_ms = [item["wall_ms"] for row in rows for item in row["overlap"]]
    exact = all(row["all_outputs_bitwise_equal"] for row in rows)
    speedup = statistics.median(baseline_ms) / statistics.median(overlap_ms)
    passed = exact and speedup >= 1.05
    report = {
        "schema": "aion.gptoss-120b-io-compute-overlap-layer-gate.v1",
        "status": "ADVANCE_IO_COMPUTE_OVERLAP" if passed else "STOP_IO_COMPUTE_OVERLAP",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": "GPT-OSS 120B Q4_K_M/MXFP4",
        "capture_count": len(rows), "repeats": args.repeats,
        "all_outputs_bitwise_equal": exact,
        "baseline": summary(baseline_ms), "overlap": summary(overlap_ms),
        "wall_speedup": speedup,
        "gate": {"minimum_wall_speedup": 1.05, "bitwise_output_required": True,
                 "passed": passed},
        "rows": rows, "store_metrics": store.metrics(),
        "claim_boundary": (
            "Real captured activations and exact internal-L2 expert frames over selected "
            "layers and positions. This measures within-layer read/compute overlap only; "
            "it is not complete generation or tokens-per-second evidence."),
    }
    body = json.dumps(report, sort_keys=True, separators=(",", ":"))
    report["canonical_sha256"] = hashlib.sha256(body.encode()).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: report[key] for key in (
        "status", "capture_count", "all_outputs_bitwise_equal",
        "wall_speedup", "canonical_sha256")}, sort_keys=True))


if __name__ == "__main__":
    main()
