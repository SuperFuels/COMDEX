#!/usr/bin/env python3
"""Execute one real packed gpt-oss expert after exact SD-frame loading."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from backend.modules.aion_inference.gptoss_expert_frame_store import GptOssExpertFrameStore


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--layer", type=int, default=0)
    parser.add_argument("--expert", type=int, default=0)
    parser.add_argument("--repetitions", type=int, default=8)
    parser.add_argument("--threads", type=int, default=8)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("refusing to overwrite evidence")
    source = Path(__file__).parents[1] / "modules/aion_inference/native/gptoss_packed_expert_cpu_gate.cpp"
    with tempfile.TemporaryDirectory(prefix="aion-gptoss-expert-") as temporary:
        root = Path(temporary)
        executable = root / "gate"
        subprocess.run([
            "clang++", "-std=c++17", "-O3", "-I/opt/homebrew/include",
            str(source), "-L/opt/homebrew/lib", "-lggml", "-lggml-base", "-ldl",
            "-o", str(executable),
        ], check=True)
        store = GptOssExpertFrameStore(args.manifest, 64 * 1024 * 1024)
        value = store.get(args.layer, args.expert)
        paths = []
        for projection in ("gate", "up", "down"):
            for kind in ("weight", "bias"):
                path = root / f"{projection}-{kind}.bin"
                path.write_bytes(value[projection][kind])
                paths.append(str(path))
        first = json.loads(subprocess.check_output([
            str(executable), *paths, str(args.repetitions), str(args.threads)], text=True))
        second = json.loads(subprocess.check_output([
            str(executable), *paths, str(args.repetitions), str(args.threads)], text=True))
    repeatable = first["finite"] and second["finite"] and first["checksum"] == second["checksum"]
    report = {
        "schema": "aion.gptoss-packed-expert-compute-gate.v1",
        "status": "PASSED" if repeatable else "FAILED",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "manifest": str(args.manifest.resolve()),
        "layer": args.layer, "expert": args.expert,
        "warehouse_metrics": store.metrics(),
        "run_a": first, "run_b": second,
        "finite_and_checksum_repeatable": repeatable,
        "claim_boundary": (
            "This is one real packed MXFP4 gpt-oss expert calculation using exact weights "
            "loaded from the verified SD warehouse. It is a CPU microgate with a synthetic "
            "activation, not a full transformer token, semantic output, or tokens-per-second result."
        ),
    }
    report["canonical_sha256"] = hashlib.sha256(
        json.dumps(report, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": report["status"], "output": str(args.output),
                      "run_a": first, "run_b": second,
                      "warehouse_metrics": report["warehouse_metrics"],
                      "canonical_sha256": report["canonical_sha256"]}, sort_keys=True))


if __name__ == "__main__":
    main()
