#!/usr/bin/env python3
"""Calculate an optimistic end-to-end ceiling for GPT-OSS attention batching."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def canonical_sha256(value: dict) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def summarize_run(run: dict) -> dict:
    wall = float(run["wall_seconds"])
    layers = run["layers"]
    attention = sum(float(layer.get("attention_ms_total", 0.0)) for layer in layers) / 1000
    moe = sum(float(layer.get("moe_ms_total", 0.0)) for layer in layers) / 1000
    delivery = sum(float(layer.get("expert_load_seconds", 0.0)) for layer in layers)
    output = sum(float(item.get("output_ms", 0.0)) for item in run.get("positions", [])) / 1000

    def speedup_if_removed(seconds: float) -> float:
        # This intentionally gives the candidate every benefit: measured component
        # time is subtracted from wall time even if instrumentation overlaps.
        remaining = max(wall - seconds, 1e-12)
        return wall / remaining

    return {
        "mode": run.get("mode"),
        "wall_seconds": wall,
        "positions": len(run.get("positions", [])),
        "all_positions_bitwise_exact": bool(run.get("all_positions_bitwise_exact")),
        "measured_attention_seconds": attention,
        "measured_moe_seconds": moe,
        "measured_expert_delivery_seconds": delivery,
        "measured_output_seconds": output,
        "attention_fraction_of_wall": attention / wall,
        "optimistic_speedup_if_attention_were_free": speedup_if_removed(attention),
        "optimistic_speedup_if_attention_and_moe_were_free": speedup_if_removed(
            attention + moe
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--minimum-material-speedup", type=float, default=1.5)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("refusing to overwrite evidence")
    source = json.loads(args.source.read_text())
    runs = [summarize_run(run) for run in source["runs"]]
    if not runs or not all(run["all_positions_bitwise_exact"] for run in runs):
        raise SystemExit("source must contain exact completed runs")
    best = max(run["optimistic_speedup_if_attention_were_free"] for run in runs)
    status = (
        "PROCEED_TO_BATCHED_ATTENTION"
        if best >= args.minimum_material_speedup
        else "STOP_BATCHED_ATTENTION_AS_MATERIAL_SPEED_STRATEGY"
    )
    report = {
        "schema": "aion.gptoss-120b-attention-batch-ceiling.v1",
        "status": status,
        "source": str(args.source.resolve()),
        "source_file_sha256": hashlib.sha256(args.source.read_bytes()).hexdigest(),
        "minimum_material_speedup": args.minimum_material_speedup,
        "runs": runs,
        "best_optimistic_attention_only_speedup": best,
        "decision": (
            "Do not implement attention batching as a primary speed strategy. Even "
            "making measured attention completely free cannot approach the declared "
            "material-speed threshold. Preserve attention batching only as a future "
            "compound optimization after expert work and delivery are reduced."
            if status.startswith("STOP_")
            else "Implement the narrow attention-batching candidate."
        ),
        "claim_boundary": (
            "This is an optimistic upper bound from exact eight-position full-model "
            "instrumentation, not a measured candidate speed. Subtracting component "
            "time from wall time can overstate the available gain when timings overlap."
        ),
    }
    report["canonical_sha256"] = canonical_sha256(report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "status": status,
        "best_optimistic_attention_only_speedup": best,
        "canonical_sha256": report["canonical_sha256"],
    }, indent=2))


if __name__ == "__main__":
    main()
