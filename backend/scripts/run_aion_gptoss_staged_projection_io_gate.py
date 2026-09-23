#!/usr/bin/env python3
"""ABBA-test whole-expert overlap against dependency-staged exact L2 reads."""

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
    GptOssReusableArenaPersistentL2ExpertFrameStore,
    ctypes_component_pointer_array,
)


WIDTH = 2880


def summary(values: list[float]) -> dict:
    ordered = sorted(values)
    return {"samples": len(values), "p50_ms": statistics.median(values),
            "p95_ms": ordered[int(.95 * (len(ordered) - 1))],
            "mean_ms": statistics.mean(values)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--capture-dir", type=Path, required=True)
    parser.add_argument("--l2-root", type=Path, required=True)
    parser.add_argument("--l2-gib", type=float, default=20.0)
    parser.add_argument("--captures", type=int, default=8)
    parser.add_argument("--rounds", type=int, default=6)
    parser.add_argument("--threads", type=int, default=8)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("refusing to overwrite evidence")
    paths = sorted(args.capture_dir.glob("position-*-layer-*.json"))[:args.captures]
    if not paths or args.rounds < 2:
        raise SystemExit("captures and at least two rounds are required")

    native = Path(__file__).parents[1] / "modules/aion_inference/native"
    with tempfile.TemporaryDirectory(prefix="aion-gptoss-staged-io-") as temporary:
        library_path = Path(temporary) / "moe.dylib"
        subprocess.run(["clang++", "-std=c++17", "-O3", "-dynamiclib",
                        "-I/opt/homebrew/include", str(native / "gptoss_persistent_moe_library.cpp"),
                        "-L/opt/homebrew/lib", "-lggml", "-lggml-base", "-ldl",
                        "-o", str(library_path)], check=True)
        library = ctypes.CDLL(str(library_path))
        whole = library.aion_gptoss_one_expert_contribution_batch
        whole.argtypes = [ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_void_p),
                          ctypes.POINTER(ctypes.c_float), ctypes.c_int,
                          ctypes.POINTER(ctypes.c_float), ctypes.c_int,
                          ctypes.POINTER(ctypes.c_double)]
        whole.restype = ctypes.c_int
        gate_up = library.aion_gptoss_expert_gate_up
        gate_up.argtypes = [ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_void_p),
                            ctypes.POINTER(ctypes.c_float), ctypes.c_int,
                            ctypes.POINTER(ctypes.c_double)]
        gate_up.restype = ctypes.c_int
        down = library.aion_gptoss_expert_down_contribution
        down.argtypes = [ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_void_p),
                         ctypes.c_float, ctypes.POINTER(ctypes.c_float), ctypes.c_int,
                         ctypes.POINTER(ctypes.c_double)]
        down.restype = ctypes.c_int
        store = GptOssReusableArenaPersistentL2ExpertFrameStore(
            args.manifest, 0, args.l2_root, int(args.l2_gib * 1024 ** 3))

        def whole_mode(layer, route, gates, router):
            outputs = np.empty((4, WIDTH), dtype=np.float32)
            started = time.perf_counter_ns()
            with ThreadPoolExecutor(max_workers=4) as pool:
                futures = {pool.submit(store._read_l2_into_slot, layer, expert, slot): slot
                           for slot, expert in enumerate(route)}
                for future in as_completed(futures):
                    slot = futures[future]
                    value = future.result()
                    if value is None:
                        raise RuntimeError("whole L2 frame missing")
                    refs, pointers = ctypes_component_pointer_array([
                        value[projection][kind] for projection in ("gate", "up", "down")
                        for kind in ("weight", "bias")])
                    gate = np.asarray([gates[slot]], dtype=np.float32)
                    elapsed = ctypes.c_double()
                    status = whole(router.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                                   pointers, gate.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                                   1, outputs[slot].ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                                   args.threads, ctypes.byref(elapsed))
                    if status:
                        raise RuntimeError(f"whole contribution failed: {status}")
                    _ = refs
            return outputs, (time.perf_counter_ns() - started) / 1_000_000

        def staged_mode(layer, route, gates, router):
            outputs = np.empty((4, WIDTH), dtype=np.float32)
            started = time.perf_counter_ns()
            with ThreadPoolExecutor(max_workers=8) as pool:
                first_futures = {
                    pool.submit(store.read_verified_l2_component_group_into_slot,
                                layer, expert, slot, (0, 1, 2, 3)): slot
                    for slot, expert in enumerate(route)}
                for first_future in as_completed(first_futures):
                    slot = first_futures[first_future]
                    first = first_future.result()
                    second_future = pool.submit(
                        store.read_verified_l2_component_group_into_slot,
                        layer, route[slot], slot, (4, 5))
                    first_refs, first_pointers = ctypes_component_pointer_array([
                        first[projection][kind] for projection in ("gate", "up")
                        for kind in ("weight", "bias")])
                    hidden = np.empty(WIDTH, dtype=np.float32)
                    elapsed = ctypes.c_double()
                    status = gate_up(
                        router.ctypes.data_as(ctypes.POINTER(ctypes.c_float)), first_pointers,
                        hidden.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                        args.threads, ctypes.byref(elapsed))
                    if status:
                        raise RuntimeError(f"gate/up failed: {status}")
                    second = second_future.result()
                    second_refs, second_pointers = ctypes_component_pointer_array([
                        second["down"][kind] for kind in ("weight", "bias")])
                    status = down(
                        hidden.ctypes.data_as(ctypes.POINTER(ctypes.c_float)), second_pointers,
                        ctypes.c_float(gates[slot]),
                        outputs[slot].ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                        args.threads, ctypes.byref(elapsed))
                    if status:
                        raise RuntimeError(f"down contribution failed: {status}")
                    _ = first_refs, second_refs
            return outputs, (time.perf_counter_ns() - started) / 1_000_000

        rows = []
        for capture_index, path in enumerate(paths):
            metadata = json.loads(path.read_text())
            stem = path.with_suffix("")
            router = np.fromfile(Path(str(stem) + "-router.bin"), dtype="<f4")
            layer = int(metadata["layer"])
            route = [int(expert) for expert in metadata["route"]]
            gates = np.asarray(metadata["gates"], dtype=np.float32)
            # Establish the same process-verification epoch required by the
            # production reusable arena before any partial read is permitted.
            for slot, expert in enumerate(route):
                if store._read_l2_into_slot(layer, expert, slot) is None:
                    store._load_value(layer, expert)
                    if store._read_l2_into_slot(layer, expert, slot) is None:
                        raise RuntimeError("verification warm-up L2 refill failed")
            observations = {"whole": [], "staged": []}
            reference = None
            exact = True
            for round_index in range(args.rounds):
                order = ("whole", "staged") if (capture_index + round_index) % 2 == 0 \
                    else ("staged", "whole")
                for mode in order:
                    output, wall_ms = (whole_mode(layer, route, gates, router)
                                       if mode == "whole" else
                                       staged_mode(layer, route, gates, router))
                    digest = hashlib.sha256(output.tobytes()).hexdigest()
                    reference = digest if reference is None else reference
                    exact = exact and digest == reference
                    observations[mode].append({"wall_ms": wall_ms,
                                                "output_sha256": digest})
            rows.append({"capture_path": str(path.resolve()), "layer": layer,
                         "route": route, "all_outputs_bitwise_equal": exact,
                         **observations})

    whole_ms = [sample["wall_ms"] for row in rows for sample in row["whole"]]
    staged_ms = [sample["wall_ms"] for row in rows for sample in row["staged"]]
    exact = all(row["all_outputs_bitwise_equal"] for row in rows)
    speedup = statistics.median(whole_ms) / statistics.median(staged_ms)
    passed = exact and speedup >= 1.05
    result = {
        "schema": "aion.gptoss-120b-staged-projection-io-gate.v1",
        "status": "ADVANCE_STAGED_PROJECTION_IO" if passed else "STOP_STAGED_PROJECTION_IO",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": "GPT-OSS 120B Q4_K_M/MXFP4", "captures": len(rows),
        "rounds": args.rounds, "threads": args.threads,
        "all_outputs_bitwise_equal": exact, "whole": summary(whole_ms),
        "staged": summary(staged_ms), "wall_speedup": speedup,
        "gate": {"minimum_wall_speedup": 1.05, "bitwise_output_required": True,
                 "passed": passed},
        "rows": rows, "store_metrics": store.metrics(),
        "claim_boundary": (
            "Real captured activations and process-verified internal-L2 frames. Gate/up "
            "components are read first; the down read overlaps exact gate/up arithmetic. "
            "This is a selected layer microgate, not full-generation evidence."),
    }
    result["canonical_sha256"] = hashlib.sha256(json.dumps(
        result, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: result[key] for key in (
        "status", "all_outputs_bitwise_equal", "wall_speedup", "canonical_sha256")},
        sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
