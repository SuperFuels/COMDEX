#!/usr/bin/env python3
"""Compare one real four-expert GPT-OSS route on CPU and fused Metal graphs."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
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
    parser.add_argument("--position", type=int, default=0)
    parser.add_argument("--layer", type=int, default=0)
    parser.add_argument("--threads", type=int, default=6)
    parser.add_argument("--resident-pool", type=Path)
    parser.add_argument("--resident-pool-gib", type=float, default=8.0)
    parser.add_argument("--activation-capture", type=Path)
    parser.add_argument("--cpu-cache-thrash-mib", type=int, default=0)
    parser.add_argument("--zero-copy-host", action="store_true")
    parser.add_argument("--batched-cpu", action="store_true")
    parser.add_argument("--batched-cpu-mmap", action="store_true")
    parser.add_argument("--batched-cpu-repack", action="store_true")
    parser.add_argument("--batched-cpu-indirect", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("refusing to overwrite evidence")
    trace = json.loads(args.trace.read_text())
    layer = trace["run_a"]["tokens"][args.position]["layers"][args.layer]
    activation_path = None
    if args.activation_capture:
        capture = json.loads(args.activation_capture.read_text())
        if capture["position"] != args.position or capture["layer"] != args.layer:
            raise SystemExit("activation capture position/layer does not match")
        layer = capture
        activation_path = args.activation_capture.with_suffix("")
        activation_path = Path(str(activation_path) + "-router.bin")
    route = layer["route"]
    gates = layer["gates"]
    capacity = int(args.resident_pool_gib * 1024 ** 3) if args.resident_pool else 64 * 1024 * 1024
    store = GptOssExpertFrameStore(args.manifest, capacity)
    pool_preload_seconds = 0.0
    if args.resident_pool:
        pool = json.loads(args.resident_pool.read_text())
        started = time.perf_counter()
        for pool_layer in range(36):
            store.get_layer_route_parallel(pool_layer, pool["layers"][str(pool_layer)], workers=4)
        store.protect(pool["layers"])
        pool_preload_seconds = time.perf_counter() - started
    values = store.get_layer_route_parallel(args.layer, route, workers=4)
    native = Path(__file__).parents[1] / "modules/aion_inference/native"
    with tempfile.TemporaryDirectory(prefix="aion-gptoss-fused-metal-route-") as temporary:
        root = Path(temporary)
        cpu_executable = root / "cpu"
        metal_executable = root / "metal"
        batched_executable = root / "batched"
        compile_prefix = ["clang++", "-std=c++17", "-O3", "-I/opt/homebrew/include"]
        libraries = ["-L/opt/homebrew/lib", "-lggml", "-lggml-base", "-ldl"]
        subprocess.run([*compile_prefix, str(native / "gptoss_packed_route_cpu_gate.cpp"),
                        *libraries, "-o", str(cpu_executable)], check=True)
        subprocess.run([*compile_prefix, str(native / "gptoss_fused_route_metal_probe.cpp"),
                        *libraries, "-o", str(metal_executable)], check=True)
        if args.batched_cpu:
            subprocess.run([*compile_prefix, str(native / "gptoss_batched_route_cpu_gate.cpp"),
                            *libraries, "-o", str(batched_executable)], check=True)
        for position, value in enumerate(values):
            for projection in ("gate", "up", "down"):
                for kind in ("weight", "bias"):
                    (root / f"{position}-{projection}-{kind}.bin").write_bytes(
                        value[projection][kind]
                    )
        gate_text = ",".join(f"{value:.9g}" for value in gates)
        cpu_output = root / "cpu-output.bin"
        metal_output = root / "metal-output.bin"
        child_env = dict(os.environ)
        if activation_path:
            child_env["AION_INPUT_PATH"] = str(activation_path.resolve())
        if args.cpu_cache_thrash_mib:
            child_env["AION_CPU_CACHE_THRASH_MIB"] = str(args.cpu_cache_thrash_mib)
        if args.zero_copy_host:
            child_env["AION_ZERO_COPY_HOST"] = "1"
        cpu = json.loads(subprocess.check_output([
            str(cpu_executable), str(root), ",".join(map(str, route)), gate_text,
            "10", str(args.threads),
        ], env={**child_env, "AION_OUTPUT_PATH": str(cpu_output)}, text=True))
        metal = json.loads(subprocess.check_output([
            str(metal_executable), str(root), gate_text, str(metal_output),
        ], env=child_env, text=True))
        batched = None
        batched_output = root / "batched-output.bin"
        if args.batched_cpu:
            batched_env = {**child_env, "AION_OUTPUT_PATH": str(batched_output)}
            if args.batched_cpu_mmap:
                batched_env["AION_MMAP_COMPONENTS"] = "1"
            if args.batched_cpu_repack:
                batched_env["AION_REPACK_COMPONENTS"] = "1"
            if args.batched_cpu_indirect:
                batched_env["AION_MUL_MAT_ID"] = "1"
            batched = json.loads(subprocess.check_output([
                str(batched_executable), str(root), gate_text, "10", str(args.threads),
            ], env=batched_env, text=True))
        reference = np.fromfile(cpu_output, dtype="<f4").astype(np.float64)
        candidate = np.fromfile(metal_output, dtype="<f4").astype(np.float64)
        batched_candidate = (np.fromfile(batched_output, dtype="<f4").astype(np.float64)
                             if args.batched_cpu else None)
    delta = reference - candidate
    relative_l2 = float(np.linalg.norm(delta) / np.linalg.norm(reference))
    max_abs = float(np.abs(delta).max())
    metal_charged_ms = metal["warm_p50_ms"] + (
        metal["upload_ms"] if args.cpu_cache_thrash_mib and not args.zero_copy_host else 0.0
    )
    speedup = cpu["p50_ms"] / metal_charged_ms
    promoted = speedup >= 1.15 and relative_l2 <= 0.01
    batched_relative_l2 = (
        float(np.linalg.norm(reference - batched_candidate) / np.linalg.norm(reference))
        if batched_candidate is not None else None)
    batched_argmax_equal = (
        int(reference.argmax()) == int(batched_candidate.argmax())
        if batched_candidate is not None else None)
    batched_speedup = (cpu["p50_ms"] / batched["p50_ms"]
                       if batched is not None else None)
    batched_advanced = bool(
        batched is not None and args.batched_cpu_indirect and args.batched_cpu_mmap
        and batched_speedup >= 1.15 and batched_relative_l2 <= 1e-6
        and batched_argmax_equal)
    result = {
        "schema": "aion.gptoss-120b-fused-four-expert-metal-gate.v1",
        "status": "ADVANCE_FUSED_METAL_ROUTE" if promoted else "NOT_PROMOTED",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": "GPT-OSS 120B Q4_K_M/MXFP4",
        "trace_path": str(args.trace.resolve()),
        "trace_file_sha256": hashlib.sha256(args.trace.read_bytes()).hexdigest(),
        "position": args.position,
        "layer": args.layer,
        "route": route,
        "normalized_gates": gates,
        "warehouse_metrics": store.metrics(),
        "resident_pool_path": str(args.resident_pool.resolve()) if args.resident_pool else None,
        "resident_pool_preload_seconds": pool_preload_seconds,
        "activation_capture_path": str(args.activation_capture.resolve()) if args.activation_capture else None,
        "activation_capture_sha256": hashlib.sha256(args.activation_capture.read_bytes()).hexdigest() if args.activation_capture else None,
        "cpu": cpu,
        "fused_metal": metal,
        "batched_cpu": batched,
        "metal_speedup": speedup,
        "metal_charged_route_ms": metal_charged_ms,
        "relative_l2_error": relative_l2,
        "max_abs_error": max_abs,
        "argmax_equal": int(reference.argmax()) == int(candidate.argmax()),
        "outputs_bitwise_equal": bool(np.array_equal(reference, candidate)),
        "batched_cpu_status": ("ADVANCE_MAPPED_INDIRECT_ROUTE" if batched_advanced
                               else "NOT_PROMOTED" if batched is not None else None),
        "batched_cpu_speedup": batched_speedup,
        "batched_cpu_relative_l2_error": batched_relative_l2,
        "batched_cpu_argmax_equal": batched_argmax_equal,
        "batched_cpu_outputs_bitwise_equal": (
            bool(np.array_equal(reference, batched_candidate))
            if batched_candidate is not None else None),
        "promotion_gates": {"metal_speedup_at_least": 1.15,
                            "metal_relative_l2_at_most": 0.01,
                            "mapped_indirect_speedup_at_least": 1.15,
                            "mapped_indirect_relative_l2_at_most": 1e-6,
                            "mapped_indirect_argmax_equal": True},
        "claim_boundary": (
            "One real four-expert layer route from a frozen GPT-OSS 120B trace was "
            "calculated as one Metal graph under the recorded parent-process resident-pool pressure. "
            + (
                "The CPU cache-thrash buffer is a synthetic cold-cache diagnostic; its touch time "
                "is excluded, while the Metal comparison charges route upload plus warm compute. "
                if args.cpu_cache_thrash_mib else ""
            )
            + (
                "The zero-copy candidate binds a page-aligned host arena through the Metal backend; "
                "its separately recorded host packing time is excluded from the compute comparison. "
                if args.zero_copy_host else ""
            )
            + (
                "The mapped indirect CPU candidate virtually concatenates the four independently "
                "stored expert projections and uses GGML indirect matrix multiplication without "
                "copying their 52.9 MB route into a charged arena. It changes floating-point "
                "reduction order and therefore belongs to the quality track unless bitwise equality "
                "is separately recovered. " if args.batched_cpu_indirect else ""
            )
            + "This is a changed-arithmetic microgate, not a full token, semantic-quality result, "
            "or generated tokens-per-second claim."
        ),
    }
    result["canonical_sha256"] = hashlib.sha256(json.dumps(
        result, sort_keys=True, separators=(",", ":"),
    ).encode()).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: result[key] for key in (
        "status", "metal_speedup", "relative_l2_error", "max_abs_error",
        "argmax_equal", "outputs_bitwise_equal", "batched_cpu_status",
        "batched_cpu_speedup", "batched_cpu_relative_l2_error", "canonical_sha256",
    )}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
