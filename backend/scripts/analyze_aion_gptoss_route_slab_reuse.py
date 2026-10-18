#!/usr/bin/env python3
"""Measure whether ordered GPT-OSS expert quartets justify prepared route slabs."""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from statistics import median


def canonical_sha256(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def extract_run_routes(report: dict, run_name: str,
                       route_prefix_width: int = 0) -> list[tuple[int, tuple[int, ...]]]:
    run = report.get(run_name)
    if not isinstance(run, dict):
        return []
    rows: list[tuple[int, tuple[int, ...]]] = []
    for token in run.get("tokens", []):
        if not isinstance(token, dict):
            continue
        for layer in token.get("layers", []):
            if not isinstance(layer, dict):
                continue
            route = layer.get("route")
            layer_id = layer.get("layer")
            if isinstance(layer_id, int) and isinstance(route, list) and route:
                selected = route[:route_prefix_width] if route_prefix_width else route
                rows.append((layer_id, tuple(int(expert) for expert in selected)))
    return rows


def summarize(routes: list[tuple[int, tuple[int, ...]]], touches: int,
              slab_bytes: int) -> dict:
    counts = Counter(routes)
    total = sum(counts.values())
    admitted = {key: count for key, count in counts.items() if count > touches}
    reusable = sum(count - touches for count in admitted.values())
    return {
        "route_occurrences": total,
        "unique_ordered_layer_routes": len(counts),
        "maximum_route_occurrences": max(counts.values(), default=0),
        "admitted_route_slabs": len(admitted),
        "post_admission_reuses": reusable,
        "post_admission_reuse_fraction": reusable / total if total else 0.0,
        "projected_route_slab_storage_bytes": len(admitted) * slab_bytes,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--admission-touches", type=int, default=3)
    parser.add_argument("--route-slab-bytes", type=int, default=53_015_264)
    parser.add_argument("--route-prefix-width", type=int, default=0)
    parser.add_argument("--minimum-reuse-fraction", type=float, default=0.10)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("refusing to overwrite evidence")
    if args.admission_touches < 1:
        raise SystemExit("admission touches must be positive")
    if args.route_prefix_width < 0:
        raise SystemExit("route prefix width cannot be negative")

    observations = []
    for path in args.report:
        report = json.loads(path.read_text())
        for run_name in ("run_a", "run_b"):
            routes = extract_run_routes(report, run_name, args.route_prefix_width)
            if routes:
                observations.append({
                    "source": str(path),
                    "source_file_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    "source_canonical_sha256": report.get("canonical_sha256"),
                    "source_status": report.get("status"),
                    "run": run_name,
                    **summarize(routes, args.admission_touches, args.route_slab_bytes),
                })
    if not observations:
        raise SystemExit("no token-layer routes found")

    reuse_fractions = [row["post_admission_reuse_fraction"] for row in observations]
    passed = all(value >= args.minimum_reuse_fraction for value in reuse_fractions)
    result = {
        "schema": "aion.gptoss-120b-route-slab-reuse-bound.v1",
        "status": (
            "ADVANCE_ROUTE_SLAB_MICROGATE"
            if passed else "STOP_ROUTE_SLAB_FOR_MEASURED_COHORT"
        ),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "admission_touches": args.admission_touches,
        "route_slab_bytes": args.route_slab_bytes,
        "route_prefix_width": args.route_prefix_width,
        "minimum_reuse_fraction": args.minimum_reuse_fraction,
        "median_post_admission_reuse_fraction": median(reuse_fractions),
        "minimum_post_admission_reuse_fraction": min(reuse_fractions),
        "observations": observations,
        "claim_boundary": (
            "This is an offline upper-bound screen over ordered layer/expert route "
            "prefixes (or complete routes when prefix width is zero). "
            "It charges slab storage but not construction, verification, delivery, "
            "kernel dispatch or eviction. It is not generated-token speed evidence."
        ),
    }
    result["canonical_sha256"] = canonical_sha256(result)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "status": result["status"],
        "median_post_admission_reuse_fraction": result[
            "median_post_admission_reuse_fraction"
        ],
        "minimum_post_admission_reuse_fraction": result[
            "minimum_post_admission_reuse_fraction"
        ],
        "canonical_sha256": result["canonical_sha256"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
