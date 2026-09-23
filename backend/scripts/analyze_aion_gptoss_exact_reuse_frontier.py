#!/usr/bin/env python3
"""Map exact GPT-OSS response expert reuse against additional resident bytes."""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from backend.scripts.analyze_aion_gptoss_family_cartridges import (
    GIB,
    expert_storage_sizes,
)


TARGETS = (0.50, 0.75, 0.90, 0.95)
CAPACITIES_GIB = (0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0)


def component_storage_sizes(manifest: dict) -> dict[tuple[int, int, str], int]:
    sizes: dict[tuple[int, int, str], int] = {}
    for region in manifest["regions"]:
        name = region["region_name"]
        if not name.startswith("blk.") or "_exps." not in name:
            continue
        parts = name.split(".")
        layer = int(parts[1])
        component = parts[2].removeprefix("ffn_") + "." + parts[3]
        for frame in region["frames"]:
            key = (layer, int(frame["expert"]), component)
            if key in sizes:
                raise ValueError(f"duplicate component frame {key}")
            sizes[key] = int(frame["raw_bytes"])
    if len(sizes) != 36 * 128 * 6 or any(value <= 0 for value in sizes.values()):
        raise ValueError("manifest does not contain a complete 36x128x6 component bank")
    return sizes


def load_pool(path: Path) -> set[tuple[int, int]]:
    pool = json.loads(path.read_text())
    layers = pool.get("layers", {})
    if set(layers) != {str(layer) for layer in range(36)}:
        raise ValueError("RAM pool does not cover all 36 layers")
    return {(layer, int(expert)) for layer in range(36)
            for expert in layers[str(layer)]}


def response_accesses(trace: dict, prompt_positions: int,
                      ram_pool: set[tuple[int, int]]) -> list[tuple[int, int]]:
    if (trace.get("status") != "PASSED" or trace.get("quality_track") is True
            or not trace.get("routes_repeatable")
            or not trace.get("final_hidden_and_logits_bitwise_repeatable")):
        raise ValueError("trace is not passed, exact and repeatable")
    tokens = trace["run_a"]["tokens"]
    if not 0 <= prompt_positions < len(tokens):
        raise ValueError("prompt position boundary is outside trace")
    accesses: list[tuple[int, int]] = []
    for token in tokens[prompt_positions:]:
        if len(token["layers"]) != 36:
            raise ValueError("trace token does not contain 36 layers")
        for expected_layer, observation in enumerate(token["layers"]):
            layer = int(observation["layer"])
            route = [int(expert) for expert in observation["route"]]
            if layer != expected_layer or len(route) != 4 or len(set(route)) != 4:
                raise ValueError("trace contains a non-exact route")
            accesses.extend((layer, expert) for expert in route
                            if (layer, expert) not in ram_pool)
    return accesses


def weighted_reuse_distances(accesses: list[tuple[int, int]], sizes: dict) -> list[int]:
    """Return unique intervening resident bytes for every repeated access."""
    stack: list[tuple[int, int]] = []
    positions: dict[tuple[int, int], int] = {}
    distances: list[int] = []
    for key in accesses:
        old = positions.get(key)
        if old is not None:
            distances.append(sum(sizes[item] for item in stack[old + 1:]))
            stack.pop(old)
        stack.append(key)
        positions = {item: index for index, item in enumerate(stack)}
    return distances


