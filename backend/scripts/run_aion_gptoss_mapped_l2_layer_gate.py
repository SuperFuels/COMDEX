#!/usr/bin/env python3
"""ABBA-test copied versus directly mapped L2 frames on one real 120B route."""

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

from backend.modules.aion_inference.gptoss_expert_frame_store import (
    ctypes_component_pointer_array,
    GptOssMappedPersistentL2ExpertFrameStore,
    GptOssPinnedVerifiedPersistentL2ExpertFrameStore,
    GptOssPersistentL2ExpertFrameStore,
    GptOssReusableArenaPersistentL2ExpertFrameStore,
)


WIDTH = 2880


def p95(values: list[float]) -> float:
    return sorted(values)[int(0.95 * (len(values) - 1))]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--l2-root", type=Path, required=True)
    parser.add_argument("--l2-capacity-gib", type=float, required=True)
    parser.add_argument("--trace", type=Path, required=True)
    parser.add_argument("--position", type=int, default=7)
    parser.add_argument("--layer", type=int, default=0)
    parser.add_argument("--threads", type=int, default=6)
    parser.add_argument("--rounds", type=int, default=12)
    parser.add_argument("--candidate", choices=("mapped", "pinned_verified", "reusable_arena"),
                        default="mapped")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("refusing to overwrite evidence")
    trace = json.loads(args.trace.read_text())
    observation = trace["run_a"]["tokens"][args.position]["layers"][args.layer]
    if observation["layer"] != args.layer:
        raise RuntimeError("trace layer index mismatch")
    route = observation["route"]
    gates = np.asarray(observation["gates"], dtype=np.float32)
    capacity = int(args.l2_capacity_gib * 1024 * 1024 * 1024)
    candidate_type = ({
        "mapped": GptOssMappedPersistentL2ExpertFrameStore,
        "pinned_verified": GptOssPinnedVerifiedPersistentL2ExpertFrameStore,
        "reusable_arena": GptOssReusableArenaPersistentL2ExpertFrameStore,
    }[args.candidate])
    stores = {
        "copied": GptOssPersistentL2ExpertFrameStore(
            args.manifest, 0, args.l2_root, capacity),
        "candidate": candidate_type(
            args.manifest, 0, args.l2_root, capacity),
    }
    ffn = np.cos(np.arange(WIDTH, dtype=np.float32) * np.float32(0.002))
    router = np.sin(np.arange(WIDTH, dtype=np.float32) * np.float32(0.00390625))
    native = (Path(__file__).parents[1]
              / "modules/aion_inference/native/gptoss_persistent_moe_library.cpp")
    samples = {name: [] for name in stores}
    outputs = {name: [] for name in stores}
    first_mapped_verification = None
    with tempfile.TemporaryDirectory(prefix="aion-gptoss-mapped-l2-") as temporary:
        library_path = Path(temporary) / "moe.dylib"
        subprocess.run([
            "clang++", "-std=c++17", "-O3", "-dynamiclib", "-I/opt/homebrew/include",
            str(native), "-L/opt/homebrew/lib", "-lggml", "-lggml-base", "-ldl",
            "-o", str(library_path),
        ], check=True)
        loaded = ctypes.CDLL(str(library_path))
        function = loaded.aion_gptoss_moe_finish
        function.argtypes = [
            ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_float),
            ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(ctypes.c_float),
            ctypes.POINTER(ctypes.c_float), ctypes.c_int,
            ctypes.POINTER(ctypes.c_double),
        ]
        function.restype = ctypes.c_int

        def evaluate(name: str) -> tuple[dict[str, float], bytes]:
            started = time.perf_counter_ns()
            load_started = time.perf_counter_ns()
            values = stores[name].get_layer_route_parallel(args.layer, route, workers=4)
            load_ms = (time.perf_counter_ns() - load_started) / 1_000_000
            pointer_started = time.perf_counter_ns()
            blobs = [value[projection][kind] for value in values
                     for projection in ("gate", "up", "down")
                     for kind in ("weight", "bias")]
            references, pointers = ctypes_component_pointer_array(blobs)
            pointer_ms = (time.perf_counter_ns() - pointer_started) / 1_000_000
            output = np.empty(WIDTH, dtype=np.float32)
            native_ms = ctypes.c_double()
            status = function(
                ffn.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                router.ctypes.data_as(ctypes.POINTER(ctypes.c_float)), pointers,
                gates.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                output.ctypes.data_as(ctypes.POINTER(ctypes.c_float)), args.threads,
                ctypes.byref(native_ms),
            )
            total_ms = (time.perf_counter_ns() - started) / 1_000_000
            if status:
                raise RuntimeError(f"{name} native status {status}")
            result = output.tobytes()
            del pointers, references, blobs, values
            return {"total_ms": total_ms, "load_ms": load_ms,
                    "pointer_ms": pointer_ms, "native_ms": native_ms.value}, result

        # Disclose the mapped representation's one-time in-process verification
        # separately. Timed ABBA rounds compare the stable repeated access path.
        first_sample, first_output = evaluate("candidate")
        first_mapped_verification = {
            **first_sample, "output_sha256": hashlib.sha256(first_output).hexdigest(),
            "metrics_after": stores["candidate"].metrics(),
        }
        copied_warmup, copied_output = evaluate("copied")
        if copied_output != first_output:
            raise RuntimeError("mapped first verification changed expert output")

        order = ("copied", "candidate", "candidate", "copied")
        for _ in range(args.rounds):
            for name in order:
                sample, output = evaluate(name)
                samples[name].append(sample)
                outputs[name].append(output)

    summaries = {}
    for name, values in samples.items():
        summaries[name] = {}
        for metric in ("total_ms", "load_ms", "pointer_ms", "native_ms"):
            metric_values = [value[metric] for value in values]
            summaries[name][f"{metric}_p50"] = statistics.median(metric_values)
            summaries[name][f"{metric}_p95"] = p95(metric_values)
    all_outputs = outputs["copied"] + outputs["candidate"] + [first_output, copied_output]
    exact = len(set(all_outputs)) == 1
    speedup = summaries["copied"]["total_ms_p50"] / summaries["candidate"]["total_ms_p50"]
    candidate_metrics = stores["candidate"].metrics()
    result = {
        "schema": "aion.gptoss-120b-l2-access-real-layer-gate.v2",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": "GPT-OSS 120B Q4_K_M/MXFP4",
        "trace_path": str(args.trace.resolve()),
        "trace_file_sha256": hashlib.sha256(args.trace.read_bytes()).hexdigest(),
        "position": args.position,
        "layer": args.layer,
        "route": route,
        "gates": observation["gates"],
        "threads": args.threads,
        "rounds": args.rounds,
        "candidate": args.candidate,
        "abba_order": ["copied", "candidate", "candidate", "copied"],
        "first_mapped_verification": first_mapped_verification,
        "copied_warmup": copied_warmup,
        "summaries": summaries,
        "candidate_over_copied_wall_speedup": speedup,
        "all_outputs_bitwise_equal": exact,
        "copied_metrics": stores["copied"].metrics(),
        "candidate_metrics": candidate_metrics,
        "promotion_gate": {
            "minimum_complete_layer_speedup": 1.20,
            "requires_bitwise_output_equality": True,
            "requires_zero_candidate_sd_fallbacks": True,
        },
        "status": (
            "ADVANCE_CANDIDATE_L2_FULL_MODEL"
            if exact and speedup >= 1.20 and candidate_metrics["sd_fallbacks"] == 0
            else "NOT_PROMOTED"
        ),
        "claim_boundary": (
            "One exact four-expert route from a real 120B trace was evaluated through the "
            "same native packed MXFP4 calculation. The candidate uses a declared process-lifetime "
            "verification epoch; every new process revalidates all six component hashes. This is a real "
            "layer-route gate, not full-token or sustained-generation evidence."
        ),
    }
    result["canonical_sha256"] = hashlib.sha256(json.dumps(
        result, sort_keys=True, separators=(",", ":"),
    ).encode()).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: result[key] for key in (
        "status", "candidate_over_copied_wall_speedup", "all_outputs_bitwise_equal",
        "summaries", "canonical_sha256",
    )}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
