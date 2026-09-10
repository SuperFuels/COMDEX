#!/usr/bin/env python3
"""Compare one real four-expert GPT-OSS route on CPU and fused Metal graphs."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import tempfile
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
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("refusing to overwrite evidence")
    trace = json.loads(args.trace.read_text())
    layer = trace["run_a"]["tokens"][args.position]["layers"][args.layer]
    route = layer["route"]
    gates = layer["gates"]
    store = GptOssExpertFrameStore(args.manifest, 64 * 1024 * 1024)
    values = store.get_layer_route_parallel(args.layer, route, workers=4)
    native = Path(__file__).parents[1] / "modules/aion_inference/native"
    with tempfile.TemporaryDirectory(prefix="aion-gptoss-fused-metal-route-") as temporary:
        root = Path(temporary)
        cpu_executable = root / "cpu"
        metal_executable = root / "metal"
        compile_prefix = ["clang++", "-std=c++17", "-O3", "-I/opt/homebrew/include"]
        libraries = ["-L/opt/homebrew/lib", "-lggml", "-lggml-base", "-ldl"]
        subprocess.run([*compile_prefix, str(native / "gptoss_packed_route_cpu_gate.cpp"),
                        *libraries, "-o", str(cpu_executable)], check=True)
        subprocess.run([*compile_prefix, str(native / "gptoss_fused_route_metal_probe.cpp"),
                        *libraries, "-o", str(metal_executable)], check=True)
        for position, value in enumerate(values):
            for projection in ("gate", "up", "down"):
                for kind in ("weight", "bias"):
                    (root / f"{position}-{projection}-{kind}.bin").write_bytes(
                        value[projection][kind]
                    )
        gate_text = ",".join(f"{value:.9g}" for value in gates)
        cpu_output = root / "cpu-output.bin"
        metal_output = root / "metal-output.bin"
        cpu = json.loads(subprocess.check_output([
            str(cpu_executable), str(root), ",".join(map(str, route)), gate_text,
            "10", str(args.threads),
        ], env={**os.environ, "AION_OUTPUT_PATH": str(cpu_output)}, text=True))
        metal = json.loads(subprocess.check_output([
            str(metal_executable), str(root), gate_text, str(metal_output),
        ], text=True))
        reference = np.fromfile(cpu_output, dtype="<f4").astype(np.float64)
        candidate = np.fromfile(metal_output, dtype="<f4").astype(np.float64)
    delta = reference - candidate
    relative_l2 = float(np.linalg.norm(delta) / np.linalg.norm(reference))
    max_abs = float(np.abs(delta).max())
    speedup = cpu["p50_ms"] / metal["warm_p50_ms"]
    promoted = speedup >= 1.15 and relative_l2 <= 0.01
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
        "cpu": cpu,
        "fused_metal": metal,
        "metal_speedup": speedup,
        "relative_l2_error": relative_l2,
        "max_abs_error": max_abs,
        "argmax_equal": int(reference.argmax()) == int(candidate.argmax()),
        "outputs_bitwise_equal": bool(np.array_equal(reference, candidate)),
        "promotion_gates": {"speedup_at_least": 1.15, "relative_l2_at_most": 0.01},
        "claim_boundary": (
            "One real four-expert layer route from a frozen GPT-OSS 120B trace was "
            "calculated as one Metal graph. This is a changed-arithmetic microgate, not "
            "a full token, semantic-quality result, or generated tokens-per-second claim."
        ),
    }
    result["canonical_sha256"] = hashlib.sha256(json.dumps(
        result, sort_keys=True, separators=(",", ":"),
    ).encode()).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: result[key] for key in (
        "status", "metal_speedup", "relative_l2_error", "max_abs_error",
        "argmax_equal", "outputs_bitwise_equal", "canonical_sha256",
    )}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
