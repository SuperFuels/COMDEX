from __future__ import annotations

import pytest

from backend.modules.aion_inference import (
    broad_expert_prefetch_plan,
    build_expert_prefetch_plan,
)


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


def test_prefetch_plan_rejects_unknown_profile_and_invalid_coverage():
    with pytest.raises(ValueError, match="unsupported"):
        build_expert_prefetch_plan(_routing_profile(), "imaginary")
    with pytest.raises(ValueError, match="coverage_target"):
        build_expert_prefetch_plan(_routing_profile(), "policy", coverage_target=0.0)
