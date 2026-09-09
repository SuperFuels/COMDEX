#!/usr/bin/env python3
"""Measure held-out functional rank across real packed GPT-OSS experts."""
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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--layer", type=int, default=0)
    parser.add_argument("--train-probes", type=int, default=24)
    parser.add_argument("--holdout-probes", type=int, default=12)
    parser.add_argument("--seed", type=int, default=120036)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("refusing to overwrite evidence")
    if args.train_probes < 4 or args.holdout_probes < 4:
        raise SystemExit("too few probes")
    manifest = json.loads(args.manifest.read_text())
    if manifest.get("status") != "COMPLETE_VERIFIED":
        raise SystemExit("warehouse is not complete and verified")

    rng = np.random.default_rng(args.seed)
    total_probes = args.train_probes + args.holdout_probes
    activations = rng.standard_normal((total_probes, 2880), dtype=np.float32)
    # Keep the synthetic inputs in a transformer-like bounded range.
    activations = np.clip(activations, -4.0, 4.0)
    responses = np.empty((128, total_probes, 2880), dtype=np.float32)
    retrieval_seconds = []
    compute_seconds = []
    native = Path(__file__).parents[1] / "modules/aion_inference/native"
    with tempfile.TemporaryDirectory(prefix="aion-gptoss-basis-") as temporary:
        root = Path(temporary); executable = root / "cpu"
        subprocess.run([
            "clang++", "-std=c++17", "-O3", "-I/opt/homebrew/include",
            str(native / "gptoss_packed_expert_cpu_gate.cpp"),
            "-L/opt/homebrew/lib", "-lggml", "-lggml-base", "-ldl",
            "-o", str(executable),
        ], check=True)
        input_path = root / "input.bin"; input_path.write_bytes(activations.tobytes())
        component_paths = [root / f"component-{index}.bin" for index in range(6)]
        output_path = root / "output.bin"
        store = GptOssExpertFrameStore(args.manifest, 64 * 1024 * 1024)
        for expert in range(128):
            started = time.perf_counter(); value = store.get(args.layer, expert)
            retrieval_seconds.append(time.perf_counter() - started)
            index = 0
            for projection in ("gate", "up", "down"):
                for kind in ("weight", "bias"):
                    component_paths[index].write_bytes(value[projection][kind]); index += 1
            environment = {
                **os.environ, "AION_BATCH": str(total_probes),
                "AION_INPUT_PATH": str(input_path),
                "AION_OUTPUT_PATH": str(output_path),
            }
            started = time.perf_counter()
            subprocess.check_output([
                str(executable), *(str(path) for path in component_paths), "1", "8"
            ], env=environment, text=True)
            compute_seconds.append(time.perf_counter() - started)
            responses[expert] = np.fromfile(output_path, dtype="<f4").reshape(total_probes, 2880)

    train = responses[:, :args.train_probes].reshape(128, -1).astype(np.float64)
    holdout = responses[:, args.train_probes:].reshape(128, -1).astype(np.float64)
    train_mean = train.mean(axis=0, keepdims=True)
    holdout_mean = holdout.mean(axis=0, keepdims=True)
    train_centered = train - train_mean
    holdout_centered = holdout - holdout_mean
    gram = train_centered @ train_centered.T
    eigenvalues, eigenvectors = np.linalg.eigh(gram)
    order = np.argsort(eigenvalues)[::-1]
    eigenvalues = np.maximum(eigenvalues[order], 0.0)
    eigenvectors = eigenvectors[:, order]
    total_variance = float(eigenvalues.sum())
    ranks = []
    for rank in (4, 8, 12, 16, 32, 64):
        basis = eigenvectors[:, :rank]
        reconstruction = holdout_mean + basis @ (basis.T @ holdout_centered)
        difference = holdout - reconstruction
        ranks.append({
            "rank": rank,
            "representation_reduction": 128 / rank,
            "train_variance_explained": float(eigenvalues[:rank].sum() / total_variance),
            "holdout_relative_l2_error": float(np.linalg.norm(difference) / np.linalg.norm(holdout)),
            "holdout_mean_abs_error": float(np.abs(difference).mean()),
            "holdout_max_abs_error": float(np.abs(difference).max()),
        })
    qualifying = [
        item for item in ranks
        if item["representation_reduction"] >= 10.0
        and item["holdout_relative_l2_error"] <= 0.05
    ]
    report = {
        "schema": "aion.gptoss-expert-functional-basis-gate.v1",
        "status": "ADVANCE_SHARED_EXPERT_BASIS" if qualifying else "STOP_SHARED_EXPERT_BASIS",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": "GPT-OSS 120B Q4_K_M/MXFP4",
        "layer": args.layer, "experts": 128,
        "train_probes": args.train_probes, "holdout_probes": args.holdout_probes,
        "seed": args.seed, "rank_results": ranks,
        "gates": {"representation_reduction_at_least": 10.0,
                  "holdout_relative_l2_error_at_most": 0.05},
        "retrieval_seconds_total": sum(retrieval_seconds),
        "expert_process_seconds_total": sum(compute_seconds),
        "warehouse_metrics": store.metrics(),
        "claim_boundary": (
            "A bounded random-projection mechanism test on all 128 real experts in one "
            "layer. The expert-space basis is learned only from training activations and "
            "evaluated on disjoint held-out activations. It is an optimistic functional-rank "
            "bound, not a compiled basis, transformer generation, or semantic evaluation."
        ),
    }
    report["canonical_sha256"] = hashlib.sha256(
        json.dumps(report, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": report["status"], "rank_results": ranks,
                      "canonical_sha256": report["canonical_sha256"]}, sort_keys=True))


if __name__ == "__main__":
    main()
