#!/usr/bin/env python3
"""Compare one real GPT-OSS MXFP4 expert on CPU and Metal."""
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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--layer", type=int, default=0)
    parser.add_argument("--expert", type=int, default=0)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("refusing to overwrite evidence")
    native = Path(__file__).parents[1] / "modules/aion_inference/native"
    with tempfile.TemporaryDirectory(prefix="aion-gptoss-metal-gate-") as temporary:
        root = Path(temporary)
        metal_exe, cpu_exe = root / "metal", root / "cpu"
        common = ["clang++", "-std=c++17", "-O3", "-I/opt/homebrew/include"]
        libraries = ["-L/opt/homebrew/lib", "-lggml", "-lggml-base", "-ldl"]
        subprocess.run([*common, str(native / "gptoss_mxfp4_metal_probe.cpp"),
                        *libraries, "-o", str(metal_exe)], check=True)
        subprocess.run([*common, str(native / "gptoss_packed_expert_cpu_gate.cpp"),
                        *libraries, "-o", str(cpu_exe)], check=True)
        store = GptOssExpertFrameStore(args.manifest, 64 * 1024 * 1024)
        value = store.get(args.layer, args.expert)
        input_path = root / "input.bin"
        activation = np.sin(np.arange(2880, dtype=np.float32) * np.float32(0.00390625))
        input_path.write_bytes(activation.tobytes())
        components = []
        for projection in ("gate", "up", "down"):
            for kind in ("weight", "bias"):
                path = root / f"{projection}-{kind}.bin"
                path.write_bytes(value[projection][kind])
                components.append(str(path))
        cpu_output, metal_output = root / "cpu.bin", root / "metal.bin"
        environment = {**os.environ, "AION_INPUT_PATH": str(input_path),
                       "AION_OUTPUT_PATH": str(cpu_output)}
        cpu = json.loads(subprocess.check_output(
            [str(cpu_exe), *components, "8", "8"], env=environment, text=True))
        metal_process = subprocess.run(
            [str(metal_exe), str(input_path), *components, str(metal_output)],
            text=True, capture_output=True, check=True)
        metal = json.loads(metal_process.stdout)
        reference = np.fromfile(cpu_output, dtype="<f4").astype(np.float64)
        candidate = np.fromfile(metal_output, dtype="<f4").astype(np.float64)
        difference = reference - candidate
        comparison = {
            "values": int(reference.size),
            "bitwise_equal": bool(np.array_equal(reference, candidate)),
            "argmax_equal": int(reference.argmax()) == int(candidate.argmax()),
            "max_abs_error": float(np.abs(difference).max()),
            "mean_abs_error": float(np.abs(difference).mean()),
            "relative_l2_error": float(np.linalg.norm(difference) / np.linalg.norm(reference)),
            "metal_over_cpu_compute_ratio": metal["warm_p50_ms"] / cpu["p50_ms"],
        }
    promoted = (comparison["relative_l2_error"] <= 0.01
                and comparison["argmax_equal"]
                and metal["warm_p50_ms"] <= 0.85 * cpu["p50_ms"])
    report = {
        "schema": "aion.gptoss-mxfp4-metal-gate.v1",
        "status": "PROMOTED" if promoted else "NOT_PROMOTED",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": "GPT-OSS 120B Q4_K_M/MXFP4",
        "layer": args.layer, "expert": args.expert,
        "cpu": cpu, "metal": metal, "comparison": comparison,
        "warehouse_metrics": store.metrics(),
        "gates": {"relative_l2_at_most": 0.01, "argmax_equal": True,
                  "metal_speed_improvement_at_least": 0.15},
        "claim_boundary": (
            "One real expert with one synthetic activation. This tests direct packed "
            "Metal support and a narrow warm kernel; it is not a transformer-token or "
            "semantic-quality result. Bitwise equality remains mandatory on the exact track."
        ),
    }
    report["canonical_sha256"] = hashlib.sha256(
        json.dumps(report, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": report["status"], "comparison": comparison,
                      "canonical_sha256": report["canonical_sha256"]}, sort_keys=True))


if __name__ == "__main__":
    main()
