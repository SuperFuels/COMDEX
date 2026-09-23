#!/usr/bin/env python3
"""Bound adaptive multi-position reuse before building a speculative runtime."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from datetime import datetime, timezone
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(8 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def canonical(value: dict) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"),
    ).encode()).hexdigest()


def response_tokens(report: dict) -> tuple[int, list[dict]]:
    tokens = report["run_a"]["tokens"]
    start = next(index for index, token in enumerate(tokens)
                 if not token["input_was_forced_prompt"])
    return start, tokens[start:]


def family_bound(path: Path, block_sizes: tuple[int, ...]) -> dict:
    report = json.loads(path.read_text())
    start, tokens = response_tokens(report)
    blocks = {}
    for size in block_sizes:
        ratios = []
        saved = []
        for offset in range(0, len(tokens) - size + 1, size):
            window = tokens[offset:offset + size]
            logical = 0
            union = 0
            for layer in range(36):
                routes = [token["layers"][layer]["route"] for token in window]
                logical += sum(len(route) for route in routes)
                union += len({expert for route in routes for expert in route})
            ratios.append(logical / union)
            saved.append((logical - union) / logical)
        blocks[str(size)] = {
            "complete_nonoverlapping_windows": len(ratios),
            "expert_delivery_reduction_p50": statistics.median(ratios),
            "expert_delivery_reduction_max": max(ratios),
            "expert_delivery_fraction_saved_p50": statistics.median(saved),
        }
    return {
        "path": str(path.resolve()),
        "file_sha256": sha256_file(path),
        "canonical_sha256": report.get("canonical_sha256"),
        "response_start_position": start,
        "response_positions": len(tokens),
        "blocks": blocks,
    }


def draft_overlap(draft_path: Path, target_path: Path) -> dict:
    draft_report = json.loads(draft_path.read_text())
    target_report = json.loads(target_path.read_text())
    _, draft = response_tokens(draft_report)
    _, target = response_tokens(target_report)
    draft_ids = [token["generated_token_id"] for token in draft]
    target_ids = [token["generated_token_id"] for token in target]
    prefix = 0
    for left, right in zip(draft_ids, target_ids):
        if left != right:
            break
        prefix += 1
    return {
        "draft_path": str(draft_path.resolve()),
        "draft_file_sha256": sha256_file(draft_path),
        "target_path": str(target_path.resolve()),
        "target_file_sha256": sha256_file(target_path),
        "shared_greedy_prefix_tokens": prefix,
        "compared_positions": min(len(draft_ids), len(target_ids)),
        "boundary": (
            "This is one shared-context prefix only. It does not measure acceptance after "
            "rejection recovery and cannot be treated as a corpus acceptance rate."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--arithmetic", type=Path, required=True)
    parser.add_argument("--extraction", type=Path, required=True)
    parser.add_argument("--draft", type=Path, required=True)
    parser.add_argument("--draft-target", type=Path, required=True)
    parser.add_argument("--exact-frontier-tps", type=float, default=1.82858)
    parser.add_argument("--north-star-tps", type=float, default=30.0)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("refusing to overwrite evidence")
    families = {
        "arithmetic": family_bound(args.arithmetic, (2, 4, 8)),
        "extraction": family_bound(args.extraction, (2, 4, 8)),
    }
    best_reduction = max(
        block["expert_delivery_reduction_max"]
        for family in families.values() for block in family["blocks"].values()
    )
    report = {
        "schema": "aion.gptoss-120b-adaptive-block-bound.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": "GPT-OSS 120B Q4_K_M/MXFP4",
        "track": "quality_track_offline_route_bound",
        "families": families,
        "draft_overlap": draft_overlap(args.draft, args.draft_target),
        "exact_frontier_tps": args.exact_frontier_tps,
        "north_star_tps": args.north_star_tps,
        "north_star_required_speedup": args.north_star_tps / args.exact_frontier_tps,
        "best_observed_window_delivery_reduction": best_reduction,
        "traffic_only_optimistic_tps_ceiling": args.exact_frontier_tps * best_reduction,
        "decision": "DO_NOT_BUILD_FULL_COMPOSITE_FROM_ROUTE_REUSE_ALONE",
        "claim_boundary": (
            "Teacher routes reveal the maximum duplicate expert delivery removable inside known "
            "blocks. They do not remove autoregressive causality, include draft cost, establish "
            "post-rejection acceptance, or measure generated tokens per second. The optimistic "
            "ceiling assumes all exact-frontier time scales with expert delivery and is therefore "
            "an intentionally favourable upper bound, not a performance forecast."
        ),
    }
    report["canonical_sha256"] = canonical(report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: report[key] for key in (
        "decision", "north_star_required_speedup",
        "best_observed_window_delivery_reduction", "traffic_only_optimistic_tps_ceiling",
        "canonical_sha256",
    )}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
