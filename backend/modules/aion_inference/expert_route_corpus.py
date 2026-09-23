"""Content-addressed, prompt-private route corpus for MoE cache learning."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Sequence

from .expert_cache_budget import (
    ExpertCacheBudgetPlan,
    ExpertCacheMemoryPlan,
    RouteBatch,
    optimize_expert_cache_budget,
    optimize_expert_cache_memory_budget,
)


def _canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


class ExpertRouteCorpus:
    """Store verified router selections without storing the user's prompt text."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.objects = self.root / "objects"
        self.objects.mkdir(parents=True, exist_ok=True)

    def record(
        self,
        *,
        route_batches_by_layer: Sequence[Sequence[RouteBatch]],
        glyph_address: str,
        model_input_sha256: str,
        generated_tokens: int,
        model_config_sha256: str,
        shard_manifest_sha256: str,
        pack_manifest_sha256: str,
        experts_per_layer: int,
    ) -> str:
        layers = len(route_batches_by_layer)
        if layers < 1 or experts_per_layer < 1 or generated_tokens < 1:
            raise ValueError("route corpus architecture and token count must be positive")
        if not glyph_address.startswith("glyph:sha256:"):
            raise ValueError("route observation requires a content-addressed glyph")
        hashes = (model_input_sha256, model_config_sha256, shard_manifest_sha256, pack_manifest_sha256)
        if any(len(value) != 64 for value in hashes):
            raise ValueError("route observation bindings must be SHA-256 digests")
        normalized = []
        for layer_batches in route_batches_by_layer:
            if not layer_batches:
                raise ValueError("route observation must contain batches for every layer")
            normalized_batches = []
            for batch in layer_batches:
                normalized_routes = []
                for route in batch:
                    experts = tuple(int(expert) for expert in route)
                    if any(expert < 0 or expert >= experts_per_layer for expert in experts):
                        raise ValueError("route observation contains an out-of-range expert")
                    normalized_routes.append(list(experts))
                normalized_batches.append(normalized_routes)
            normalized.append(normalized_batches)
        payload = {
            "schema_version": "aion.expert_route_observation.v1",
            "architecture": {"layers": layers, "experts_per_layer": experts_per_layer},
            "glyph_address": glyph_address,
            "model_input_sha256": model_input_sha256,
            "generated_tokens": generated_tokens,
            "bindings": {
                "model_config_sha256": model_config_sha256,
                "shard_manifest_sha256": shard_manifest_sha256,
                "pack_manifest_sha256": pack_manifest_sha256,
            },
            "route_batches_by_layer": normalized,
            "privacy": {"prompt_text_stored": False, "model_output_stored": False},
        }
        observation_sha256 = _canonical_sha256(payload)
        document = {**payload, "observation_sha256": observation_sha256}
        path = self.objects / f"{observation_sha256}.json"
        encoded = json.dumps(document, indent=2, sort_keys=True) + "\n"
        if path.exists():
            if path.read_text(encoding="utf-8") != encoded:
                raise RuntimeError("content-address collision in route corpus")
        else:
            with path.open("x", encoding="utf-8") as handle:
                handle.write(encoded)
        return observation_sha256

    def load(self, observation_sha256: str) -> dict[str, Any]:
        if len(observation_sha256) != 64:
            raise ValueError("invalid route observation digest")
        path = self.objects / f"{observation_sha256}.json"
        document = json.loads(path.read_text(encoding="utf-8"))
        claimed = document.pop("observation_sha256", None)
        if claimed != observation_sha256 or _canonical_sha256(document) != observation_sha256:
            raise ValueError("route observation hash mismatch")
        document["observation_sha256"] = claimed
        return document

    def optimize(
        self,
        observation_sha256s: Sequence[str],
        entries_by_layer: Sequence[dict[int, dict[str, Any]]],
        *,
        total_capacity: int,
    ) -> ExpertCacheBudgetPlan:
        if not observation_sha256s:
            raise ValueError("at least one route observation is required")
        observations = [self.load(digest) for digest in observation_sha256s]
        binding = observations[0]["bindings"]
        architecture = observations[0]["architecture"]
        if any(observation["bindings"] != binding for observation in observations[1:]):
            raise ValueError("route corpus mixes model or manifest bindings")
        if any(observation["architecture"] != architecture for observation in observations[1:]):
            raise ValueError("route corpus mixes architectures")
        if len(entries_by_layer) != int(architecture["layers"]):
            raise ValueError("route corpus and expert entries are misaligned")
        combined: list[list[RouteBatch]] = [[] for _ in entries_by_layer]
        for observation in observations:
            for layer, batches in enumerate(observation["route_batches_by_layer"]):
                combined[layer].extend(
                    tuple(tuple(int(expert) for expert in route) for route in batch)
                    for batch in batches
                )
        return optimize_expert_cache_budget(
            tuple(tuple(batches) for batches in combined),
            entries_by_layer,
            total_capacity=total_capacity,
        )

    def optimize_memory(
        self,
        observation_sha256s: Sequence[str],
        entries_by_layer: Sequence[dict[int, dict[str, Any]]],
        *,
        maximum_resident_bytes: int,
    ) -> ExpertCacheMemoryPlan:
        """Learn an exact plan from verified observations under a byte ceiling."""
        if not observation_sha256s:
            raise ValueError("at least one route observation is required")
        observations = [self.load(digest) for digest in observation_sha256s]
        binding = observations[0]["bindings"]
        architecture = observations[0]["architecture"]
        if any(observation["bindings"] != binding for observation in observations[1:]):
            raise ValueError("route corpus mixes model or manifest bindings")
        if any(observation["architecture"] != architecture for observation in observations[1:]):
            raise ValueError("route corpus mixes architectures")
        if len(entries_by_layer) != int(architecture["layers"]):
            raise ValueError("route corpus and expert entries are misaligned")
        combined: list[list[RouteBatch]] = [[] for _ in entries_by_layer]
        for observation in observations:
            for layer, batches in enumerate(observation["route_batches_by_layer"]):
                combined[layer].extend(
                    tuple(tuple(int(expert) for expert in route) for route in batch)
                    for batch in batches
                )
        return optimize_expert_cache_memory_budget(
            tuple(tuple(batches) for batches in combined),
            entries_by_layer,
            maximum_resident_bytes=maximum_resident_bytes,
        )
