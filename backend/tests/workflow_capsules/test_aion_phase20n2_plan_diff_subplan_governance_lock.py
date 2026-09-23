from backend.services.aion_mission_mode.mission_plan_approval_matrix import (
    create_mission_plan_approval_matrix,
    example_roofing_business_plan,
)
from backend.services.aion_mission_mode.plan_diff_subplan_governance import (
    approve_subplan_matrix,
    create_plan_diff,
    create_subplan_approval_matrix,
    create_subplan_tree_hash,
    strictest_decision,
    validate_subplan_authority,
)


def _base_matrix():
    return create_mission_plan_approval_matrix(
        mission_id="mission_roofing",
        mission_run_id="run_001",
        plan_id="plan_001",
        user_goal="Build my roofing business in Surrey",
        raw_steps=example_roofing_business_plan(),
    )


def test_phase20n2_plan_diff_detects_added_step() -> None:
    previous = _base_matrix()
    changed_steps = example_roofing_business_plan()
    changed_steps.append(
        {
            "step_id": "connect_dns",
            "title": "Connect DNS",
            "description": "Connect domain DNS.",
            "lane": "deployment_action",
            "risk_level": "high",
            "action_type": "connect_dns",
            "provider": "domain_provider",
            "external_side_effect": True,
            "payload_required_later": True,
        }
    )
    current = create_mission_plan_approval_matrix(
        mission_id="mission_roofing",
        mission_run_id="run_001",
        plan_id="plan_001",
        plan_version=2,
        user_goal="Build my roofing business in Surrey",
        raw_steps=changed_steps,
        change_reason="added_dns_step",
    )

    diff = create_plan_diff(
        previous_plan=previous,
        current_plan=current,
        reason="added_dns_step",
    )

    assert diff["requires_re_review"] is True
    assert len(diff["added_steps"]) == 1
    assert diff["added_steps"][0]["step_id"] == "connect_dns"
    assert len(diff["new_external_side_effects"]) == 1
    assert diff["plan_diff_hash"].startswith("sha256:")


def test_phase20n2_plan_diff_detects_removed_step() -> None:
    previous = _base_matrix()
    reduced_steps = [s for s in example_roofing_business_plan() if s["step_id"] != "launch_ad"]

    current = create_mission_plan_approval_matrix(
        mission_id="mission_roofing",
        mission_run_id="run_001",
        plan_id="plan_001",
        plan_version=2,
        user_goal="Build my roofing business in Surrey",
        raw_steps=reduced_steps,
        change_reason="removed_ad_step",
    )

    diff = create_plan_diff(previous_plan=previous, current_plan=current, reason="removed_ad_step")

    assert diff["requires_re_review"] is True
    assert len(diff["removed_steps"]) == 1
    assert diff["removed_steps"][0]["step_id"] == "launch_ad"


def test_phase20n2_plan_diff_detects_modified_cost() -> None:
    previous = _base_matrix()
    changed_steps = example_roofing_business_plan()
    launch_ad = next(s for s in changed_steps if s["step_id"] == "launch_ad")
    launch_ad["estimated_cost"] = 80.0

    current = create_mission_plan_approval_matrix(
        mission_id="mission_roofing",
        mission_run_id="run_001",
        plan_id="plan_001",
        plan_version=2,
        user_goal="Build my roofing business in Surrey",
        raw_steps=changed_steps,
        change_reason="ad_budget_changed",
    )

    diff = create_plan_diff(previous_plan=previous, current_plan=current, reason="ad_budget_changed")

    assert diff["requires_re_review"] is True
    assert len(diff["modified_steps"]) == 1
    assert diff["estimated_cost_delta"] == 30.0


def test_phase20n2_strictest_decision_detects_parent_ceiling() -> None:
    matrix = _base_matrix()
    assert strictest_decision(matrix["steps"]) == "human_task_required"


def test_phase20n2_subplan_matrix_requires_review_and_blocks_execution_initially() -> None:
    parent = _base_matrix()
    subplan_steps = [
        {
            "step_id": "draft_campaign",
            "title": "Draft marketing campaign",
            "description": "Draft posts and campaign copy.",
            "lane": "creation",
            "risk_level": "low",
            "action_type": "draft_campaign",
            "default_decision": "autonomous",
            "effective_decision": "autonomous",
        }
    ]

    subplan = create_subplan_approval_matrix(
        parent_mission_id=parent["mission_id"],
        parent_mission_run_id=parent["mission_run_id"],
        parent_plan_id=parent["plan_id"],
        parent_matrix_hash=parent["plan_approval_matrix_hash"],
        parent_steps=parent["steps"],
        subplan_id="subplan_marketing",
        reason_created="need_marketing_launch_plan",
        subplan_steps=subplan_steps,
    )

    assert subplan["subplan_review_required"] is True
    assert subplan["subplan_execution_allowed"] is False
    assert subplan["subplan_approval_matrix_hash"].startswith("sha256:")


