#!/usr/bin/env python3
"""Gate a direct split-stream MXFP4 Metal four-expert route."""
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
    parser.add_argument("--capture", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--threads", type=int, default=6)
    parser.add_argument("--cache-thrash-mib", type=int, default=512)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("refusing to overwrite evidence")
    capture = json.loads(args.capture.read_text())
    layer, route, gates = capture["layer"], capture["route"], capture["gates"]
    if len(route) != 4 or len(gates) != 4:
        raise SystemExit("capture must contain a four-expert route")
    native = Path(__file__).parents[1] / "modules/aion_inference/native"
    store = GptOssExpertFrameStore(args.manifest, 64 * 1024 * 1024)
    values = store.get_layer_route_parallel(layer, route, workers=4)
    with tempfile.TemporaryDirectory(prefix="aion-gptoss-split-metal-") as temporary:
        root = Path(temporary)
        cpu_exe, metal_exe = root / "cpu", root / "metal"
        libraries = ["-L/opt/homebrew/lib", "-lggml", "-lggml-base", "-ldl"]
        subprocess.run([
            "clang++", "-std=c++17", "-O3", "-I/opt/homebrew/include",
            str(native / "gptoss_packed_route_cpu_gate.cpp"), *libraries,
            "-o", str(cpu_exe),
        ], check=True)
        subprocess.run([
            "clang++", "-std=c++17", "-O3", "-Wno-deprecated-declarations",
            "-fobjc-arc", "-framework", "Foundation", "-framework", "Metal",
            str(native / "gptoss_split_mxfp4_route_probe.mm"), "-o", str(metal_exe),
        ], check=True)
        for position, value in enumerate(values):
            for projection in ("gate", "up", "down"):
                for kind in ("weight", "bias"):
                    (root / f"{position}-{projection}-{kind}.bin").write_bytes(
                        value[projection][kind]
                    )
        stem = args.capture.with_suffix("")
        input_path = Path(str(stem) + "-router.bin")
        gate_csv = ",".join(str(value) for value in gates)
        cpu_output, metal_output = root / "cpu.bin", root / "metal.bin"
        environment = {
            **os.environ,
            "AION_INPUT_PATH": str(input_path),
            "AION_CPU_CACHE_THRASH_MIB": str(args.cache_thrash_mib),
        }
        cpu = json.loads(subprocess.check_output([
            str(cpu_exe), str(root), ",".join(map(str, route)), gate_csv,
            "20", str(args.threads),
        ], env={**environment, "AION_OUTPUT_PATH": str(cpu_output)}, text=True))
        metal = json.loads(subprocess.check_output([
            str(metal_exe), str(native / "gptoss_split_mxfp4_route.metal"),
            str(root), gate_csv, str(input_path), str(metal_output),
        ], env=environment, text=True))
        reference = np.fromfile(cpu_output, dtype="<f4").astype(np.float64)
        candidate = np.fromfile(metal_output, dtype="<f4").astype(np.float64)
    delta = reference - candidate
    relative_l2 = float(np.linalg.norm(delta) / np.linalg.norm(reference))
    speedup = float(cpu["p50_ms"] / metal["warm_p50_ms"])
    promoted = relative_l2 <= 0.01 and speedup >= 1.15
    report = {
        "schema": "aion.gptoss-120b-split-mxfp4-metal-route-gate.v1",
        "status": "ADVANCE_SPLIT_METAL_ROUTE" if promoted else "NOT_PROMOTED",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": "GPT-OSS 120B Q4_K_M/MXFP4",
        "layer": layer,
        "route": route,
        "gates": gates,
        "cpu": cpu,
        "split_mxfp4_metal": metal,
        "metal_speedup": speedup,
        "relative_l2_error": relative_l2,
        "maximum_absolute_error": float(np.abs(delta).max()),
        "cosine_similarity": float(
            reference @ candidate / (np.linalg.norm(reference) * np.linalg.norm(candidate))
        ),
        "argmax_equal": bool(reference.argmax() == candidate.argmax()),
        "warehouse_metrics": store.metrics(),
        "source_capture": str(args.capture.resolve()),
        "source_capture_sha256": hashlib.sha256(args.capture.read_bytes()).hexdigest(),
        "promotion_gates": {"minimum_speedup": 1.15, "maximum_relative_l2": 0.01},
        "claim_boundary": (
            "One real four-expert layer route under an equal CPU cache-displacement charge. "
            "The candidate losslessly splits GGUF MXFP4 scale/value streams and directly "
            "calculates them with a custom Metal kernel. This is a changed-arithmetic "
            "microgate, not generated-token or semantic-quality evidence."
        ),
    }
    report["canonical_sha256"] = hashlib.sha256(json.dumps(
        report, sort_keys=True, separators=(",", ":"),
    ).encode()).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "status": report["status"], "metal_speedup": speedup,
        "relative_l2_error": relative_l2,
        "canonical_sha256": report["canonical_sha256"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
