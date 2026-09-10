#!/usr/bin/env python3
"""Offline exact-route analysis for physical GPT-OSS family cartridges."""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


GIB = 1024 ** 3


def expert_storage_sizes(manifest: dict, field: str) -> dict[tuple[int, int], int]:
    sizes: dict[tuple[int, int], int] = collections.defaultdict(int)
    for region in manifest["regions"]:
        name = region["region_name"]
        if not name.startswith("blk.") or "_exps." not in name:
            continue
        parts = name.split(".")
        layer = int(parts[1])
        for frame in region["frames"]:
            sizes[(layer, int(frame["expert"]))] += int(frame[field])
    if len(sizes) != 36 * 128 or any(value <= 0 for value in sizes.values()):
        raise ValueError("manifest does not contain a complete 36x128 expert bank")
    return dict(sizes)


def expert_sizes(manifest: dict) -> dict[tuple[int, int], int]:
    return expert_storage_sizes(manifest, "raw_bytes")


def trace_accesses(trace: dict) -> list[tuple[int, int]]:
    if (trace.get("status") != "PASSED" or trace.get("quality_track") is True
            or not trace.get("routes_repeatable")):
        raise ValueError("trace is not an exact repeatable passed route source")
    tokens = trace.get("run_a", {}).get("tokens", [])
    accesses: list[tuple[int, int]] = []
    for token in tokens:
        layers = token.get("layers", [])
        if len(layers) != 36:
            raise ValueError("trace token does not cover all 36 layers")
        for expected_layer, observation in enumerate(layers):
            layer = int(observation["layer"])
            route = [int(value) for value in observation["route"]]
            if layer != expected_layer or len(route) != 4 or len(set(route)) != 4:
                raise ValueError("trace contains an invalid unrestricted route")
            accesses.extend((layer, expert) for expert in route)
    if not accesses:
        raise ValueError("trace contains no expert accesses")
    return accesses


def select_within_budget(ranked: Iterable[tuple[int, int]], sizes: dict,
                         budget: int) -> set[tuple[int, int]]:
    selected: set[tuple[int, int]] = set()
    used = 0
    for key in ranked:
        size = sizes[key]
        if used + size <= budget:
            selected.add(key)
            used += size
    return selected


def simulate(accesses: list[tuple[int, int]], sizes: dict,
             fixed: set[tuple[int, int]], halo_budget: int,
             compressed_sizes: dict | None = None) -> dict:
    halo: OrderedDict[tuple[int, int], int] = OrderedDict()
    halo_bytes = hits = misses = miss_bytes = miss_compressed_bytes = 0
    for key in accesses:
        if key in fixed:
            hits += 1
            continue
        size = sizes[key]
        resident = halo.pop(key, None)
        if resident is not None:
            hits += 1
            halo[key] = resident
            continue
        misses += 1
        miss_bytes += size
        if compressed_sizes is not None:
            miss_compressed_bytes += compressed_sizes[key]
        if size > halo_budget:
            continue
        while halo and halo_bytes + size > halo_budget:
            _, removed = halo.popitem(last=False)
            halo_bytes -= removed
        halo[key] = size
        halo_bytes += size
    total = hits + misses
    return {
        "accesses": total,
        "hits": hits,
        "misses": misses,
        "hit_rate": hits / total,
        "miss_raw_bytes": miss_bytes,
        "miss_compressed_bytes": miss_compressed_bytes,
        "final_halo_bytes": halo_bytes,
    }


