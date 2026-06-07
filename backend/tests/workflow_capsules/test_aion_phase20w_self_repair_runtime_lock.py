from backend.services.aion_mission_mode.self_repair_runtime import (
    RepairAttemptInput,
    final_repair_failure_result,
    is_forbidden_repair_action,
    is_safe_repair_lane,
    run_repair_attempt,
    validate_repair_attempt_allowed,
)


def make_attempt(**overrides):
    data = {
        "mission_id": "mission_home_fixed_lead_campaign_001",
        "mission_run_id": "run_001",
        "step_id": "step_03_draft_facebook_advert",
        "action_type": "draft_facebook_advert",
        "lane": "creation",
        "error_type": "schema_error",
        "error_message": "description must be string",
        "payload": {"title": None, "description": None, "content": "Draft ad"},
        "trace_context": {"state_hash": "sha256:state"},
        "attempt_index": 1,
    }
    data.update(overrides)
    return RepairAttemptInput(**data)


def test_phase20w_safe_repair_lanes_are_locked() -> None:
    assert is_safe_repair_lane("research") is True
    assert is_safe_repair_lane("creation") is True
    assert is_safe_repair_lane("internal_ops") is True
    assert is_safe_repair_lane("external_action") is False


def test_phase20w_forbidden_repair_actions_are_locked() -> None:
    assert is_forbidden_repair_action("send_email_live") is True
    assert is_forbidden_repair_action("take_payment") is True
    assert is_forbidden_repair_action("deploy_live_page") is True
    assert is_forbidden_repair_action("draft_offer") is False


def test_phase20w_repair_allowed_for_safe_internal_creation_step() -> None:
    allowed, reason = validate_repair_attempt_allowed(make_attempt())

    assert allowed is True
    assert reason == "repair_allowed_safe_internal_lane"


def test_phase20w_repair_blocks_external_lane() -> None:
    allowed, reason = validate_repair_attempt_allowed(
        make_attempt(lane="external_action", action_type="publish_advert")
    )

    assert allowed is False
    assert reason == "repair_forbidden_lane:external_action"


def test_phase20w_repair_blocks_forbidden_action_even_if_lane_claims_safe() -> None:
    allowed, reason = validate_repair_attempt_allowed(
        make_attempt(lane="creation", action_type="send_email_live")
    )

    assert allowed is False
    assert reason == "repair_forbidden_action:send_email_live"


def test_phase20w_repair_blocks_more_than_two_attempts() -> None:
    allowed, reason = validate_repair_attempt_allowed(make_attempt(attempt_index=3))

    assert allowed is False
    assert reason == "max_repair_attempts_exceeded"


def test_phase20w_run_repair_attempt_patches_schema_only_and_resumes() -> None:
    result = run_repair_attempt(make_attempt())

    assert result["repair_allowed"] is True
    assert result["repair_succeeded"] is True
    assert result["runtime_state"] == "running_autonomous_steps"
    assert result["repaired_payload"]["title"] == ""
    assert result["repaired_payload"]["description"] == ""
    assert result["repaired_payload"]["draft"] == "Draft ad"
    assert result["repaired_payload"]["repair_metadata"]["live_side_effects_enabled"] is False
    assert result["live_side_effects_enabled"] is False
    assert result["repair_hash"].startswith("sha256:")


def test_phase20w_forbidden_repair_transitions_to_human_review() -> None:
    result = run_repair_attempt(
        make_attempt(lane="financial_action", action_type="take_payment")
    )

    assert result["repair_allowed"] is False
    assert result["repair_succeeded"] is False
    assert result["runtime_state"] == "waiting_human_review"
    assert result["live_side_effects_enabled"] is False


def test_phase20w_final_repair_failure_preserves_attempt_hashes() -> None:
    first = run_repair_attempt(make_attempt(attempt_index=1))
    second = run_repair_attempt(make_attempt(attempt_index=2))

    result = final_repair_failure_result(
        mission_id="mission_001",
        mission_run_id="run_001",
        step_id="step_001",
        action_type="draft_offer",
        lane="creation",
        attempts=[first, second],
    )

    assert result["runtime_state"] == "waiting_human_review"
    assert result["repair_succeeded"] is False
    assert result["attempt_count"] == 2
    assert len(result["attempt_hashes"]) == 2
    assert result["failure_hash"].startswith("sha256:")


def test_phase20w_repair_hash_is_deterministic() -> None:
    first = run_repair_attempt(make_attempt())
    second = run_repair_attempt(make_attempt())

    assert first["repair_hash"] == second["repair_hash"]


def test_phase20w1_repair_pedigree_accepts_omitted_lane_and_action() -> None:
    from backend.services.aion_mission_mode.self_repair_runtime import (
        validate_repair_pedigree_immutability,
    )

    ok, reason = validate_repair_pedigree_immutability(
        failed_lane="creation",
        failed_action_type="draft_offer",
        repaired_payload={"draft": "safe repaired payload"},
    )

    assert ok is True
    assert reason == "repair_pedigree_immutable"


def test_phase20w1_repair_pedigree_blocks_lane_escalation() -> None:
    from backend.services.aion_mission_mode.self_repair_runtime import (
        validate_repair_pedigree_immutability,
    )

    ok, reason = validate_repair_pedigree_immutability(
        failed_lane="creation",
        failed_action_type="draft_offer",
        repaired_payload={
            "lane": "external_action",
            "action_type": "draft_offer",
            "draft": "unsafe escalation",
        },
    )

    assert ok is False
    assert reason == "repair_lane_escalation_intercepted"


def test_phase20w1_repair_pedigree_blocks_action_mutation() -> None:
    from backend.services.aion_mission_mode.self_repair_runtime import (
        validate_repair_pedigree_immutability,
    )

    ok, reason = validate_repair_pedigree_immutability(
        failed_lane="creation",
        failed_action_type="draft_offer",
        repaired_payload={
            "lane": "creation",
            "action_type": "publish_advert",
            "draft": "unsafe action mutation",
        },
    )

    assert ok is False
    assert reason == "repair_action_mutation_intercepted"


def test_phase20w1_repair_attempt_with_pedigree_adds_chained_hash() -> None:
    from backend.services.aion_mission_mode.self_repair_runtime import (
        run_repair_attempt_with_pedigree,
    )

    first = run_repair_attempt_with_pedigree(make_attempt(attempt_index=1))
    second = run_repair_attempt_with_pedigree(
        make_attempt(attempt_index=2),
        previous_repair_hash=first["repair_hash"],
    )

    assert first["pedigree_immutable"] is True
    assert second["pedigree_immutable"] is True
    assert second["previous_repair_hash"] == first["repair_hash"]
    assert second["chained_repair_hash"].startswith("sha256:")
    assert first["chained_repair_hash"] != second["chained_repair_hash"]


def test_phase20w1_repair_hash_chain_is_deterministic() -> None:
    from backend.services.aion_mission_mode.self_repair_runtime import (
        run_repair_attempt_with_pedigree,
    )

    first = run_repair_attempt_with_pedigree(
        make_attempt(attempt_index=2),
        previous_repair_hash="sha256:previous",
    )
    second = run_repair_attempt_with_pedigree(
        make_attempt(attempt_index=2),
        previous_repair_hash="sha256:previous",
    )

    assert first["chained_repair_hash"] == second["chained_repair_hash"]
    assert first["repair_hash"] == second["repair_hash"]
