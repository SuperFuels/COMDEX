#!/usr/bin/env python3
"""Compare serial and rotating two-lane exact expert calculation on real routes."""
from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import statistics
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from backend.modules.aion_inference.gptoss_expert_frame_store import (
    GptOssExpertFrameStore, ctypes_component_pointer_array,
)
from backend.scripts.run_aion_expert_function_atlas_gate import digest


WIDTH = 2880


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--captures", type=Path, required=True)
    parser.add_argument("--layer", type=int, default=12)
    parser.add_argument("--threads", type=int, default=6)
    parser.add_argument("--routes", type=int, default=16)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("refusing to overwrite evidence")
    metadata_paths = sorted(
        args.captures.glob(f"position-*-layer-{args.layer}.json"),
        key=lambda path: int(path.name.split("-")[1]),
    )[-args.routes:]
    if len(metadata_paths) != args.routes:
        raise SystemExit("insufficient captured routes")

    source = (Path(__file__).parents[1] /
              "modules/aion_inference/native/gptoss_persistent_moe_library.cpp")
    store = GptOssExpertFrameStore(args.manifest, 512 * 1024 * 1024)
    observations = []
    with tempfile.TemporaryDirectory(prefix="aion-pairwise-experts-") as temporary:
        library_path = Path(temporary) / "moe.dylib"
        subprocess.run([
            "clang++", "-std=c++17", "-O3", "-dynamiclib",
            "-I/opt/homebrew/include", str(source), "-L/opt/homebrew/lib",
            "-lggml", "-lggml-base", "-ldl", "-o", str(library_path),
        ], check=True)
        library = ctypes.CDLL(str(library_path))
        signature = [
            ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_float),
            ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(ctypes.c_float),
            ctypes.POINTER(ctypes.c_float), ctypes.c_int,
            ctypes.POINTER(ctypes.c_double),
        ]
        serial = library.aion_gptoss_moe_finish
        pairwise = library.aion_gptoss_moe_finish_pairwise
        serial.argtypes = signature
        pairwise.argtypes = signature
        serial.restype = ctypes.c_int
        pairwise.restype = ctypes.c_int

        def calculate(function, ffn, router, pointers, gates):
            output = np.empty(WIDTH, dtype=np.float32)
            elapsed = ctypes.c_double()
            status = function(
                ffn.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                router.ctypes.data_as(ctypes.POINTER(ctypes.c_float)), pointers,
                gates.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                output.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                args.threads, ctypes.byref(elapsed),
            )
            if status:
                raise RuntimeError(f"native MoE status {status}")
            return output, elapsed.value

        for metadata_path in metadata_paths:
            metadata = json.loads(metadata_path.read_text())
            stem = metadata_path.with_suffix("")
            ffn_path = Path(str(stem) + "-ffn.bin")
            router_path = Path(str(stem) + "-router.bin")
            if digest(ffn_path) != metadata["ffn_sha256"]:
                raise SystemExit(f"capture hash mismatch: {ffn_path}")
            if digest(router_path) != metadata["router_sha256"]:
                raise SystemExit(f"capture hash mismatch: {router_path}")
            ffn = np.fromfile(ffn_path, dtype="<f4")
            router = np.fromfile(router_path, dtype="<f4")
            gates = np.asarray(metadata["gates"], dtype=np.float32)
            experts = store.get_layer_route_parallel(
                args.layer, metadata["route"], workers=4,
            )
            blobs = [expert[projection][kind] for expert in experts
                     for projection in ("gate", "up", "down")
                     for kind in ("weight", "bias")]
            references, pointers = ctypes_component_pointer_array(blobs)
            # Both implementations must enter the measured ABBA sequence with
            # their graphs initialized and all selected weight pages touched.
            # Otherwise the first serial observation pays lazy page faults and
            # the following pairwise observations inherit artificially warm
            # pages, which is not a resident-calculation comparison.
            calculate(serial, ffn, router, pointers, gates)
            calculate(pairwise, ffn, router, pointers, gates)
            timings = {"serial": [], "pairwise": []}
            reference = None
            all_equal = True
            for name, function in (("serial", serial), ("pairwise", pairwise),
                                   ("pairwise", pairwise), ("serial", serial)):
                output, elapsed = calculate(function, ffn, router, pointers, gates)
                timings[name].append(elapsed)
                if reference is None:
                    reference = output.copy()
                else:
                    all_equal = all_equal and np.array_equal(reference, output)
            observations.append({
                "capture": metadata_path.name, "position": metadata["position"],
                "route": metadata["route"], "all_outputs_bitwise_equal": all_equal,
                "serial_ms": statistics.median(timings["serial"]),
                "pairwise_ms": statistics.median(timings["pairwise"]),
                "speedup": (statistics.median(timings["serial"]) /
                            statistics.median(timings["pairwise"])),
            })
            _ = references

    speedups = [item["speedup"] for item in observations]
    passed = (all(item["all_outputs_bitwise_equal"] for item in observations)
              and statistics.median(speedups) >= 1.05
              and sum(value > 1.0 for value in speedups) >= len(speedups) * 0.75)
    report = {
        "schema": "aion.gptoss-120b-pairwise-rotating-expert-gate.v1",
        "status": "ADVANCE_PAIRWISE_ROTATION" if passed
                  else "STOP_PAIRWISE_ROTATION",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "quality_track": False, "layer": args.layer, "threads": args.threads,
        "routes": len(observations), "observations": observations,
        "unmeasured_dual_implementation_warmup_per_route": True,
        "all_outputs_bitwise_equal": all(
            item["all_outputs_bitwise_equal"] for item in observations),
        "median_speedup": statistics.median(speedups),
        "p95_speedup": float(np.percentile(speedups, 95)),
        "routes_faster": sum(value > 1.0 for value in speedups),
        "promotion_gate": {"minimum_median_speedup": 1.05,
                           "minimum_fraction_routes_faster": 0.75,
                           "bitwise_output_equivalence": True},
        "warehouse_manifest_sha256": digest(args.manifest),
        "claim_boundary": (
            "Real resident route microgate. Both implementations and all selected weight "
            "pages are warmed before the measured ABBA sequence. Pairwise rotation "
            "calculates two original experts concurrently and then the next pair. It "
            "excludes SD/L2 delivery, attention and output projection, so it is not "
            "generated-token speed."
        ),
    }
    report["canonical_sha256"] = hashlib.sha256(json.dumps(
        report, sort_keys=True, separators=(",", ":"),
    ).encode()).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "status": report["status"], "median_speedup": report["median_speedup"],
        "routes_faster": report["routes_faster"],
        "all_outputs_bitwise_equal": report["all_outputs_bitwise_equal"],
        "canonical_sha256": report["canonical_sha256"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
