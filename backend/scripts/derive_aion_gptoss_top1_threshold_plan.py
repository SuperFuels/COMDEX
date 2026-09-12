#!/usr/bin/env python3
"""Derive a stricter immutable GPT-OSS top-1 threshold plan."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def canonical(value: object) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
    ).encode()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--absolute-margin", type=float, required=True)
    parser.add_argument("--layers", help="Optional comma-separated subset of source layers")
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("refusing to overwrite evidence")
    if args.absolute_margin < 0.0:
        raise SystemExit("absolute margin must be non-negative")

    source = json.loads(args.input.read_text())
    source_hash = hashlib.sha256(args.input.read_bytes()).hexdigest()
    selected_layers = ({item.strip() for item in args.layers.split(",") if item.strip()}
                       if args.layers else None)
    thresholds = {
        layer: min(1.0, float(value) + args.absolute_margin)
        for layer, value in source["minimum_top_gate_gap_by_layer"].items()
        if selected_layers is None or layer in selected_layers
    }
    if selected_layers is not None and selected_layers != set(thresholds):
        missing = sorted(selected_layers - set(thresholds), key=int)
        raise SystemExit(f"requested layers absent from source plan: {missing}")
    report = {
        "schema": "aion.gptoss-120b-top1-threshold-plan.v1",
        "status": "DEVELOPMENT_CANDIDATE",
        "model": source["model"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "minimum_top_gate_gap_by_layer": thresholds,
        "absolute_safety_margin": args.absolute_margin,
        "selected_layers": sorted(map(int, thresholds)),
        "source_plan": str(args.input.resolve()),
        "source_plan_file_sha256": source_hash,
        "source_plan_canonical_sha256": source.get("canonical_sha256"),
        "selection": source.get("selection"),
        "sources": source.get("sources"),
        "fallback": (
            "Use the configured adaptive 2/3/4-expert continuation policy when no "
            "layer threshold exists or the live top-gate gap is below the stricter threshold."
        ),
        "claim_boundary": (
            "Derived only from a previously frozen arithmetic/extraction development plan. "
            "The added uniform safety margin is conservative and was fixed before the next "
            "reasoning-family run. This is not a quality or speed result until that run passes."
        ),
    }
    report["canonical_sha256"] = canonical(report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "output": str(args.output),
        "absolute_safety_margin": args.absolute_margin,
        "canonical_sha256": report["canonical_sha256"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
