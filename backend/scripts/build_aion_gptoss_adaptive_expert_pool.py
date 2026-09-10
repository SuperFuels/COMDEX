#!/usr/bin/env python3
"""Build a variable-width 120B pool that preserves an exact request prefix."""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from backend.scripts.run_aion_gptoss_route_cartridge_gate import (
    canonical_sha256,
    expert_sizes,
    extract_routes,
)


def _file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--required-prefix-report", type=Path, required=True)
    parser.add_argument("--required-prefix-tokens", type=int, required=True)
    parser.add_argument("--supplemental-report", action="append", type=Path, default=[])
    parser.add_argument("--capacity-gib", type=float, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("refusing to overwrite expert pool")
    manifest = json.loads(args.manifest.read_text())
    if manifest.get("status") != "COMPLETE_VERIFIED":
        raise SystemExit("warehouse is not complete and verified")
    _, raw_sizes = expert_sizes(manifest)
    prefix_report = json.loads(args.required_prefix_report.read_text())
    prefix_routes = extract_routes(prefix_report)
    if not 1 <= args.required_prefix_tokens <= len(prefix_routes):
        raise SystemExit("required prefix token count is invalid")
    required: set[tuple[int, int]] = {
        (layer, expert)
        for token in prefix_routes[:args.required_prefix_tokens]
        for layer, route in enumerate(token)
        for expert in route
    }
    capacity = int(args.capacity_gib * 1024 ** 3)
    required_bytes = sum(raw_sizes[key] for key in required)
    if required_bytes > capacity:
        raise SystemExit("required exact prefix exceeds pool capacity")
    frequency: collections.Counter[tuple[int, int]] = collections.Counter()
    source_paths = [args.required_prefix_report, *args.supplemental_report]
    sources = []
    for path in source_paths:
        report = json.loads(path.read_text())
        routes = extract_routes(report)
        used = (routes[:args.required_prefix_tokens]
                if path.resolve() == args.required_prefix_report.resolve() else routes)
        for token in used:
            for layer, route in enumerate(token):
                frequency.update((layer, expert) for expert in route)
        sources.append({"path": str(path.resolve()), "tokens_used": len(used),
                        "file_sha256": _file_sha(path),
                        "canonical_sha256": report.get("canonical_sha256")})
    selected = set(required)
    resident = required_bytes
    ranked = sorted((key for key in frequency if key not in selected), key=lambda key: (
        -(frequency[key] / raw_sizes[key]), -frequency[key], raw_sizes[key], key,
    ))
    for key in ranked:
        size = raw_sizes[key]
        if resident + size <= capacity:
            selected.add(key)
            resident += size
    layers = {str(layer): sorted(expert for chosen_layer, expert in selected
                                 if chosen_layer == layer) for layer in range(36)}
    if any(len(values) < 4 for values in layers.values()):
        raise SystemExit("adaptive pool left a layer with fewer than four experts")
    result = {
        "schema": "aion.gptoss-120b-constrained-expert-pool.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": "GPT-OSS 120B Q4_K_M/MXFP4",
        "quality_track": True,
        "selection": "all exact required-prefix routes, then observed frequency per raw byte",
        "capacity_bytes": capacity,
        "resident_raw_bytes": resident,
        "required_prefix_experts": len(required),
        "required_prefix_raw_bytes": required_bytes,
        "total_layer_experts": len(selected),
        "minimum_experts_per_layer": min(map(len, layers.values())),
        "maximum_experts_per_layer": max(map(len, layers.values())),
        "required_prefix": {"path": str(args.required_prefix_report.resolve()),
                            "tokens": args.required_prefix_tokens},
        "sources": sources,
        "warehouse_manifest_sha256": _file_sha(args.manifest),
        "layers": layers,
        "claim_boundary": (
            "All original expert routes observed during the declared request prefix are retained, "
            "but later routing is constrained to this bounded original-weight pool. This is a "
            "changed-model quality track, not unrestricted exact GPT-OSS 120B inference."
        ),
    }
    result["canonical_sha256"] = canonical_sha256(result)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: result[key] for key in (
        "resident_raw_bytes", "required_prefix_experts", "total_layer_experts",
        "minimum_experts_per_layer", "maximum_experts_per_layer", "canonical_sha256",
    )}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
