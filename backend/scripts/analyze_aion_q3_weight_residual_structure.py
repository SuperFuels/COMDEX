#!/usr/bin/env python3
"""Bound whether sparse exact corrections can repair a compact Q3 projection."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from backend.modules.aion_inference.gptoss_expert_frame_store import GptOssExpertFrameStore


WIDTH = 2880
PADDED = 3072


def canonical(value: dict) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"),
    ).encode()).hexdigest()


def cumulative_fraction(values: np.ndarray, fractions: tuple[float, ...]) -> dict[str, float]:
    ordered = np.sort(values.reshape(-1))[::-1]
    cumulative = np.cumsum(ordered, dtype=np.float64)
    total = float(cumulative[-1]) if len(cumulative) else 0.0
    return {str(fraction): (float(cumulative[max(0, int(np.ceil(len(ordered) * fraction)) - 1)]) /
                            total if total else 1.0)
            for fraction in fractions}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--activations", type=Path, required=True)
    parser.add_argument("--layer", type=int, default=12)
    parser.add_argument("--route-rank", type=int, choices=(0, 1, 2, 3), default=3)
    parser.add_argument("--projection", choices=("gate", "up", "down"), default="up")
    parser.add_argument("--maximum-experts", type=int, default=8)
    parser.add_argument("--threads", type=int, default=6)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("refusing to overwrite evidence")
    captures = sorted(args.activations.glob(f"position-*-layer-{args.layer}.json"))
    experts: list[int] = []
    capture_hashes = {}
    for path in captures:
        row = json.loads(path.read_text())
        expert = int(row["route"][args.route_rank])
        capture_hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
        if expert not in experts:
            experts.append(expert)
        if len(experts) >= args.maximum_experts:
            break
    if not experts:
        raise SystemExit("no routed experts found")
    native = Path(__file__).parents[1] / "modules/aion_inference/native"
    common = ["clang++", "-std=c++17", "-O3", "-I/opt/homebrew/include"]
    libraries = ["-L/opt/homebrew/lib", "-lggml", "-lggml-base", "-ldl"]
    store = GptOssExpertFrameStore(args.manifest, 256 * 1024 * 1024)
    observations = []
    with tempfile.TemporaryDirectory(prefix="aion-q3-residual-bound-") as temporary:
        root = Path(temporary)
        original_dequantizer = root / "mxfp4-dequantize"
        converter = root / "mxfp4-to-q3"
        compact_dequantizer = root / "q3-dequantize"
        for source, target in (
            ("gptoss_mxfp4_dequantize.cpp", original_dequantizer),
            ("gptoss_mxfp4_to_padded_k.cpp", converter),
            ("gptoss_padded_k_dequantize.cpp", compact_dequantizer),
        ):
            subprocess.run([*common, str(native / source), *libraries, "-o", str(target)],
                           check=True)
        for expert in experts:
            value = store.get_layer_route_parallel(
                args.layer, [expert], workers=1,
            )[0][args.projection]["weight"]
            source = root / f"expert-{expert}.mxfp4"
            original_path = root / f"expert-{expert}.f32"
            compact_path = root / f"expert-{expert}.q3"
            compact_f32_path = root / f"expert-{expert}.q3.f32"
            source.write_bytes(value)
            subprocess.run([str(original_dequantizer), str(source), str(original_path),
                            str(WIDTH), str(args.threads)], check=True,
                           stdout=subprocess.DEVNULL)
            subprocess.run([str(converter), str(source), str(compact_path), "q3_k",
                            str(WIDTH), str(args.threads)], check=True,
                           stdout=subprocess.DEVNULL)
            subprocess.run([str(compact_dequantizer), str(compact_path),
                            str(compact_f32_path), "q3_k", str(args.threads)], check=True,
                           stdout=subprocess.DEVNULL)
            original = np.memmap(original_path, dtype="<f4", mode="r", shape=(WIDTH, WIDTH))
            compact = np.memmap(compact_f32_path, dtype="<f4", mode="r",
                                shape=(PADDED, PADDED))[:WIDTH, :WIDTH]
            residual = np.asarray(original, dtype=np.float32) - np.asarray(compact, dtype=np.float32)
            squared = residual.astype(np.float64) ** 2
            row_energy = squared.sum(axis=1)
            block = 64
            trimmed = squared[:WIDTH // block * block, :WIDTH // block * block]
            block_energy = trimmed.reshape(WIDTH // block, block,
                                           WIDTH // block, block).sum(axis=(1, 3))
            observations.append({
                "expert": expert,
                "original_bytes": len(value),
                "q3_bytes": compact_path.stat().st_size,
                "relative_frobenius_error": float(
                    np.sqrt(squared.sum()) /
                    np.linalg.norm(np.asarray(original, dtype=np.float64))),
                "residual_energy_in_top_row_fraction": cumulative_fraction(
                    row_energy, (.01, .02, .05, .10, .20)),
                "residual_energy_in_top_64x64_block_fraction": cumulative_fraction(
                    block_energy, (.01, .02, .05, .10, .20)),
            })
    median_top10_blocks = float(np.median([
        row["residual_energy_in_top_64x64_block_fraction"]["0.1"]
        for row in observations
    ]))
    status = ("ADVANCE_SPARSE_Q3_RESIDUAL" if median_top10_blocks >= .75
              else "STOP_SPARSE_Q3_RESIDUAL")
    report = {
        "schema": "aion.gptoss-120b-q3-weight-residual-structure.v1",
        "status": status,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": "GPT-OSS 120B Q4_K_M/MXFP4",
        "quality_track": True,
        "layer": args.layer,
        "route_rank": args.route_rank,
        "projection": args.projection,
        "experts": experts,
        "observations": observations,
        "median_residual_energy_in_top_10pct_blocks": median_top10_blocks,
        "advance_gate": {"minimum_top_10pct_block_energy": .75},
        "capture_hashes": capture_hashes,
        "warehouse_metrics": store.metrics(),
        "claim_boundary": (
            "This is an offline weight-space upper-bound screen. It does not execute a "
            "corrected expert and makes no token-speed or semantic-quality claim. Sparse "
            "correction advances only if Q3 error energy is sufficiently concentrated."
        ),
    }
    report["canonical_sha256"] = canonical(report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": status, "experts": len(experts),
                      "median_top10_block_energy": median_top10_blocks,
                      "canonical_sha256": report["canonical_sha256"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
