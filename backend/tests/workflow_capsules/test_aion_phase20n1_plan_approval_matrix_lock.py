from backend.services.aion_mission_mode.mission_plan_approval_matrix import (
    approve_plan_matrix,
    create_mission_plan_approval_matrix,
    default_control_mode_for_step,
    effective_control_mode,
    example_roofing_business_plan,
    validate_plan_matrix_unchanged,
)


def test_phase20n1_default_safe_creation_step_is_autonomous() -> None:
    decision = default_control_mode_for_step(
        {"lane": "creation", "risk_level": "low", "action_type": "draft_copy"}
    )
    assert decision == "autonomous"


def test_phase20n1_default_financial_step_requires_approval() -> None:
    decision = default_control_mode_for_step(
        {"lane": "financial_action", "risk_level": "high", "action_type": "buy_domain"}
    )
    assert decision == "human_approval_required"


def test_phase20n1_default_human_task_action_requires_human_task() -> None:
    decision = default_control_mode_for_step(
        {
            "lane": "external_action",
            "risk_level": "medium",
            "action_type": "create_real_facebook_account",
        }
    )
    assert decision == "human_task_required"


def test_phase20n1_user_can_make_safe_step_stricter() -> None:
    effective, violation = effective_control_mode(
        system_decision="autonomous",
        user_override="human_approval_required",
    )
    assert effective == "human_approval_required"
    assert violation is False


def test_phase20n1_user_cannot_downgrade_approval_step_to_autonomous() -> None:
    effective, violation = effective_control_mode(
        system_decision="human_approval_required",
        user_override="autonomous",
    )
    assert effective == "human_approval_required"
    assert violation is True


def test_phase20n1_builds_reviewable_roofing_business_plan() -> None:
    matrix = create_mission_plan_approval_matrix(
        mission_id="mission_roofing",
        mission_run_id="run_001",
        plan_id="plan_001",
        user_goal="Build my roofing business in Surrey",
        raw_steps=example_roofing_business_plan(),
    )

    assert matrix["step_count"] == 10
    assert matrix["autonomous_count"] >= 4
    assert matrix["approval_count"] >= 4
    assert matrix["human_task_count"] >= 1
    assert matrix["plan_level_approval_only"] is True
    assert matrix["payload_level_approval_still_required"] is True
    assert matrix["plan_approval_matrix_hash"].startswith("sha256:")


def test_phase20n1_buy_domain_requires_payload_later() -> None:
    matrix = create_mission_plan_approval_matrix(
        mission_id="mission_roofing",
        mission_run_id="run_001",
        plan_id="plan_001",
        user_goal="Build my roofing business in Surrey",
        raw_steps=example_roofing_business_plan(),
    )

    buy_domain = next(step for step in matrix["steps"] if step["step_id"] == "buy_domain")

    assert buy_domain["effective_decision"] == "human_approval_required"
    assert buy_domain["requires_human_approval"] is True
    assert buy_domain["payload_required_later"] is True


def test_phase20n1_facebook_page_becomes_human_task() -> None:
    matrix = create_mission_plan_approval_matrix(
        mission_id="mission_roofing",
        mission_run_id="run_001",
        plan_id="plan_001",
        user_goal="Build my roofing business in Surrey",
        raw_steps=example_roofing_business_plan(),
    )

    fb_page = next(step for step in matrix["steps"] if step["step_id"] == "facebook_page")

    assert fb_page["effective_decision"] == "human_task_required"
    assert fb_page["requires_human_task"] is True


def test_phase20n1_matrix_hash_is_deterministic() -> None:
    kwargs = dict(
        mission_id="mission_roofing",
        mission_run_id="run_001",
        plan_id="plan_001",
        user_goal="Build my roofing business in Surrey",
        raw_steps=example_roofing_business_plan(),
    )

    first = create_mission_plan_approval_matrix(**kwargs)
    second = create_mission_plan_approval_matrix(**kwargs)

    assert first["plan_approval_matrix_hash"] == second["plan_approval_matrix_hash"]


def test_phase20n1_user_override_changes_matrix_hash() -> None:
    base_steps = example_roofing_business_plan()
    changed_steps = example_roofing_business_plan()
    changed_steps[0]["user_override"] = "human_approval_required"

    base = create_mission_plan_approval_matrix(
        mission_id="mission_roofing",
        mission_run_id="run_001",
        plan_id="plan_001",
        user_goal="Build my roofing business in Surrey",
        raw_steps=base_steps,
    )
    changed = create_mission_plan_approval_matrix(
        mission_id="mission_roofing",
        mission_run_id="run_001",
        plan_id="plan_001",
        user_goal="Build my roofing business in Surrey",
        raw_steps=changed_steps,
    )

    assert base["plan_approval_matrix_hash"] != changed["plan_approval_matrix_hash"]


def test_phase20n1_plan_approval_is_plan_level_only() -> None:
    matrix = create_mission_plan_approval_matrix(
        mission_id="mission_roofing",
        mission_run_id="run_001",
        plan_id="plan_001",
        user_goal="Build my roofing business in Surrey",
        raw_steps=example_roofing_business_plan(),
    )

    approval = approve_plan_matrix(matrix=matrix, approving_human="kevin")

    assert approval["plan_level_approval_only"] is True
    assert approval["payload_level_approval_still_required"] is True
    assert approval["approved_matrix_hash"] == matrix["plan_approval_matrix_hash"]
    assert approval["plan_approval_hash"].startswith("sha256:")


def test_phase20n1_plan_change_requires_re_review() -> None:
    base_steps = example_roofing_business_plan()
    changed_steps = example_roofing_business_plan()
    changed_steps.append(
        {
            "step_id": "connect_dns",
            "title": "Connect DNS",
            "description": "Connect domain DNS to production hosting.",
            "lane": "deployment_action",
            "risk_level": "high",
            "action_type": "connect_dns",
            "provider": "domain_provider",
            "external_side_effect": True,
            "payload_required_later": True,
        }
    )

    base = create_mission_plan_approval_matrix(
        mission_id="mission_roofing",
        mission_run_id="run_001",
        plan_id="plan_001",
        user_goal="Build my roofing business in Surrey",
        raw_steps=base_steps,
    )
    changed = create_mission_plan_approval_matrix(
        mission_id="mission_roofing",
        mission_run_id="run_001",
        plan_id="plan_001",
        user_goal="Build my roofing business in Surrey",
        raw_steps=changed_steps,
        plan_version=2,
        change_reason="added_dns_step",
    )

    result = validate_plan_matrix_unchanged(
        approved_matrix_hash=base["plan_approval_matrix_hash"],
        current_matrix=changed,
    )

    assert result["plan_unchanged"] is False
    assert result["requires_re_review"] is True
    assert result["reason"] == "plan_matrix_changed_after_approval"


def test_phase20n1_policy_override_violation_blocks_runtime_mount() -> None:
    steps = example_roofing_business_plan()
    buy_domain = next(step for step in steps if step["step_id"] == "buy_domain")
    buy_domain["user_override"] = "autonomous"

    matrix = create_mission_plan_approval_matrix(
        mission_id="mission_roofing",
        mission_run_id="run_001",
        plan_id="plan_001",
        user_goal="Build my roofing business in Surrey",
        raw_steps=steps,
    )

    assert matrix["policy_override_violation_count"] == 1
    assert matrix["runtime_mount_allowed"] is False
