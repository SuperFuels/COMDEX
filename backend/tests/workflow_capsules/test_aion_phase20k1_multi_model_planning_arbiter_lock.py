import pytest

from backend.services.aion_mission_mode.multi_model_planning_arbiter import (
    PlannerConsensusRejected,
    UnsupportedPlannerProvider,
    compile_arbiter_output_to_contract,
    compare_step_sets,
    merge_planner_proposals,
    normalise_planner_proposal,
)


def _gemma_plan():
    return {
        "plan_title": "Build Home Fixed campaign",
        "suggested_steps": [
            {
                "step_id": "g1",
                "title": "Draft offer",
                "description": "Create campaign offer",
                "suggested_action_type": "draft_offer",
                "suggested_lane": "autonomous",
            },
            {
                "step_id": "g2",
                "title": "Build landing page",
                "description": "Generate landing copy",
                "suggested_action_type": "create_landing_page_preview",
                "suggested_lane": "autonomous",
            },
            {
                "step_id": "g3",
                "title": "Deploy website",
                "description": "Deploy production website",
                "suggested_action_type": "deploy_to_production",
                "suggested_lane": "autonomous",
            },
        ],
    }


def _openai_plan():
    return {
        "title": "Home Fixed launch",
        "steps": [
            {
                "step_id": "o1",
                "title": "Draft offer",
                "description": "Create offer",
                "action_type": "draft_offer",
                "lane": "autonomous",
            },
            {
                "step_id": "o2",
                "title": "Build landing page",
                "description": "Generate site preview",
                "action_type": "create_landing_page_preview",
                "lane": "autonomous",
            },
            {
                "step_id": "o3",
                "title": "Publish first Facebook post",
                "description": "Publish public post",
                "action_type": "publish_facebook_post",
                "lane": "autonomous",
            },
        ],
    }


def test_phase20k1_normalises_supported_planner():
    proposal = normalise_planner_proposal("gemma_local", _gemma_plan())
    assert proposal["provider"] == "gemma_local"
    assert proposal["model_may_execute"] is False
    assert proposal["requires_aion_compilation"] is True
    assert proposal["proposal_hash"].startswith("sha256:")


def test_phase20k1_rejects_unsupported_provider():
    with pytest.raises(UnsupportedPlannerProvider):
        normalise_planner_proposal("random_model", _gemma_plan())


def test_phase20k1_recursively_blocks_execution_injection():
    bad = _gemma_plan()
    bad["suggested_steps"][0]["nested"] = {"execute_now": True}
    with pytest.raises(PlannerConsensusRejected):
        normalise_planner_proposal("gemma_local", bad)


def test_phase20k1_risky_model_label_is_overridden():
    proposal = normalise_planner_proposal("gemma_local", _gemma_plan())
    deploy = [s for s in proposal["steps"] if s["action_type"] == "deploy_to_production"][0]
    assert deploy["planner_suggested_lane"] == "autonomous"
    assert deploy["aion_effective_control"] == "human_approval_required"


def test_phase20k1_human_task_action_is_forced():
    plan = {
        "suggested_steps": [
            {
                "step_id": "x",
                "title": "Create Facebook account",
                "description": "Create real Facebook account",
                "suggested_action_type": "create_real_facebook_account",
                "suggested_lane": "autonomous",
            }
        ]
    }
    proposal = normalise_planner_proposal("mock_planner", plan)
    assert proposal["steps"][0]["aion_effective_control"] == "human_task_required"


def test_phase20k1_compares_step_sets():
    a = normalise_planner_proposal("gemma_local", _gemma_plan())
    b = normalise_planner_proposal("openai_frontier", _openai_plan())
    comparison = compare_step_sets(a, b)
    assert "draft_offer" in comparison["shared_step_keys"]
    assert comparison["comparison_hash"].startswith("sha256:")
    assert comparison["jaccard_similarity"] > 0


