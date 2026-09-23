#!/usr/bin/env python3
"""Evaluate whether real GPT-OSS routes can amortise SD reads and Metal work."""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--route-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("refusing to overwrite evidence")
    manifest = json.loads(args.manifest.read_text())
    route_report = json.loads(args.route_report.read_text())
    if manifest.get("status") != "COMPLETE_VERIFIED":
        raise SystemExit("warehouse is not complete and verified")
    if not route_report.get("final_hidden_and_logits_bitwise_repeatable"):
        raise SystemExit("route source is not exact and repeatable")

    component_bytes: dict[tuple[int, int], int] = collections.defaultdict(int)
    component_raw_bytes: dict[tuple[int, int], int] = collections.defaultdict(int)
    for region in manifest["regions"]:
        name = region["region_name"]
        if not name.startswith("blk.") or ".ffn_" not in name or "_exps." not in name:
            continue
        layer = int(name.split(".")[1])
        for frame in region["frames"]:
            component_bytes[(layer, int(frame["expert"]))] += int(frame["compressed_bytes"])
            component_raw_bytes[(layer, int(frame["expert"]))] += int(frame["raw_bytes"])

    tokens = route_report["run_a"]["tokens"]
    layer_reports = []
    all_occupancies = []
    naive_bytes = grouped_bytes = 0
    for layer in range(36):
        selected = [expert for token in tokens
                    for expert in token["layers"][layer]["route"]]
        counts = collections.Counter(selected)
        occupancies = sorted(counts.values(), reverse=True)
        all_occupancies.extend(occupancies)
        layer_naive = sum(component_bytes[(layer, expert)] for expert in selected)
        layer_grouped = sum(component_bytes[(layer, expert)] for expert in counts)
        naive_bytes += layer_naive
        grouped_bytes += layer_grouped
        layer_reports.append({
            "layer": layer, "selected_activations": len(selected),
            "unique_experts": len(counts), "maximum_expert_batch": max(occupancies),
            "mean_expert_batch": len(selected) / len(counts),
            "experts_at_batch_4_or_more": sum(value >= 4 for value in occupancies),
            "experts_at_batch_8_or_more": sum(value >= 8 for value in occupancies),
            "grouped_compressed_bytes": layer_grouped,
            "naive_compressed_bytes": layer_naive,
        })
    selection_count = len(tokens) * 36 * 4
    crossover_16 = sum(value >= 16 for value in all_occupancies)
    split = len(tokens) // 2
    dictionary_candidates = []
    for expert_limit in (4, 6, 8, 12, 16):
        covered = total = resident_raw = 0
        for layer in range(36):
            training = collections.Counter(
                expert for token in tokens[:split]
                for expert in token["layers"][layer]["route"])
            selected = [expert for expert, _ in training.most_common(expert_limit)]
            selected_set = set(selected)
            resident_raw += sum(component_raw_bytes[(layer, expert)]
                                for expert in selected)
            for token in tokens[split:]:
                for expert in token["layers"][layer]["route"]:
                    covered += expert in selected_set
                    total += 1
        dictionary_candidates.append({
            "experts_per_layer": expert_limit,
            "training_tokens": split,
            "held_out_tokens": len(tokens) - split,
            "held_out_route_coverage": covered / total,
            "resident_raw_bytes": resident_raw,
            "within_3_gib": resident_raw <= 3 * 1024 * 1024 * 1024,
        })
    report = {
        "schema": "aion.gptoss-route-grouping-gate.v1",
        "status": "STOP_UNCONSTRAINED_BATCHED_METAL"
                  if crossover_16 == 0 else "ADVANCE_REAL_ROUTE_BATCH",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": "GPT-OSS 120B Q4_K_M/MXFP4",
        "source_route_report": str(args.route_report.resolve()),
        "source_route_report_canonical_sha256": route_report["canonical_sha256"],
        "tokens": len(tokens), "layers": 36,
        "selected_layer_expert_activations": selection_count,
        "unique_layer_expert_pairs": len(all_occupancies),
        "naive_compressed_bytes": naive_bytes,
        "perfect_grouping_compressed_bytes": grouped_bytes,
        "perfect_grouping_byte_reduction": 1.0 - grouped_bytes / naive_bytes,
        "mean_activations_per_loaded_expert": selection_count / len(all_occupancies),
        "maximum_observed_expert_batch": max(all_occupancies),
        "expert_groups_at_metal_batch_16_crossover": crossover_16,
        "expert_groups_at_batch_8_or_more": sum(value >= 8 for value in all_occupancies),
        "expert_groups_at_batch_4_or_more": sum(value >= 4 for value in all_occupancies),
        "dictionary_candidates": dictionary_candidates,
        "layer_reports": layer_reports,
        "decision_rule": (
            "Advance unconstrained real-route Metal only if at least one real expert "
            "group reaches the measured batch-16 crossover. Otherwise stop and require "
            "a separately quality-gated route-concentration architecture."
        ),
        "claim_boundary": (
            "This is an exact calculation over captured real routes and hash-bound "
            "warehouse frame sizes. It is a feasibility projection, not an executed "
            "batched transformer or generated tokens-per-second measurement."
        ),
    }
    report["canonical_sha256"] = hashlib.sha256(
        json.dumps(report, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: report[key] for key in (
        "status", "selected_layer_expert_activations", "unique_layer_expert_pairs",
        "perfect_grouping_byte_reduction", "mean_activations_per_loaded_expert",
        "maximum_observed_expert_batch", "expert_groups_at_metal_batch_16_crossover",
        "canonical_sha256")}, sort_keys=True))


if __name__ == "__main__":
    main()
