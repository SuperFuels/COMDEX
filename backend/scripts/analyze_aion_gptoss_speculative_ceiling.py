#!/usr/bin/env python3
"""Bound speculative speed before implementing a costly multi-token runtime."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


LAYERS = 36


def canonical_sha256(value: dict) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, action="append", required=True)
    parser.add_argument("--family", action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--measured-block-speedup", type=float, required=True)
    parser.add_argument("--compatible-external-draft-installed", action="store_true")
    args = parser.parse_args()
    if len(args.input) != len(args.family):
        raise SystemExit("each input requires one family label")
    if args.output.exists():
        raise SystemExit("refusing to overwrite evidence")
    if args.measured_block_speedup <= 1:
        raise SystemExit("measured block speedup must exceed one")

    by_layer: dict[int, list[bool]] = {}
    sources = []
    for path, family in zip(args.input, args.family):
        report = json.loads(path.read_text())
        prompt_positions = len(report["input_token_ids"])
        rows: dict[int, list[bool]] = {}
        # Use only run A so deterministic replication is not counted as new data.
        for token in report["run_a"]["tokens"]:
            if token["position"] < prompt_positions:
                continue
            for layer in token["layers"]:
                diagnostic = layer.get("early_exit_diagnostic")
                if diagnostic is None:
                    continue
                match = diagnostic["argmax_token_id"] == token["generated_token_id"]
                rows.setdefault(layer["layer"], []).append(match)
                by_layer.setdefault(layer["layer"], []).append(match)
        sources.append(
            {
                "family": family,
                "source_canonical_sha256": report["canonical_sha256"],
                "distinct_continuation_positions": report["token_count"] - prompt_positions,
                "agreement_by_layer": {
                    str(layer): sum(matches) / len(matches)
                    for layer, matches in sorted(rows.items())
                },
            }
        )

    layer_bounds = {}
    for layer, matches in sorted(by_layer.items()):
        lower_fraction = (layer + 1) / LAYERS
        verifier_fraction = (LAYERS - layer - 1) / LAYERS
        ideal_cost_fraction = lower_fraction + verifier_fraction / args.measured_block_speedup
        layer_bounds[str(layer)] = {
            "distinct_positions": len(matches),
            "oracle_path_argmax_agreement": sum(matches) / len(matches),
            "serial_draft_layer_fraction": lower_fraction,
            "remaining_verifier_layer_fraction": verifier_fraction,
            "ideal_speedup_if_every_draft_were_accepted": 1 / ideal_cost_fraction,
        }

    best_ideal = max(value["ideal_speedup_if_every_draft_were_accepted"] for value in layer_bounds.values())
    report = {
        "schema": "aion.gptoss-120b-speculative-ceiling.v1",
        "status": "STOP_INTERMEDIATE_DEPTH_DRAFT_FOR_ORDER_GAIN",
        "sources": sources,
        "measured_exact_block_speedup": args.measured_block_speedup,
        "layer_bounds": layer_bounds,
        "best_ideal_intermediate_draft_speedup": best_ideal,
        "free_external_draft_ceiling_speedup": args.measured_block_speedup,
        "compatible_external_draft_installed": args.compatible_external_draft_installed,
        "decision": (
            "Do not build the intermediate-depth speculative runtime for the sustained-throughput objective. "
            "Even the optimistic bound assumes every proposal is accepted and ignores rejection, draft-head, scheduling, and KV catch-up overhead."
        ),
        "claim_boundary": (
            "This is an architecture-and-observed-agreement upper bound, not a measured generation-speed result. "
            "Agreement is measured on authoritative full-depth trajectories; a free-running draft can only do worse after its first mismatch. "
            "Layer fractions assume equal layer cost and therefore remain an approximation."
        ),
    }
    report["canonical_sha256"] = canonical_sha256(report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"canonical_sha256": report["canonical_sha256"], "status": report["status"], "best_ideal_speedup": best_ideal}))


if __name__ == "__main__":
    main()