def bytes_for(keys: set[tuple[int, int]], sizes: dict) -> int:
    return sum(sizes[key] for key in keys)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--family", action="append", required=True,
                        help="id:kind:path where kind is semantic or stress")
    parser.add_argument("--ram-pool", action="append", default=[],
                        help="family_id:path for an already-protected exact RAM pool")
    parser.add_argument("--capacities-gib", default="20,25,30")
    parser.add_argument("--ram-hotset-gib", type=float, default=1.5)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("refusing to overwrite evidence")
    manifest = json.loads(args.manifest.read_text())
    if manifest.get("status") != "COMPLETE_VERIFIED":
        raise SystemExit("warehouse manifest is not complete and verified")
    sizes = expert_sizes(manifest)
    compressed_sizes = expert_storage_sizes(manifest, "compressed_bytes")
    families = {}
    for declaration in args.family:
        family_id, kind, path_text = declaration.split(":", 2)
        if kind not in {"semantic", "stress"} or family_id in families:
            raise SystemExit("family declarations require unique id:semantic|stress:path")
        path = Path(path_text).resolve()
        trace = json.loads(path.read_text())
        accesses = trace_accesses(trace)
        families[family_id] = {
            "kind": kind, "path": path, "trace": trace,
            "accesses": accesses, "counts": collections.Counter(accesses),
            "unique": set(accesses),
        }
    ram_pools = {}
    for declaration in args.ram_pool:
        family_id, path_text = declaration.split(":", 1)
        if family_id not in families or family_id in ram_pools:
            raise SystemExit("RAM pool must reference one declared family exactly once")
        path = Path(path_text).resolve()
        pool = json.loads(path.read_text())
        layers = pool.get("layers", {})
        if set(layers) != {str(layer) for layer in range(36)}:
            raise SystemExit("RAM pool does not cover all 36 layers")
        keys = {(layer, int(expert)) for layer in range(36)
                for expert in layers[str(layer)]}
        ram_pools[family_id] = {"path": path, "keys": keys}
    for family_id, family in families.items():
        ram = ram_pools.get(family_id, {}).get("keys", set())
        family["all_accesses"] = family["accesses"]
        family["ram_pool"] = ram
        family["ram_hits"] = sum(key in ram for key in family["all_accesses"])
        family["accesses"] = [key for key in family["all_accesses"] if key not in ram]
        family["counts"] = collections.Counter(family["accesses"])
        family["unique"] = set(family["accesses"])
    presence = collections.Counter(
        key for family in families.values() for key in family["unique"])
    aggregate = collections.Counter(
        key for family in families.values() for key in family["accesses"])
    semantic_presence = collections.Counter(
        key for family in families.values() if family["kind"] == "semantic"
        for key in family["unique"])
    semantic_aggregate = collections.Counter(
        key for family in families.values() if family["kind"] == "semantic"
        for key in family["accesses"])
    global_rank = sorted(
        aggregate,
        key=lambda key: (
            semantic_presence[key], presence[key],
            semantic_aggregate[key] / sizes[key], aggregate[key] / sizes[key],
            semantic_aggregate[key], aggregate[key], -sizes[key],
        ),
        reverse=True,
    )
    capacities = [float(value) for value in args.capacities_gib.split(",")]
    candidates = []
    for capacity_gib in capacities:
        capacity = int(capacity_gib * GIB)
        for core_gib in (0, 2, 4, 6, 8, 10):
            for halo_gib in (1, 2, 4, 6):
                core_budget = int(core_gib * GIB)
                halo_budget = int(halo_gib * GIB)
                if core_budget + halo_budget >= capacity:
                    continue
                core = select_within_budget(global_rank, sizes, core_budget)
                segment_budget = capacity - bytes_for(core, sizes) - halo_budget
                rows = {}
                for family_id, family in families.items():
                    family_rank = sorted(
                        (key for key in family["counts"] if key not in core),
                        key=lambda key: (family["counts"][key] / sizes[key],
                                         family["counts"][key], -sizes[key]),
                        reverse=True,
                    )
                    segment = select_within_budget(family_rank, sizes, segment_budget)
                    fixed = core | segment
                    rows[family_id] = {
                        "kind": family["kind"],
                        "unique_experts": len(family["unique"]),
                        "unique_raw_bytes": bytes_for(family["unique"], sizes),
                        "core_covered_unique": len(family["unique"] & core),
                        "cartridge_entries": len(segment),
                        "cartridge_raw_bytes": bytes_for(segment, sizes),
                        "cartridge_compressed_bytes": bytes_for(segment, compressed_sizes),
                        "ram_pool_raw_bytes": bytes_for(family["ram_pool"], sizes),
                        "ram_pool_compressed_bytes": bytes_for(
                            family["ram_pool"], compressed_sizes),
                        "switch_stage_raw_bytes": (
                            bytes_for(segment, sizes) + bytes_for(family["ram_pool"], sizes)
                        ),
                        "switch_stage_compressed_bytes": (
                            bytes_for(segment, compressed_sizes)
                            + bytes_for(family["ram_pool"], compressed_sizes)
                        ),
                        "cold_core_plus_cartridge_bytes": bytes_for(fixed, sizes),
                        **simulate(family["accesses"], sizes, fixed, halo_budget,
                                   compressed_sizes),
                    }
                    rows[family_id]["overall_physical_hit_rate"] = (
                        family["ram_hits"] + rows[family_id]["hits"]
                    ) / len(family["all_accesses"])
                    rows[family_id]["ram_pool_hits"] = family["ram_hits"]
                    rows[family_id]["total_model_accesses"] = len(family["all_accesses"])
                semantic = [row for row in rows.values() if row["kind"] == "semantic"]
                all_rows = list(rows.values())
                candidates.append({
                    "capacity_gib": capacity_gib,
                    "core_budget_gib": core_gib,
                    "halo_budget_gib": halo_gib,
                    "actual_core_bytes": bytes_for(core, sizes),
                    "core_entries": len(core),
                    "family_segment_budget_bytes": segment_budget,
                    "semantic_min_hit_rate": min(row["hit_rate"] for row in semantic),
                    "semantic_mean_hit_rate": sum(row["hit_rate"] for row in semantic) / len(semantic),
                    "all_min_hit_rate": min(row["hit_rate"] for row in all_rows),
                    "all_mean_hit_rate": sum(row["hit_rate"] for row in all_rows) / len(all_rows),
                    "mean_miss_raw_bytes": sum(row["miss_raw_bytes"] for row in all_rows) / len(all_rows),
                    "mean_cartridge_raw_bytes": sum(row["cartridge_raw_bytes"] for row in all_rows) / len(all_rows),
                    "mean_switch_stage_raw_bytes": sum(row["switch_stage_raw_bytes"] for row in all_rows) / len(all_rows),
                    "mean_switch_stage_compressed_bytes": sum(
                        row["switch_stage_compressed_bytes"] for row in all_rows
                    ) / len(all_rows),
                    "families": rows,
                })
    def recommend(rows):
        viable = [row for row in rows if row["semantic_min_hit_rate"] >= 0.95]
        if viable:
            return min(viable, key=lambda row: (
                row["mean_miss_raw_bytes"], row["capacity_gib"],
                row["mean_cartridge_raw_bytes"],
                -row["all_min_hit_rate"], -row["semantic_mean_hit_rate"],
                -row["halo_budget_gib"],
            ))
        return max(rows, key=lambda row: (
            row["semantic_min_hit_rate"], row["all_min_hit_rate"],
            row["semantic_mean_hit_rate"], -row["mean_miss_raw_bytes"],
        ))
    recommended_by_capacity = {
        str(capacity): recommend([row for row in candidates
                                  if row["capacity_gib"] == capacity])
        for capacity in capacities
    }
    recommended = recommend(candidates)
    def materialize_plan(row):
        core = select_within_budget(
            global_rank, sizes, int(row["core_budget_gib"] * GIB))
        segment_budget = int(row["capacity_gib"] * GIB) - bytes_for(core, sizes) \
            - int(row["halo_budget_gib"] * GIB)
        cartridges = {}
        ram_hotsets = {}
        for family_id, family in families.items():
            ranking = sorted(
                (key for key in family["counts"] if key not in core),
                key=lambda key: (family["counts"][key] / sizes[key],
                                 family["counts"][key], -sizes[key]),
                reverse=True,
            )
            selected = select_within_budget(ranking, sizes, segment_budget)
            cartridges[family_id] = [
                {"layer": key[0], "expert": key[1], "raw_bytes": sizes[key],
                 "compressed_bytes": compressed_sizes[key]}
                for key in sorted(selected)
            ]
            hot_rank = sorted(
                family["counts"],
                key=lambda key: (
                    max(family["counts"][key] - 1, 0) / sizes[key],
                    family["counts"][key], -sizes[key]),
                reverse=True,
            )
            hot = select_within_budget(
                hot_rank, sizes, int(args.ram_hotset_gib * GIB))
            ram_hotsets[family_id] = {
                "budget_gib": args.ram_hotset_gib,
                "entries": [
                    {"layer": key[0], "expert": key[1], "raw_bytes": sizes[key],
                     "compressed_bytes": compressed_sizes[key],
                     "observed_accesses": family["counts"][key]}
                    for key in sorted(hot)
                ],
                "raw_bytes": bytes_for(hot, sizes),
                "observed_future_hits": sum(
                    max(family["counts"][key] - 1, 0) for key in hot),
                "observed_avoided_l2_raw_bytes": sum(
                    max(family["counts"][key] - 1, 0) * sizes[key]
                    for key in hot),
            }
        return {
            "capacity_gib": row["capacity_gib"],
            "core_budget_gib": row["core_budget_gib"],
            "halo_budget_gib": row["halo_budget_gib"],
            "core": [{"layer": key[0], "expert": key[1], "raw_bytes": sizes[key],
                      "compressed_bytes": compressed_sizes[key]}
                     for key in sorted(core)],
            "cartridges": cartridges,
            "ram_hotsets": ram_hotsets,
        }
    recommended_plan = materialize_plan(recommended)
    sets = [family["unique"] for family in families.values()]
    union = set().union(*sets)
    family_summary = {}
    for family_id, family in families.items():
        others = set().union(*(value["unique"] for key, value in families.items()
                               if key != family_id))
        family_summary[family_id] = {
            "kind": family["kind"],
            "trace_path": str(family["path"]),
            "trace_sha256": hashlib.sha256(family["path"].read_bytes()).hexdigest(),
            "trace_canonical_sha256": family["trace"].get("canonical_sha256"),
            "positions": len(family["trace"]["run_a"]["tokens"]),
            "total_model_accesses": len(family["all_accesses"]),
            "ram_pool_hits": family["ram_hits"],
            "ram_pool_entries": len(family["ram_pool"]),
            "ram_pool_raw_bytes": bytes_for(family["ram_pool"], sizes),
            "ram_pool_compressed_bytes": bytes_for(
                family["ram_pool"], compressed_sizes),
            "ram_pool_path": (str(ram_pools[family_id]["path"])
                              if family_id in ram_pools else None),
            "l2_accesses": len(family["accesses"]),
            "unique_experts": len(family["unique"]),
            "unique_raw_bytes": bytes_for(family["unique"], sizes),
            "unique_to_family_experts": len(family["unique"] - others),
            "unique_to_family_raw_bytes": bytes_for(family["unique"] - others, sizes),
        }
    result = {
        "schema": "aion.gptoss-120b-exact-family-cartridge-analysis.v1",
        "status": "OFFLINE_ANALYSIS_COMPLETE",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": "GPT-OSS 120B Q4_K_M/MXFP4",
        "manifest_path": str(args.manifest.resolve()),
        "manifest_sha256": hashlib.sha256(args.manifest.read_bytes()).hexdigest(),
        "family_count": len(families),
        "semantic_family_count": sum(value["kind"] == "semantic" for value in families.values()),
        "stress_family_count": sum(value["kind"] == "stress" for value in families.values()),
        "families": family_summary,
        "union_experts": len(union),
        "union_raw_bytes": bytes_for(union, sizes),
        "union_definition": "L2-demand experts after removing each semantic family's active RAM pool",
        "all_family_intersection_experts": len(set.intersection(*sets)),
        "all_family_intersection_raw_bytes": bytes_for(set.intersection(*sets), sizes),
        "experts_by_family_presence": {
            str(count): sum(value == count for value in presence.values())
            for count in range(1, len(families) + 1)
        },
        "candidate_count": len(candidates),
        "recommended": recommended,
        "recommended_plan": recommended_plan,
        "recommended_by_capacity": recommended_by_capacity,
        "all_candidates": candidates,
        "claim_boundary": (
            "Offline physical-cache analysis over two semantic exact traces and synthetic "
            "route-diversity stress traces. It changes no model computation and proves no "
            "runtime speed. Cartridge bytes are a cold/switch cost; predicted warm hit rate "
            "must be validated on family-disjoint complete generation before promotion."
        ),
    }
    body = json.dumps(result, sort_keys=True, separators=(",", ":"))
    result["canonical_sha256"] = hashlib.sha256(body.encode()).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "status": result["status"], "family_count": len(families),
        "union_gib": result["union_raw_bytes"] / GIB,
        "recommended": {key: recommended[key] for key in (
            "capacity_gib", "core_budget_gib", "halo_budget_gib",
            "semantic_min_hit_rate", "all_min_hit_rate", "all_mean_hit_rate")},
        "canonical_sha256": result["canonical_sha256"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