def test_phase20k1_rejects_low_similarity_plans():
    a = normalise_planner_proposal("gemma_local", _gemma_plan())
    b = normalise_planner_proposal(
        "openai_frontier",
        {
            "steps": [
                {
                    "step_id": "z",
                    "title": "Unrelated",
                    "description": "No overlap",
                    "action_type": "totally_unrelated_step",
                }
            ]
        },
    )
    with pytest.raises(PlannerConsensusRejected):
        merge_planner_proposals("mission-1", "home-fixed", [a, b], min_similarity=0.5)


def test_phase20k1_merges_missing_steps():
    a = normalise_planner_proposal("gemma_local", _gemma_plan())
    b = normalise_planner_proposal("openai_frontier", _openai_plan())
    merged = merge_planner_proposals("mission-1", "home-fixed", [a, b], min_similarity=0.2)

    action_types = {s["action_type"] for s in merged["steps"]}
    assert "deploy_to_production" in action_types
    assert "publish_facebook_post" in action_types
    assert merged["arbiter_hash"].startswith("sha256:")
    assert merged["model_may_execute"] is False


def test_phase20k1_merged_risky_steps_remain_approval_required():
    a = normalise_planner_proposal("gemma_local", _gemma_plan())
    b = normalise_planner_proposal("openai_frontier", _openai_plan())
    merged = merge_planner_proposals("mission-1", "home-fixed", [a, b], min_similarity=0.2)

    controls = {s["action_type"]: s["aion_effective_control"] for s in merged["steps"]}
    assert controls["deploy_to_production"] == "human_approval_required"
    assert controls["publish_facebook_post"] == "human_approval_required"


def test_phase20k1_duplicate_provider_rejected():
    a = normalise_planner_proposal("gemma_local", _gemma_plan())
    b = normalise_planner_proposal("gemma_local", _gemma_plan())
    with pytest.raises(PlannerConsensusRejected):
        merge_planner_proposals("mission-1", "home-fixed", [a, b])


def test_phase20k1_step_limit_enforced():
    plan = {
        "steps": [
            {
                "step_id": f"s{i}",
                "title": f"Step {i}",
                "description": "x",
                "action_type": f"action_{i}",
            }
            for i in range(5)
        ]
    }
    p = normalise_planner_proposal("mock_planner", plan)
    with pytest.raises(PlannerConsensusRejected):
        merge_planner_proposals("mission-1", "biz", [p], max_merged_steps=2)


def test_phase20k1_compiles_to_review_only_contract():
    a = normalise_planner_proposal("gemma_local", _gemma_plan())
    b = normalise_planner_proposal("openai_frontier", _openai_plan())
    merged = merge_planner_proposals("mission-1", "home-fixed", [a, b], min_similarity=0.2)
    contract = compile_arbiter_output_to_contract(merged)

    assert contract["compiled_contract_state"] == "requires_plan_matrix_review"
    assert contract["must_pass_plan_approval_matrix"] is True
    assert contract["must_pass_external_tool_gateway"] is True
    assert contract["live_external_side_effects_allowed"] is False
    assert contract["contract_hash"].startswith("sha256:")


def test_phase20k1_contract_hash_is_deterministic():
    a1 = normalise_planner_proposal("gemma_local", _gemma_plan())
    b1 = normalise_planner_proposal("openai_frontier", _openai_plan())
    merged1 = merge_planner_proposals("mission-1", "home-fixed", [a1, b1], min_similarity=0.2)
    c1 = compile_arbiter_output_to_contract(merged1)

    a2 = normalise_planner_proposal("gemma_local", _gemma_plan())
    b2 = normalise_planner_proposal("openai_frontier", _openai_plan())
    merged2 = merge_planner_proposals("mission-1", "home-fixed", [a2, b2], min_similarity=0.2)
    c2 = compile_arbiter_output_to_contract(merged2)

    assert c1["contract_hash"] == c2["contract_hash"]
