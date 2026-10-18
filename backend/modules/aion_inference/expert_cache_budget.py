"""Deterministic memory-budget planning for reuse-aware MoE expert caches."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Sequence


Route = tuple[int, ...]
RouteBatch = tuple[Route, ...]


@dataclass(frozen=True)
class ExpertCacheBudgetPlan:
    capacities_by_layer: tuple[int, ...]
    total_capacity: int
    predicted_demand_bytes: int
    uniform_capacity: int
    uniform_predicted_demand_bytes: int
    predicted_byte_reduction_percent: float
    plan_sha256: str


@dataclass(frozen=True)
class ExpertCacheMemoryPlan:
    """A cache allocation selected under an explicit resident-byte ceiling."""

    capacities_by_layer: tuple[int, ...]
    maximum_resident_bytes: int
    estimated_resident_bytes: int
    predicted_demand_bytes: int
    uniform_capacity: int
    uniform_estimated_resident_bytes: int
    uniform_predicted_demand_bytes: int
    predicted_byte_reduction_percent: float
    plan_sha256: str


def verify_promoted_expert_cache_plan(
    document: dict[str, Any],
    *,
    expected_model_config_sha256: str | None = None,
    expected_shard_manifest_sha256: str | None = None,
    expected_pack_manifest_sha256: str | None = None,
) -> tuple[int, ...]:
    """Fail closed unless a promoted cache plan and its bindings are intact."""
    if document.get("schema_version") != "aion.promoted_expert_cache_plan.v1":
        raise ValueError("unsupported promoted cache plan schema")
    claimed = document.get("artifact_sha256")
    payload = {key: value for key, value in document.items() if key != "artifact_sha256"}
    observed = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    if claimed != observed:
        raise ValueError("promoted cache plan hash mismatch")
    integrity = document.get("integrity")
    if not isinstance(integrity, dict) or not integrity or not all(integrity.values()):
        raise ValueError("promoted cache plan integrity gate failed")
    capacities = tuple(int(value) for value in document.get("capacities_by_layer", ()))
    layers = int(document.get("architecture", {}).get("layers", 0))
    experts_per_layer = int(document.get("architecture", {}).get("experts_per_layer", 0))
    if len(capacities) != layers or any(value < 0 or value > experts_per_layer for value in capacities):
        raise ValueError("promoted cache plan capacities invalid")
    if sum(capacities) != int(document.get("total_capacity", -1)):
        raise ValueError("promoted cache plan total mismatch")
    bindings = document.get("bindings", {})
    expected = {
        "model_config_sha256": expected_model_config_sha256,
        "shard_manifest_sha256": expected_shard_manifest_sha256,
        "pack_manifest_sha256": expected_pack_manifest_sha256,
    }
    for name, value in expected.items():
        if value is not None and bindings.get(name) != value:
            raise ValueError(f"promoted cache plan {name} binding mismatch")
    return capacities


def simulate_frequency_cache_demand_bytes(
    route_batches: Sequence[RouteBatch],
    entries: dict[int, dict[str, Any]],
    capacity: int,
) -> int:
    """Replay the runtime's bounded LFU/recency policy without loading tensors."""
    if capacity < 0 or capacity > len(entries):
        raise ValueError("capacity outside layer expert range")
    retained: set[int] = set()
    counts: dict[int, int] = {}
    last_used: dict[int, int] = {}
    clock = 0
    demand_bytes = 0
    for batch in route_batches:
        required = {expert for route in batch for expert in route}
        unknown = required.difference(entries)
        if unknown:
            raise ValueError(f"route references unknown experts: {sorted(unknown)}")
        demand_bytes += sum(int(entries[expert]["bytes"]) for expert in required - retained)
        for route in batch:
            clock += 1
            for expert in route:
                counts[expert] = counts.get(expert, 0) + 1
                last_used[expert] = clock
        available = retained | required
        ranked = sorted(
            available,
            key=lambda expert: (counts.get(expert, 0), last_used.get(expert, 0), -expert),
            reverse=True,
        )
        retained = set(ranked[:capacity])
    return demand_bytes


def optimize_expert_cache_budget(
    route_batches_by_layer: Sequence[Sequence[RouteBatch]],
    entries_by_layer: Sequence[dict[int, dict[str, Any]]],
    *,
    total_capacity: int,
) -> ExpertCacheBudgetPlan:
    """Allocate a global expert-slot budget to minimize replayed demand bytes."""
    if len(route_batches_by_layer) != len(entries_by_layer) or not entries_by_layer:
        raise ValueError("route and entry layers must be non-empty and aligned")
    maximum = sum(len(entries) for entries in entries_by_layer)
    if total_capacity < 0 or total_capacity > maximum:
        raise ValueError("total_capacity outside model expert range")

    costs = [
        [simulate_frequency_cache_demand_bytes(batches, entries, capacity)
         for capacity in range(len(entries) + 1)]
        for batches, entries in zip(route_batches_by_layer, entries_by_layer, strict=True)
    ]
    infinity = 10**30
    previous = [infinity] * (total_capacity + 1)
    previous[0] = 0
    choices: list[list[int]] = []
    for layer_costs in costs:
        current = [infinity] * (total_capacity + 1)
        layer_choices = [-1] * (total_capacity + 1)
        for used_before, prior_cost in enumerate(previous):
            if prior_cost == infinity:
                continue
            for capacity, cost in enumerate(layer_costs):
                used = used_before + capacity
                if used > total_capacity:
                    break
                candidate = prior_cost + cost
                if candidate < current[used]:
                    current[used] = candidate
                    layer_choices[used] = capacity
        previous = current
        choices.append(layer_choices)
    if previous[total_capacity] == infinity:
        raise RuntimeError("cache budget allocation failed")

    capacities = [0] * len(costs)
    remaining = total_capacity
    for layer in range(len(costs) - 1, -1, -1):
        capacity = choices[layer][remaining]
        if capacity < 0:
            raise RuntimeError("cache budget reconstruction failed")
        capacities[layer] = capacity
        remaining -= capacity

    uniform_capacity = total_capacity // len(costs)
    uniform_bytes = sum(
        layer_costs[min(uniform_capacity, len(layer_costs) - 1)] for layer_costs in costs
    )
    predicted_bytes = previous[total_capacity]
    payload = {
        "capacities_by_layer": capacities,
        "total_capacity": total_capacity,
        "predicted_demand_bytes": predicted_bytes,
        "uniform_capacity": uniform_capacity,
        "uniform_predicted_demand_bytes": uniform_bytes,
    }
    plan_sha256 = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return ExpertCacheBudgetPlan(
        capacities_by_layer=tuple(capacities),
        total_capacity=total_capacity,
        predicted_demand_bytes=predicted_bytes,
        uniform_capacity=uniform_capacity,
        uniform_predicted_demand_bytes=uniform_bytes,
        predicted_byte_reduction_percent=(
            100.0 * (1.0 - predicted_bytes / uniform_bytes) if uniform_bytes else 0.0
        ),
        plan_sha256=plan_sha256,
    )


