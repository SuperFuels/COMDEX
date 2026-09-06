from __future__ import annotations

import pytest

from backend.modules.aion_inference import (
    broad_expert_prefetch_plan,
    build_expert_prefetch_plan,
)
from backend.scripts.run_aion_layer_scoped_moe_experiment import LayerScopedStore


def _routing_profile():
    return {
        "architecture": {"experts_per_layer": 4, "experts_selected_per_token": 2},
        "method": {"coverage_target": 0.95},
        "training": {
            "counts_by_domain": {
                "arithmetic": [[8, 2, 0, 0], [0, 1, 8, 1]],
                "business": [[6, 4, 0, 0], [0, 2, 7, 1]],
                "policy": [[0, 1, 8, 1], [7, 0, 1, 2]],
                "coding": [[1, 0, 2, 7], [1, 7, 2, 0]],
                "general": [[2, 6, 1, 1], [2, 1, 1, 6]],
            },
            "resident_experts_by_layer": [[0, 1, 2], [0, 1, 2, 3]],
        },
    }


def test_gateway_profile_builds_deterministic_bounded_layer_plan():
    profile = _routing_profile()
    first = build_expert_prefetch_plan(profile, "arithmetic_business", coverage_target=0.80)
    second = build_expert_prefetch_plan(profile, "arithmetic_business", coverage_target=0.80)
    assert first.experts_by_layer == ((0, 1), (1, 2))
    assert first.expert_count_by_layer == (2, 2)
    assert first.plan_sha256 == second.plan_sha256
    assert first.source_domains == ("arithmetic", "business")


def test_broad_plan_reuses_measured_cross_domain_resident_sets():
    plan = broad_expert_prefetch_plan(_routing_profile())
    assert plan.profile == "broad_control"
    assert plan.experts_by_layer == ((0, 1, 2), (0, 1, 2, 3))
    assert plan.coverage_target == 0.95


def test_layer_ahead_plan_can_be_capped_at_native_router_top_k():
    plan = build_expert_prefetch_plan(
        _routing_profile(), "policy", coverage_target=0.99, max_experts_per_layer=2
    )
    assert plan.max_experts_per_layer == 2
    assert plan.expert_count_by_layer == (2, 2)


def test_prefetch_plan_rejects_unknown_profile_and_invalid_coverage():
    with pytest.raises(ValueError, match="unsupported"):
        build_expert_prefetch_plan(_routing_profile(), "imaginary")
    with pytest.raises(ValueError, match="coverage_target"):
        build_expert_prefetch_plan(_routing_profile(), "policy", coverage_target=0.0)
    with pytest.raises(ValueError, match="max_experts_per_layer"):
        build_expert_prefetch_plan(_routing_profile(), "policy", max_experts_per_layer=1)


def test_layer_store_retains_bounded_union_of_two_live_routes():
    store = LayerScopedStore(0, {"experts": []})
    store.active = {1: ("i1", "o1"), 2: ("i2", "o2"), 3: ("i3", "o3")}
    store.release_with_lru_routes(((1, 2),), 2)
    assert set(store.retained) == {1, 2}

    store.active = {2: ("i2-new", "o2-new"), 3: ("i3", "o3")}
    store.release_with_lru_routes(((2, 3),), 2)
    assert set(store.retained) == {1, 2, 3}

    store.active = {3: ("i3-new", "o3-new")}
    store.release_with_lru_routes(((3,),), 2)
    assert set(store.retained) == {2, 3}


def test_layer_store_frequency_cache_is_bounded_and_rewards_reuse():
    store = LayerScopedStore(0, {"experts": []})
    store.active = {expert: (f"i{expert}", f"o{expert}") for expert in (1, 2, 3)}
    store.release_with_frequency_capacity(((1, 2), (1, 3)), 2)
    assert set(store.retained) == {1, 3}

    store.active = {2: ("i2-new", "o2-new")}
    store.release_with_frequency_capacity(((2,), (2,)), 2)
    assert set(store.retained) == {1, 2}
    assert len(store.retained) == 2


def test_layer_store_frequency_cache_rejects_zero_capacity():
    store = LayerScopedStore(0, {"experts": []})
    with pytest.raises(ValueError, match="capacity"):
        store.release_with_frequency_capacity(((1,),), 0)
