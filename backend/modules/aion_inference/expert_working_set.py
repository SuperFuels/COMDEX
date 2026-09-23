"""Hash-bound, read-free expert reuse predictions for exact MoE eviction."""

from __future__ import annotations

from collections import Counter
import hashlib
import json
from typing import Any, Iterable, Mapping, Sequence


def _hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _required(batch: Sequence[Sequence[int]]) -> set[int]:
    return {int(expert) for route in batch for expert in route}


def build_expert_working_set_dictionary(
    observations: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Learn within-layer next-batch transitions without prompt or output text."""
    if not observations:
        raise ValueError("at least one route observation is required")
    bindings = observations[0]["bindings"]
    architecture = observations[0]["architecture"]
    if any(item["bindings"] != bindings for item in observations[1:]):
        raise ValueError("route observations mix model or manifest bindings")
    if any(item["architecture"] != architecture for item in observations[1:]):
        raise ValueError("route observations mix architectures")
    layer_count = int(architecture["layers"])
    if any(len(item["route_batches_by_layer"]) != layer_count for item in observations):
        raise ValueError("route observations are missing layers")

    layers = []
    for layer in range(layer_count):
        transitions: dict[int, Counter[int]] = {}
        prior: Counter[int] = Counter()
        pairs = 0
        for observation in observations:
            required = [_required(batch) for batch in observation["route_batches_by_layer"][layer]]
            for current, following in zip(required, required[1:]):
                pairs += 1
                prior.update(following)
                for source in current:
                    transitions.setdefault(source, Counter()).update(following)
        layers.append({
            "layer": layer,
            "transition_pairs": pairs,
            "next_expert_prior": {str(key): value for key, value in sorted(prior.items())},
            "transitions": {
                str(source): {str(target): count for target, count in sorted(counts.items())}
                for source, counts in sorted(transitions.items())
            },
        })
    payload = {
        "schema_version": "aion.expert_working_set_dictionary.v1",
        "bindings": bindings,
        "architecture": architecture,
        "training_observation_sha256s": sorted(
            str(item["observation_sha256"]) for item in observations
        ),
        "method": {
            "prediction": "sum_next_expert_transition_counts",
            "action": "protect_already_resident_experts_only",
            "speculative_storage_reads": False,
            "fallback": "exact_demand_load",
        },
        "layers": layers,
    }
    return {**payload, "dictionary_sha256": _hash(payload)}


def verify_expert_working_set_dictionary(
    document: Mapping[str, Any], *, expected_bindings: Mapping[str, Any] | None = None
) -> None:
    payload = dict(document)
    claimed = payload.pop("dictionary_sha256", None)
    if claimed != _hash(payload):
        raise ValueError("expert working-set dictionary hash mismatch")
    if expected_bindings is not None and payload["bindings"] != expected_bindings:
        raise ValueError("expert working-set dictionary binding mismatch")
    if payload["method"]["speculative_storage_reads"] is not False:
        raise ValueError("working-set dictionary must not authorize speculative reads")


def select_predictive_retention(
    *,
    routes: Sequence[Sequence[int]],
    available_experts: Iterable[int],
    usage_counts: dict[int, int],
    last_used: dict[int, int],
    usage_clock: int,
    capacity: int,
    layer_dictionary: Mapping[str, Any],
) -> tuple[tuple[int, ...], int]:
    """Protect likely next-use experts, considering only weights already resident."""
    if capacity < 1:
        raise ValueError("capacity must be positive")
    current: set[int] = set()
    for route in routes:
        usage_clock += 1
        for raw_expert in route:
            expert = int(raw_expert)
            current.add(expert)
            usage_counts[expert] = usage_counts.get(expert, 0) + 1
            last_used[expert] = usage_clock
    transitions = layer_dictionary["transitions"]
    prior = layer_dictionary["next_expert_prior"]

    def key(expert: int) -> tuple[int, int, int, int, int]:
        prediction = sum(
            int(transitions.get(str(source), {}).get(str(expert), 0))
            for source in current
        )
        return (
            prediction,
            int(prior.get(str(expert), 0)),
            usage_counts.get(expert, 0),
            last_used.get(expert, 0),
            -expert,
        )

    ranked = sorted({int(value) for value in available_experts}, key=key, reverse=True)
    return tuple(ranked[:capacity]), usage_clock
