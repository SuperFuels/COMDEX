#!/usr/bin/env python3
"""Decide whether DFlash can profit on AION's current GPT-OSS 120B verifier."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def canonical_sha256(value: dict) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--block-result", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--compatible-drafter-path", type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("refusing to overwrite evidence")

    block_results = []
    for path in args.block_result:
        source = json.loads(path.read_text())
        block_results.append({
            "positions": int(source["positions"]),
            "status": source["status"],
            "all_positions_bitwise_exact": bool(
                source["all_positions_all_runs_bitwise_exact"]),
            "wall_speedup_p50": float(source["wall_speedup_p50"]),
            "compressed_traffic_reduction_p50": float(
                source["compressed_traffic_reduction_p50"]),
            "source_canonical_sha256": source["canonical_sha256"],
            "source_file_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        })
    block_results.sort(key=lambda row: row["positions"])
    best = max(block_results, key=lambda row: row["wall_speedup_p50"])
    drafter_present = bool(
        args.compatible_drafter_path and args.compatible_drafter_path.exists())
    verifier_gate = best["wall_speedup_p50"] >= 1.5
    acceptance = {
        "compatible_gptoss_120b_drafter_installed": drafter_present,
        "measured_exact_block_verifier_speedup_at_least_1_5x": verifier_gate,
        "all_source_block_outputs_bitwise_exact": all(
            row["all_positions_bitwise_exact"] for row in block_results),
    }
    report = {
        "schema": "aion.gptoss-120b-dflash-eligibility.v1",
        "status": (
            "ADVANCE_DFLASH_INTEGRATION"
            if all(acceptance.values())
            else "DEFER_DFLASH_UNTIL_BATCHED_VERIFIER"
        ),
        "model": "GPT-OSS 120B",
        "external_candidate": {
            "name": "z-lab/gpt-oss-120b-DFlash",
            "parameter_count": 800_000_000,
            "separate_checkpoint_required": True,
            "checkpoint_download_permitted_by_locked_program": False,
            "published_gptoss_evaluation_backend": "SGLang on one H200 GPU",
            "published_source": "https://huggingface.co/z-lab/gpt-oss-120b-DFlash",
            "paper": "https://arxiv.org/abs/2602.06036",
        },
        "local_drafter": {
            "path": str(args.compatible_drafter_path.resolve())
            if args.compatible_drafter_path else None,
            "present": drafter_present,
        },
        "block_results": block_results,
        "best_measured_block_verifier_speedup": best["wall_speedup_p50"],
        "best_measured_block_positions": best["positions"],
        "acceptance": acceptance,
        "decision": (
            "Do not download or integrate the external drafter yet. Build and prove a "
            "genuinely batched multi-position verifier first. Reopen DFlash when the "
            "same target model verifies a real block at least 1.5x faster under the "
            "bounded Mac/SD path."
        ),
        "claim_boundary": (
            "This gate measures verifier eligibility, not DFlash acceptance rate or "
            "end-to-end speculative throughput. Published accelerator results do not "
            "transfer automatically to the custom M3 Pro SD-backed runtime."
        ),
    }
    report["canonical_sha256"] = canonical_sha256(report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "status": report["status"],
        "best_measured_block_verifier_speedup": report[
            "best_measured_block_verifier_speedup"],
        "compatible_drafter_installed": drafter_present,
        "canonical_sha256": report["canonical_sha256"],
    }, indent=2))


if __name__ == "__main__":
    main()