def test_phase20n2_subplan_approval_allows_clean_subplan() -> None:
    parent = _base_matrix()
    subplan_steps = [
        {
            "step_id": "draft_campaign",
            "title": "Draft marketing campaign",
            "description": "Draft posts and campaign copy.",
            "lane": "creation",
            "risk_level": "low",
            "action_type": "draft_campaign",
            "default_decision": "autonomous",
            "effective_decision": "autonomous",
        }
    ]

    subplan = create_subplan_approval_matrix(
        parent_mission_id=parent["mission_id"],
        parent_mission_run_id=parent["mission_run_id"],
        parent_plan_id=parent["plan_id"],
        parent_matrix_hash=parent["plan_approval_matrix_hash"],
        parent_steps=parent["steps"],
        subplan_id="subplan_marketing",
        reason_created="need_marketing_launch_plan",
        subplan_steps=subplan_steps,
    )
    approval = approve_subplan_matrix(subplan_matrix=subplan, approving_human="kevin")

    assert approval["approved"] is True
    assert approval["subplan_execution_allowed"] is True
    assert approval["subplan_approval_hash"].startswith("sha256:")


def test_phase20n2_subplan_depth_ceiling_blocks_subplan() -> None:
    parent = _base_matrix()
    subplan = create_subplan_approval_matrix(
        parent_mission_id=parent["mission_id"],
        parent_mission_run_id=parent["mission_run_id"],
        parent_plan_id=parent["plan_id"],
        parent_matrix_hash=parent["plan_approval_matrix_hash"],
        parent_steps=parent["steps"],
        subplan_id="subplan_too_deep",
        reason_created="nested_plan_attempt",
        subplan_steps=[],
        subplan_depth=4,
        max_subplan_depth=3,
    )

    approval = approve_subplan_matrix(subplan_matrix=subplan, approving_human="kevin")

    assert subplan["violation_reason"] == "max_subplan_depth_exceeded"
    assert approval["approved"] is False
    assert approval["subplan_execution_allowed"] is False


def test_phase20n2_total_step_ceiling_blocks_subplan() -> None:
    parent = _base_matrix()
    subplan = create_subplan_approval_matrix(
        parent_mission_id=parent["mission_id"],
        parent_mission_run_id=parent["mission_run_id"],
        parent_plan_id=parent["plan_id"],
        parent_matrix_hash=parent["plan_approval_matrix_hash"],
        parent_steps=parent["steps"],
        subplan_id="subplan_too_large",
        reason_created="too_many_steps",
        subplan_steps=[],
        current_total_steps_across_all_plans=101,
        max_total_steps_across_all_plans=100,
    )

    assert subplan["violation_reason"] == "max_total_steps_exceeded"
    assert subplan["subplan_execution_allowed"] is False


def test_phase20n2_subplan_authority_violation_detected() -> None:
    parent_steps = [
        {
            "step_id": "buy_domain",
            "lane": "financial_action",
            "effective_decision": "human_approval_required",
        }
    ]
    subplan_steps = [
        {
            "step_id": "buy_domain_silently",
            "lane": "financial_action",
            "effective_decision": "autonomous",
        }
    ]

    result = validate_subplan_authority(
        parent_steps=parent_steps,
        subplan_steps=subplan_steps,
        parent_safety_ceiling="human_approval_required",
    )

    assert result["authority_valid"] is False
    assert result["violation_count"] == 1
    assert result["violations"][0]["reason"] == "subplan_attempted_to_weaken_parent_boundary"


def test_phase20n2_subplan_tree_hash_is_deterministic() -> None:
    first = create_subplan_tree_hash(
        parent_plan_hash="sha256:parent",
        subplan_hashes=["sha256:b", "sha256:a"],
    )
    second = create_subplan_tree_hash(
        parent_plan_hash="sha256:parent",
        subplan_hashes=["sha256:a", "sha256:b"],
    )

    assert first == second
    assert first.startswith("sha256:")


def test_phase20n2_plan_diff_hash_is_deterministic() -> None:
    previous = _base_matrix()
    changed_steps = example_roofing_business_plan()
    changed_steps.append(
        {
            "step_id": "extra_safe_copy",
            "title": "Draft extra copy",
            "description": "Draft more local copy.",
            "lane": "creation",
            "risk_level": "low",
            "action_type": "draft_copy",
        }
    )
    current = create_mission_plan_approval_matrix(
        mission_id="mission_roofing",
        mission_run_id="run_001",
        plan_id="plan_001",
        plan_version=2,
        user_goal="Build my roofing business in Surrey",
        raw_steps=changed_steps,
        change_reason="added_copy",
    )

    first = create_plan_diff(previous_plan=previous, current_plan=current, reason="added_copy")
    second = create_plan_diff(previous_plan=previous, current_plan=current, reason="added_copy")

    assert first["plan_diff_hash"] == second["plan_diff_hash"]
