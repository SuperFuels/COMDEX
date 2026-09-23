#!/usr/bin/env python3
"""Estimate whether per-layer exception quotas can beat the global exact halo."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path

from backend.scripts.run_aion_gptoss_route_cartridge_gate import (
    canonical_sha256,
    expert_sizes,
    extract_routes,
)


def simulate(sequence: list[int], capacity: int, compressed: dict[int, int]) -> dict:
    cache: OrderedDict[int, None] = OrderedDict()
    faults = hits = encoded = 0
    for expert in sequence:
        if expert in cache:
            hits += 1
            cache.move_to_end(expert)
            continue
        faults += 1
        encoded += compressed[expert]
        if capacity:
            while len(cache) >= capacity:
                cache.popitem(last=False)
            cache[expert] = None
    return {"faults": faults, "hits": hits, "compressed_bytes": encoded}


def optimize(curves: list[list[dict]], slots: int) -> tuple[list[int], int]:
    infinity = 10 ** 30
    costs = [0] + [infinity] * slots
    choices: list[list[int]] = []
    for curve in curves:
        next_costs = [infinity] * (slots + 1)
        selected = [0] * (slots + 1)
        for used in range(slots + 1):
            for quota, point in enumerate(curve[:slots - used + 1]):
                value = costs[used] + point["compressed_bytes"]
                target = used + quota
                if value < next_costs[target]:
                    next_costs[target] = value
                    selected[target] = quota
        costs = next_costs
        choices.append(selected)
    used = min(range(slots + 1), key=lambda value: costs[value])
    allocation = [0] * len(curves)
    for layer in range(len(curves) - 1, -1, -1):
        quota = choices[layer][used]
        allocation[layer] = quota
        used -= quota
    return allocation, min(costs)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--trace", type=Path, required=True)
    parser.add_argument("--core-pool", type=Path, required=True)
    parser.add_argument("--halo-gib", type=float, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("refusing to overwrite analysis")
    manifest = json.loads(args.manifest.read_text())
    trace = json.loads(args.trace.read_text())
    core = json.loads(args.core_pool.read_text())
    compressed, raw = expert_sizes(manifest)
    raw_sizes = set(raw.values())
    if len(raw_sizes) != 1:
        raise SystemExit("per-layer slot analysis requires equal raw expert sizes")
    slot_bytes = raw_sizes.pop()
    slots = int(args.halo_gib * 1024 ** 3) // slot_bytes
    routes = extract_routes(trace)
    sequences: list[list[int]] = [[] for _ in range(36)]
    cores = {layer: set(core["layers"][str(layer)]) for layer in range(36)}
    for token in routes:
        for layer, experts in enumerate(token):
            sequences[layer].extend(expert for expert in experts if expert not in cores[layer])
    curves = []
    for layer, sequence in enumerate(sequences):
        weights = {expert: compressed[(layer, expert)] for expert in set(sequence)}
        curves.append([simulate(sequence, quota, weights)
                       for quota in range(min(slots, len(weights)) + 1)])
    allocation, predicted_bytes = optimize(curves, slots)
    uniform_base, remainder = divmod(slots, 36)
    uniform = [uniform_base + (layer < remainder) for layer in range(36)]
    result = {
        "schema": "aion.gptoss-120b-per-layer-halo-analysis.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": "GPT-OSS 120B Q4_K_M/MXFP4",
        "trace_path": str(args.trace.resolve()),
        "trace_file_sha256": hashlib.sha256(args.trace.read_bytes()).hexdigest(),
        "core_pool_path": str(args.core_pool.resolve()),
        "core_pool_canonical_sha256": core["canonical_sha256"],
        "halo_capacity_bytes": slots * slot_bytes,
        "halo_slots": slots,
        "slot_bytes": slot_bytes,
        "optimized_slots_per_layer": allocation,
        "optimized_total_slots": sum(allocation),
        "optimized": {
            "faults": sum(curves[layer][quota]["faults"]
                          for layer, quota in enumerate(allocation)),
            "hits": sum(curves[layer][quota]["hits"]
                        for layer, quota in enumerate(allocation)),
            "compressed_bytes": predicted_bytes,
        },
        "uniform_slots_per_layer": uniform,
        "uniform": {
            key: sum(curves[layer][quota][key] for layer, quota in enumerate(uniform))
            for key in ("faults", "hits", "compressed_bytes")
        },
        "no_halo": {
            key: sum(curves[layer][0][key] for layer in range(36))
            for key in ("faults", "hits", "compressed_bytes")
        },
        "claim_boundary": (
            "This is a same-trace offline LRU allocation analysis, not runtime speed evidence. "
            "Its optimized allocation is trace-fitted and requires a separate held-out exact run."
        ),
    }
    result["canonical_sha256"] = canonical_sha256(result)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: result[key] for key in (
        "halo_slots", "optimized_total_slots", "no_halo", "uniform", "optimized",
        "canonical_sha256",
    )}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