def percentile(values: list[int], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def retention_frontier(accesses: list, sizes: dict) -> dict:
    counts = collections.Counter(accesses)
    total = sum(sizes[key] * count for key, count in counts.items())
    first_touch = sum(sizes[key] for key in counts)
    ranked = sorted(counts, key=lambda key: (counts[key] - 1, sizes[key]), reverse=True)

    def selected_for(capacity: int) -> tuple[int, int, int]:
        used = avoided = entries = 0
        for key in ranked:
            size = sizes[key]
            if used + size > capacity:
                continue
            used += size
            avoided += max(0, counts[key] - 1) * size
            entries += 1
        return used, avoided, entries

    sweep = []
    for capacity_gib in CAPACITIES_GIB:
        used, avoided, entries = selected_for(int(capacity_gib * GIB))
        sweep.append({
            "capacity_gib": capacity_gib,
            "used_bytes": used,
            "entries": entries,
            "avoidable_delivery_bytes": avoided,
            "total_delivery_reduction_fraction": avoided / total if total else 0.0,
        })

    target_rows = {}
    for target in TARGETS:
        required = target * total
        used = avoided = entries = 0
        for key in ranked:
            if avoided >= required:
                break
            size = sizes[key]
            used += size
            avoided += max(0, counts[key] - 1) * size
            entries += 1
        target_rows[str(target)] = ({
            "resident_bytes": used,
            "resident_gib": used / GIB,
            "entries": entries,
            "avoided_bytes": avoided,
            "achieved_fraction": avoided / total,
        } if avoided >= required else None)

    return {
        "accesses": len(accesses),
        "unique_entries": len(counts),
        "total_delivery_bytes": total,
        "first_touch_floor_bytes": first_touch,
        "maximum_avoidable_repeat_bytes": total - first_touch,
        "maximum_avoidable_fraction": (total - first_touch) / total if total else 0.0,
        "capacity_sweep": sweep,
        "minimum_capacity_for_total_delivery_reduction": target_rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--family", action="append", required=True,
                        help="id:trace:pool:prompt_positions")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("refusing to overwrite evidence")
    manifest = json.loads(args.manifest.read_text())
    if manifest.get("status") != "COMPLETE_VERIFIED":
        raise SystemExit("warehouse manifest is not complete and verified")
    expert_sizes = expert_storage_sizes(manifest, "raw_bytes")
    component_sizes = component_storage_sizes(manifest)
    families = {}
    for declaration in args.family:
        family_id, trace_text, pool_text, prompt_text = declaration.split(":", 3)
        trace_path = Path(trace_text).resolve()
        pool_path = Path(pool_text).resolve()
        trace = json.loads(trace_path.read_text())
        pool = load_pool(pool_path)
        accesses = response_accesses(trace, int(prompt_text), pool)
        component_accesses = [
            (layer, expert, component)
            for layer, expert in accesses
            for component in (
                "down_exps.bias", "down_exps.weight",
                "gate_exps.bias", "gate_exps.weight",
                "up_exps.bias", "up_exps.weight",
            )
        ]
        reuse = weighted_reuse_distances(accesses, expert_sizes)
        families[family_id] = {
            "trace_path": str(trace_path),
            "trace_sha256": hashlib.sha256(trace_path.read_bytes()).hexdigest(),
            "trace_canonical_sha256": trace.get("canonical_sha256"),
            "pool_path": str(pool_path),
            "pool_sha256": hashlib.sha256(pool_path.read_bytes()).hexdigest(),
            "prompt_positions": int(prompt_text),
            "continuation_positions": len(trace["run_a"]["tokens"]) - int(prompt_text),
            "whole_expert": retention_frontier(accesses, expert_sizes),
            "component_granularity": retention_frontier(component_accesses, component_sizes),
            "weighted_reuse_distance_bytes": {
                "observations": len(reuse),
                "p50": percentile(reuse, 0.50),
                "p75": percentile(reuse, 0.75),
                "p90": percentile(reuse, 0.90),
                "p95": percentile(reuse, 0.95),
                "maximum": max(reuse) if reuse else None,
            },
        }
    result = {
        "schema": "aion.gptoss-120b-exact-response-reuse-frontier.v1",
        "status": "OFFLINE_ANALYSIS_COMPLETE",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": "GPT-OSS 120B Q4_K_M/MXFP4",
        "manifest_path": str(args.manifest.resolve()),
        "manifest_sha256": hashlib.sha256(args.manifest.read_bytes()).hexdigest(),
        "families": families,
        "claim_boundary": (
            "Offline frozen-trace capacity analysis after removing each existing exact RAM pool. "
            "Avoided bytes assume an admitted immutable entry remains resident and do not predict "
            "wall-time benefit or memory-pressure cost. Component-granularity rows require a future "
            "mixed-residency kernel and are not runtime evidence."
        ),
    }
    canonical = hashlib.sha256(json.dumps(result, sort_keys=True,
                                           separators=(",", ":")).encode()).hexdigest()
    result["canonical_sha256"] = canonical
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"canonical_sha256": canonical, "families": list(families),
                      "status": result["status"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
