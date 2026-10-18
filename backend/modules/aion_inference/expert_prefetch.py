"""Deterministic bridge from Semantic Gateway profiles to MoE expert shards."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any, Mapping, Sequence


PROFILE_DOMAINS: Mapping[str, tuple[str, ...]] = {
    "arithmetic_business": ("arithmetic", "business"),
    "policy": ("policy",),
    "coding": ("coding",),
    "general": ("general",),
}


@dataclass(frozen=True)
class ExpertPrefetchPlan:
    profile: str
    source_domains: tuple[str, ...]
    coverage_target: float
    max_experts_per_layer: int | None
    experts_by_layer: tuple[tuple[int, ...], ...]
    expert_count_by_layer: tuple[int, ...]
    plan_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _plan_digest(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(dict(payload), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def build_expert_prefetch_plan(
    routing_profile: Mapping[str, Any],
    profile: str,
    *,
    coverage_target: float = 0.90,
    max_experts_per_layer: int | None = None,
) -> ExpertPrefetchPlan:
    """Build a bounded per-layer plan from measured Granite router counts."""
    if profile not in PROFILE_DOMAINS:
        raise ValueError(f"unsupported expert prefetch profile: {profile}")
    if not 0.0 < coverage_target <= 1.0:
        raise ValueError("coverage_target must be in (0, 1]")

    counts_by_domain = routing_profile["training"]["counts_by_domain"]
    domains = PROFILE_DOMAINS[profile]
    missing = [domain for domain in domains if domain not in counts_by_domain]
    if missing:
        raise ValueError(f"routing profile is missing domains: {missing}")
    layers = len(counts_by_domain[domains[0]])
    expert_total = int(routing_profile["architecture"]["experts_per_layer"])
    minimum = int(routing_profile["architecture"]["experts_selected_per_token"])
    if max_experts_per_layer is not None and not minimum <= max_experts_per_layer <= expert_total:
        raise ValueError("max_experts_per_layer must cover top-k and not exceed the expert count")
    if any(len(counts_by_domain[domain]) != layers for domain in domains):
        raise ValueError("routing profile domain layer counts differ")

    selected_layers: list[tuple[int, ...]] = []
    for layer in range(layers):
        combined = [0] * expert_total
        for domain in domains:
            counts = counts_by_domain[domain][layer]
            if len(counts) != expert_total:
                raise ValueError("routing profile expert counts differ from architecture")
            combined = [left + int(right) for left, right in zip(combined, counts, strict=True)]
        ordered = [expert for expert, _ in Counter(dict(enumerate(combined))).most_common()]
        threshold = sum(combined) * coverage_target
        running = 0
        chosen: list[int] = []
        for expert in ordered:
            chosen.append(expert)
            running += combined[expert]
            if max_experts_per_layer is not None and len(chosen) >= max_experts_per_layer:
                break
            if running >= threshold and len(chosen) >= minimum:
                break
        selected_layers.append(tuple(sorted(chosen)))

    payload = {
        "profile": profile,
        "source_domains": domains,
        "coverage_target": coverage_target,
        "max_experts_per_layer": max_experts_per_layer,
        "experts_by_layer": selected_layers,
    }
    return ExpertPrefetchPlan(
        profile=profile,
        source_domains=domains,
        coverage_target=coverage_target,
        max_experts_per_layer=max_experts_per_layer,
        experts_by_layer=tuple(selected_layers),
        expert_count_by_layer=tuple(len(layer) for layer in selected_layers),
        plan_sha256=_plan_digest(payload),
    )


def broad_expert_prefetch_plan(routing_profile: Mapping[str, Any]) -> ExpertPrefetchPlan:
    """Return the existing cross-domain residency plan as the broad control."""
    layers: Sequence[Sequence[int]] = routing_profile["training"]["resident_experts_by_layer"]
    selected = tuple(tuple(sorted(map(int, layer))) for layer in layers)
    coverage = float(routing_profile["method"]["coverage_target"])
    payload = {
        "profile": "broad_control",
        "source_domains": tuple(sorted(routing_profile["training"]["counts_by_domain"])),
        "coverage_target": coverage,
        "max_experts_per_layer": None,
        "experts_by_layer": selected,
    }
    return ExpertPrefetchPlan(
        profile="broad_control",
        source_domains=payload["source_domains"],
        coverage_target=coverage,
        max_experts_per_layer=None,
        experts_by_layer=selected,
        expert_count_by_layer=tuple(len(layer) for layer in selected),
        plan_sha256=_plan_digest(payload),
    )
