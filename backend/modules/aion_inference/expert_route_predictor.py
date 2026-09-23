"""Hash-bound, confidence-gated cross-layer expert-route prediction."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable, Sequence


def _canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


def build_cross_layer_route_capsule(
    observations: Sequence[dict[str, Any]],
    *,
    confidence_threshold: float = 0.80,
    max_predictions_per_layer: int = 1,
) -> dict[str, Any]:
    """Compile prompt-private route observations into a sparse transition capsule."""
    if not observations:
        raise ValueError("at least one route observation is required")
    if not 0.0 < confidence_threshold <= 1.0:
        raise ValueError("confidence threshold must be in (0, 1]")
    if max_predictions_per_layer < 1:
        raise ValueError("max predictions per layer must be positive")
    architecture = observations[0]["architecture"]
    bindings = observations[0]["bindings"]
    layers = int(architecture["layers"])
    experts = int(architecture["experts_per_layer"])
    if layers < 2 or experts < 1:
        raise ValueError("cross-layer prediction requires at least two valid layers")
    for observation in observations:
        if observation["architecture"] != architecture or observation["bindings"] != bindings:
            raise ValueError("route observations mix architectures or artifact bindings")
        if len(observation["route_batches_by_layer"]) != layers:
            raise ValueError("route observation layer count is inconsistent")
        if len(str(observation.get("observation_sha256", ""))) != 64:
            raise ValueError("route observation is not content addressed")

    compiled_layers: list[list[dict[str, Any]]] = [[]]
    for target_layer in range(1, layers):
        source_counts = [0] * experts
        pair_counts = [[0] * experts for _ in range(experts)]
        for observation in observations:
            source_batches = observation["route_batches_by_layer"][target_layer - 1]
            target_batches = observation["route_batches_by_layer"][target_layer]
            if len(source_batches) != len(target_batches):
                raise ValueError("source and target route batches are not aligned")
            for source_batch, target_batch in zip(source_batches, target_batches, strict=True):
                if len(source_batch) != len(target_batch):
                    raise ValueError("source and target token routes are not aligned")
                for source_route, target_route in zip(source_batch, target_batch, strict=True):
                    target_set = {int(expert) for expert in target_route}
                    for source_expert in {int(expert) for expert in source_route}:
                        source_counts[source_expert] += 1
                        for target_expert in target_set:
                            pair_counts[source_expert][target_expert] += 1
        sparse_sources = []
        for source_expert, denominator in enumerate(source_counts):
            if denominator == 0:
                continue
            targets = []
            for target_expert, hits in enumerate(pair_counts[source_expert]):
                if hits and hits / denominator >= confidence_threshold:
                    targets.append({
                        "expert": target_expert,
                        "hits": hits,
                        "source_observations": denominator,
                    })
            if targets:
                sparse_sources.append({"source_expert": source_expert, "targets": targets})
        compiled_layers.append(sparse_sources)

    payload = {
        "schema_version": "aion.cross_layer_route_capsule.v1",
        "architecture": architecture,
        "bindings": bindings,
        "training_observation_sha256s": sorted(
            str(observation["observation_sha256"]) for observation in observations
        ),
        "method": {
            "source": "same-token route in immediately preceding layer",
            "score": "maximum conditional probability across source-route experts",
            "confidence_threshold": confidence_threshold,
            "max_predictions_per_layer": max_predictions_per_layer,
            "prefill_prediction_enabled": False,
            "exact_demand_fallback": True,
        },
        "transitions_by_target_layer": compiled_layers,
        "privacy": {"prompt_text_stored": False, "model_output_stored": False},
    }
    return {**payload, "capsule_sha256": _canonical_sha256(payload)}


def verify_cross_layer_route_capsule(
    capsule: dict[str, Any],
    *,
    expected_bindings: dict[str, str] | None = None,
) -> None:
    body = dict(capsule)
    claimed = body.pop("capsule_sha256", None)
    if not isinstance(claimed, str) or claimed != _canonical_sha256(body):
        raise ValueError("cross-layer route capsule hash mismatch")
    if capsule.get("schema_version") != "aion.cross_layer_route_capsule.v1":
        raise ValueError("unsupported cross-layer route capsule schema")
    if expected_bindings is not None and capsule.get("bindings") != expected_bindings:
        raise ValueError("cross-layer route capsule artifact binding mismatch")


def predict_cross_layer_experts(
    capsule: dict[str, Any],
    *,
    target_layer: int,
    source_route: Iterable[int],
    resident_experts: Iterable[int] = (),
    verify: bool = True,
) -> tuple[dict[str, Any], ...]:
    """Return a bounded, deterministic prediction using only verified capsule data."""
    if verify:
        verify_cross_layer_route_capsule(capsule)
    layers = int(capsule["architecture"]["layers"])
    if target_layer <= 0 or target_layer >= layers:
        return ()
    sources = {int(expert) for expert in source_route}
    resident = {int(expert) for expert in resident_experts}
    best: dict[int, tuple[int, int, int]] = {}
    for entry in capsule["transitions_by_target_layer"][target_layer]:
        source = int(entry["source_expert"])
        if source not in sources:
            continue
        for target in entry["targets"]:
            expert = int(target["expert"])
            if expert in resident:
                continue
            hits = int(target["hits"])
            denominator = int(target["source_observations"])
            prior = best.get(expert)
            if prior is None or hits * prior[1] > prior[0] * denominator:
                best[expert] = (hits, denominator, source)
    ranked = sorted(
        best.items(),
        key=lambda item: (item[1][0] / item[1][1], -item[0]),
        reverse=True,
    )
    maximum = int(capsule["method"]["max_predictions_per_layer"])
    return tuple({
        "expert": expert,
        "confidence": hits / denominator,
        "hits": hits,
        "source_observations": denominator,
        "source_expert": source,
    } for expert, (hits, denominator, source) in ranked[:maximum])
