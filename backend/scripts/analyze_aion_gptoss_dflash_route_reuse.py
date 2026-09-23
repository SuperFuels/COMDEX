#!/usr/bin/env python3
"""Measure the expert-reuse ceiling available to a DFlash verifier block."""
from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from collections import Counter
from pathlib import Path


def canonical_sha256(value: dict) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def summarize(tokens: list[dict], block_size: int) -> dict:
    groups: list[int] = []
    complete_blocks = 0
    for offset in range(0, len(tokens) - block_size + 1, block_size):
        block = tokens[offset:offset + block_size]
        complete_blocks += 1
        for layer in range(36):
            counts = Counter(
                expert for token in block for expert in token["layers"][layer]["route"])
            groups.extend(counts.values())
    if not groups:
        raise ValueError(f"no complete block of size {block_size}")
    occurrences = sum(groups)
    return {
        "block_size": block_size,
        "complete_blocks": complete_blocks,
        "expert_occurrences": occurrences,
        "distinct_expert_groups": len(groups),
        "mean_occurrences_per_loaded_expert": occurrences / len(groups),
        "singleton_group_fraction": sum(size == 1 for size in groups) / len(groups),
        "maximum_group_size": max(groups),
        "group_size_histogram": {
            str(size): groups.count(size) for size in sorted(set(groups))
        },
        "perfect_reuse_only_expert_delivery_upper_bound": occurrences / len(groups),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace", type=Path, required=True)
    parser.add_argument("--block-size", type=int, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("refusing to overwrite evidence")
    source = json.loads(args.trace.read_text())
    if not source.get("routes_repeatable"):
        raise SystemExit("source routes are not repeatable")
    prompt = len(source["input_token_ids"])
    tokens = source["run_a"]["tokens"][prompt:]
    blocks = [summarize(tokens, size) for size in args.block_size]
    best = max(blocks, key=lambda item: item[
        "perfect_reuse_only_expert_delivery_upper_bound"])
    report = {
        "schema": "aion.gptoss-120b-dflash-route-reuse.v1",
        "status": "STOP_UNCHANGED_EXPERT_GROUPING_AS_DFLASH_BREAKTHROUGH",
        "source": str(args.trace.resolve()),
        "source_file_sha256": hashlib.sha256(args.trace.read_bytes()).hexdigest(),
        "source_canonical_sha256": source.get("canonical_sha256"),
        "continuation_positions": len(tokens),
        "blocks": blocks,
        "best_perfect_reuse_only_expert_delivery_upper_bound": best[
            "perfect_reuse_only_expert_delivery_upper_bound"],
        "best_block_size": best["block_size"],
        "decision": (
            "Do not retry the existing group-by-identical-expert kernel as the DFlash "
            "verifier. Most real route groups are singletons. A future verifier must "
            "batch causal attention and heterogeneous expert arithmetic without route "
            "copies, or reduce the target model's physical expert work."
        ),
        "claim_boundary": (
            "The perfect-reuse figure is an optimistic upper bound for expert delivery "
            "alone: it assumes every repeated use after the first is free and excludes "
            "attention, routing, arithmetic, drafting, rejection, KV catch-up and "
            "scheduling. It is not a measured tokens-per-second result."
        ),
    }
    report["canonical_sha256"] = canonical_sha256(report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "status": report["status"],
        "best_block_size": report["best_block_size"],
        "best_upper_bound": report[
            "best_perfect_reuse_only_expert_delivery_upper_bound"],
        "canonical_sha256": report["canonical_sha256"],
    }, indent=2))


if __name__ == "__main__":
    main()
