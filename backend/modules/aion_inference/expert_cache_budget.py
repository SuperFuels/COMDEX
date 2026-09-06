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