def optimize_expert_cache_memory_budget(
    route_batches_by_layer: Sequence[Sequence[RouteBatch]],
    entries_by_layer: Sequence[dict[int, dict[str, Any]]],
    *,
    maximum_resident_bytes: int,
) -> ExpertCacheMemoryPlan:
    """Minimize replayed demand under a fail-closed resident-byte budget.

    A retained slot is charged at the largest serialized expert in its layer.
    This is deliberately conservative: the chosen allocation cannot exceed the
    declared ceiling even when experts in a layer have different sizes.  The
    dynamic program keeps only non-dominated memory/demand states, avoiding a
    byte-sized DP table while preserving the exact optimum over layer capacities.
    """
    if len(route_batches_by_layer) != len(entries_by_layer) or not entries_by_layer:
        raise ValueError("route and entry layers must be non-empty and aligned")
    if maximum_resident_bytes < 0:
        raise ValueError("maximum_resident_bytes must be non-negative")
    if any(not entries for entries in entries_by_layer):
        raise ValueError("every layer must contain expert entries")

    slot_bytes = tuple(
        max(int(entry["bytes"]) for entry in entries.values())
        for entries in entries_by_layer
    )
    if any(value <= 0 for value in slot_bytes):
        raise ValueError("expert byte sizes must be positive")
    costs = [
        [
            simulate_frequency_cache_demand_bytes(batches, entries, capacity)
            for capacity in range(len(entries) + 1)
        ]
        for batches, entries in zip(route_batches_by_layer, entries_by_layer, strict=True)
    ]

    # resident bytes -> (demand bytes, capacities).  Equal-cost ties resolve to
    # lexicographically smaller capacities so artifacts are reproducible.
    states: dict[int, tuple[int, tuple[int, ...]]] = {0: (0, ())}
    for layer, (layer_costs, bytes_per_slot) in enumerate(zip(costs, slot_bytes, strict=True)):
        candidates: dict[int, tuple[int, tuple[int, ...]]] = {}
        for used_before, (demand_before, capacities_before) in states.items():
            for capacity, demand in enumerate(layer_costs):
                used = used_before + capacity * bytes_per_slot
                if used > maximum_resident_bytes:
                    break
                candidate = (demand_before + demand, capacities_before + (capacity,))
                incumbent = candidates.get(used)
                if incumbent is None or candidate < incumbent:
                    candidates[used] = candidate
        if not candidates:
            raise RuntimeError(f"memory-budget allocation failed at layer {layer}")

        # A state is dominated when an equal-or-smaller resident footprint has
        # no greater demand.  Retain only the strict demand frontier.
        states = {}
        best_demand: int | None = None
        for used, candidate in sorted(candidates.items()):
            demand, _ = candidate
            if best_demand is None or demand < best_demand:
                states[used] = candidate
                best_demand = demand

    estimated_resident_bytes, (predicted_bytes, capacities) = min(
        states.items(), key=lambda item: (item[1][0], item[0], item[1][1])
    )

    uniform_capacity = 0
    for capacity in range(min(len(entries) for entries in entries_by_layer) + 1):
        resident = sum(capacity * value for value in slot_bytes)
        if resident > maximum_resident_bytes:
            break
        uniform_capacity = capacity
    uniform_estimated = sum(uniform_capacity * value for value in slot_bytes)
    uniform_predicted = sum(
        layer_costs[uniform_capacity] for layer_costs in costs
    )
    payload = {
        "capacities_by_layer": capacities,
        "maximum_resident_bytes": maximum_resident_bytes,
        "estimated_resident_bytes": estimated_resident_bytes,
        "predicted_demand_bytes": predicted_bytes,
        "uniform_capacity": uniform_capacity,
        "uniform_estimated_resident_bytes": uniform_estimated,
        "uniform_predicted_demand_bytes": uniform_predicted,
    }
    plan_sha256 = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return ExpertCacheMemoryPlan(
        capacities_by_layer=capacities,
        maximum_resident_bytes=maximum_resident_bytes,
        estimated_resident_bytes=estimated_resident_bytes,
        predicted_demand_bytes=predicted_bytes,
        uniform_capacity=uniform_capacity,
        uniform_estimated_resident_bytes=uniform_estimated,
        uniform_predicted_demand_bytes=uniform_predicted,
        predicted_byte_reduction_percent=(
            100.0 * (1.0 - predicted_bytes / uniform_predicted)
            if uniform_predicted else 0.0
        ),
        plan_sha256=plan_sha256,
    )
