#!/usr/bin/env python3
"""Test exact gate/up then down staging before implementing partial L2 reads."""

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
    GptOssExpertFrameStore,
    ctypes_component_pointer_array,
)


WIDTH = 2880


def summarize(values: list[float]) -> dict:
    ordered = sorted(values)
    return {
        "samples": len(values),
        "p50_ms": statistics.median(values),
        "p95_ms": ordered[int(0.95 * (len(ordered) - 1))],
        "mean_ms": statistics.mean(values),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--capture-dir", type=Path, required=True)
    parser.add_argument("--captures", type=int, default=8)
    parser.add_argument("--rounds", type=int, default=12)
    parser.add_argument("--threads", type=int, default=8)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("refusing to overwrite evidence")
    if args.captures < 1 or args.rounds < 2 or args.threads < 1:
        raise SystemExit("captures, rounds and threads must be positive")
    metadata_paths = sorted(args.capture_dir.glob("position-*-layer-*.json"))[:args.captures]
    if not metadata_paths:
        raise SystemExit("no captures found")

    native = Path(__file__).parents[1] / "modules/aion_inference/native"
    with tempfile.TemporaryDirectory(prefix="aion-gptoss-staged-projection-") as temporary:
        library_path = Path(temporary) / "moe.dylib"
        subprocess.run([
            "clang++", "-std=c++17", "-O3", "-dynamiclib", "-I/opt/homebrew/include",
            str(native / "gptoss_persistent_moe_library.cpp"),
            "-L/opt/homebrew/lib", "-lggml", "-lggml-base", "-ldl", "-o",
            str(library_path),
        ], check=True)
        library = ctypes.CDLL(str(library_path))
        whole = library.aion_gptoss_one_expert_contribution_batch
        whole.argtypes = [ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_void_p),
                          ctypes.POINTER(ctypes.c_float), ctypes.c_int,
                          ctypes.POINTER(ctypes.c_float), ctypes.c_int,
                          ctypes.POINTER(ctypes.c_double)]
        whole.restype = ctypes.c_int
        gate_up = library.aion_gptoss_expert_gate_up
        gate_up.argtypes = [ctypes.POINTER(ctypes.c_float),
                            ctypes.POINTER(ctypes.c_void_p),
                            ctypes.POINTER(ctypes.c_float), ctypes.c_int,
                            ctypes.POINTER(ctypes.c_double)]
        gate_up.restype = ctypes.c_int
        down = library.aion_gptoss_expert_down_contribution
        down.argtypes = [ctypes.POINTER(ctypes.c_float),
                         ctypes.POINTER(ctypes.c_void_p), ctypes.c_float,
                         ctypes.POINTER(ctypes.c_float), ctypes.c_int,
                         ctypes.POINTER(ctypes.c_double)]
        down.restype = ctypes.c_int

        store = GptOssExpertFrameStore(args.manifest, args.captures * 16 * 1024 ** 2)
        rows = []
        for capture_index, metadata_path in enumerate(metadata_paths):
            metadata = json.loads(metadata_path.read_text())
            stem = metadata_path.with_suffix("")
            router = np.fromfile(Path(str(stem) + "-router.bin"), dtype="<f4")
            expert = int(metadata["route"][0])
            gate_value = np.float32(metadata["gates"][0])
            value = store.get(int(metadata["layer"]), expert)
            blobs = [value[projection][kind] for projection in ("gate", "up", "down")
                     for kind in ("weight", "bias")]
            refs, pointers = ctypes_component_pointer_array(blobs)
            gate_up_refs, gate_up_pointers = ctypes_component_pointer_array(blobs[:4])
            down_refs, down_pointers = ctypes_component_pointer_array(blobs[4:])
            observations = {"whole": [], "staged": []}
            reference = None
            exact = True
            for round_index in range(args.rounds):
                order = ("whole", "staged") if (capture_index + round_index) % 2 == 0 \
                    else ("staged", "whole")
                for mode in order:
                    output = np.empty(WIDTH, dtype=np.float32)
                    started = time.perf_counter_ns()
                    if mode == "whole":
                        elapsed = ctypes.c_double()
                        gate_array = np.asarray([gate_value], dtype=np.float32)
                        status = whole(
                            router.ctypes.data_as(ctypes.POINTER(ctypes.c_float)), pointers,
                            gate_array.ctypes.data_as(ctypes.POINTER(ctypes.c_float)), 1,
                            output.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                            args.threads, ctypes.byref(elapsed))
                        native_ms = elapsed.value
                    else:
                        hidden = np.empty(WIDTH, dtype=np.float32)
                        first = ctypes.c_double()
                        status = gate_up(
                            router.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                            gate_up_pointers,
                            hidden.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                            args.threads, ctypes.byref(first))
                        second = ctypes.c_double()
                        if not status:
                            status = down(
                                hidden.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                                down_pointers, ctypes.c_float(gate_value),
                                output.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                                args.threads, ctypes.byref(second))
                        native_ms = first.value + second.value
                    if status:
                        raise RuntimeError(f"{mode} native status {status}")
                    wall_ms = (time.perf_counter_ns() - started) / 1_000_000
                    digest = hashlib.sha256(output.tobytes()).hexdigest()
                    reference = digest if reference is None else reference
                    exact = exact and digest == reference
                    observations[mode].append({
                        "wall_ms": wall_ms, "native_ms": native_ms,
                        "output_sha256": digest,
                    })
            _ = refs, gate_up_refs, down_refs
            rows.append({
                "capture_path": str(metadata_path.resolve()),
                "layer": int(metadata["layer"]), "expert": expert,
                "all_outputs_bitwise_equal": exact,
                "whole": observations["whole"], "staged": observations["staged"],
            })

    whole_ms = [sample["wall_ms"] for row in rows for sample in row["whole"]]
    staged_ms = [sample["wall_ms"] for row in rows for sample in row["staged"]]
    exact = all(row["all_outputs_bitwise_equal"] for row in rows)
    speedup = statistics.median(whole_ms) / statistics.median(staged_ms)
    passed = exact and speedup >= 0.90
    result = {
        "schema": "aion.gptoss-120b-staged-projection-compute-gate.v1",
        "status": "ADVANCE_PARTIAL_L2_READ_PROBE" if passed else "STOP_STAGED_PROJECTION",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": "GPT-OSS 120B Q4_K_M/MXFP4",
        "captures": len(rows), "rounds": args.rounds, "threads": args.threads,
        "all_outputs_bitwise_equal": exact,
        "whole": summarize(whole_ms), "staged": summarize(staged_ms),
        "resident_compute_speedup": speedup,
        "gate": {
            "bitwise_output_required": True,
            "minimum_resident_compute_ratio": 0.90,
            "passed": passed,
        },
        "rows": rows,
        "claim_boundary": (
            "Real captured activations and original packed weights. This tests whether the "
            "gate/up and down dependency split is bitwise exact and whether its resident "
            "orchestration overhead is below 10%. It contains no partial L2 I/O and is not "
            "tokens-per-second evidence."
        ),
    }
    result["canonical_sha256"] = hashlib.sha256(json.dumps(
        result, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: result[key] for key in (
        "status", "all_outputs_bitwise_equal", "resident_compute_speedup",
        "canonical_sha256")}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
