#!/usr/bin/env python3
"""Measure training expert-route coverage without changing frozen splits."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from datetime import datetime, timezone
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("refusing to overwrite evidence")
    manifest = json.loads(args.manifest.read_text())
    split = {family: name for name, families in manifest["family_disjoint_split"].items()
             for family in families}
    rows = [(family["family_id"], split[family["family_id"]], record["layer"],
             set(record["route"])) for family in manifest["families"] for record in family["records"]]
    observations = []
    for family, split_name, layer, route in rows:
        if split_name not in ("numerical_holdout", "semantic_holdout"):
            continue
        train_routes = [other for _, other_split, other_layer, other in rows
                        if other_split == "train" and other_layer == layer]
        overlaps = [len(route & other) for other in train_routes]
        ever_seen = sum(expert in set().union(*train_routes) for expert in route)
        observations.append({"family_id": family, "split": split_name, "layer": layer,
                             "best_single_route_overlap": max(overlaps),
                             "experts_ever_seen_in_training": ever_seen})
    best = [row["best_single_route_overlap"] for row in observations]
    report = {
        "schema": "aion.shadow-expert-route-coverage.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "manifest_canonical_sha256": manifest["canonical_sha256"],
        "summary": {"holdout_rows": len(observations),
                    "best_single_route_overlap_p50": statistics.median(best),
                    "best_single_route_overlap_min": min(best),
                    "rows_with_all_four_experts_ever_seen": sum(
                        row["experts_ever_seen_in_training"] == 4 for row in observations),
                    "rows_with_zero_route_overlap": sum(value == 0 for value in best)},
        "observations": observations,
        "claim_boundary": "Descriptive coverage audit only; holdout targets are not used for fitting.",
    }
    body = json.dumps(report, sort_keys=True, separators=(",", ":"))
    report["canonical_sha256"] = hashlib.sha256(body.encode()).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({**report["summary"], "canonical_sha256": report["canonical_sha256"]},
                     sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
