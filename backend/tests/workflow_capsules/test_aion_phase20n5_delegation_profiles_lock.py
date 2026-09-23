import pytest

from backend.services.aion_mission_mode.delegation_profiles import (
    apply_delegation_profile_to_steps,
    classify_step_tool_mode,
    profile_default_decision_for_step,
    profile_defaults,
    profile_summary,
    validate_profile,
)


def test_phase20n5_profiles_exist() -> None:
    assert validate_profile("safe_draft_mode") == "safe_draft_mode"
    assert validate_profile("business_setup_mode") == "business_setup_mode"
    assert validate_profile("trusted_operator_mode") == "trusted_operator_mode"
    assert validate_profile("emergency_lockdown_mode") == "emergency_lockdown_mode"


def test_phase20n5_unknown_profile_rejected() -> None:
    with pytest.raises(ValueError):
        validate_profile("unlimited_god_mode")


def test_phase20n5_profile_defaults_hash_deterministic() -> None:
    first = profile_defaults("business_setup_mode")
    second = profile_defaults("business_setup_mode")
    assert first["profile_defaults_hash"] == second["profile_defaults_hash"]


def test_phase20n5_safe_draft_blocks_external_reads_by_default() -> None:
    defaults = profile_defaults("safe_draft_mode")
    assert defaults["max_external_reads"] == 0
    assert defaults["default_read_only_external"] == "human_approval_required"


def test_phase20n5_business_setup_allows_read_only_external() -> None:
    defaults = profile_defaults("business_setup_mode")
    assert defaults["max_external_reads"] == 25
    assert defaults["default_read_only_external"] == "autonomous"


def test_phase20n5_trusted_operator_allows_staged_external_not_live_external() -> None:
    defaults = profile_defaults("trusted_operator_mode")
    assert defaults["default_staged_external"] == "autonomous"
    assert defaults["default_live_external"] == "human_approval_required"


def test_phase20n5_emergency_lockdown_blocks_everything() -> None:
    defaults = profile_defaults("emergency_lockdown_mode")
    assert defaults["default_safe_internal"] == "blocked"
    assert defaults["default_read_only_external"] == "blocked"
    assert defaults["default_staged_external"] == "blocked"
    assert defaults["default_live_external"] == "blocked"


def test_phase20n5_tool_mode_classification() -> None:
    assert classify_step_tool_mode({"lane": "creation"}) == "safe_internal"
    assert classify_step_tool_mode({"lane": "read_only_external"}) == "read_only_external"
    assert classify_step_tool_mode({"action_type": "prepare_vercel_deploy"}) == "staged_external"
    assert classify_step_tool_mode({"action_type": "buy_domain"}) == "approved_live_external"


def test_phase20n5_human_task_actions_remain_human_task() -> None:
    step = {"action_type": "create_real_facebook_account", "lane": "identity_action"}
    assert profile_default_decision_for_step("trusted_operator_mode", step) == "human_task_required"


def test_phase20n5_always_approval_actions_remain_approval_required() -> None:
    step = {"action_type": "buy_domain", "lane": "financial_action"}
    assert profile_default_decision_for_step("trusted_operator_mode", step) == "human_approval_required"


def test_phase20n5_emergency_lockdown_forces_blocked() -> None:
    step = {"action_type": "draft_copy", "lane": "creation"}
    assert profile_default_decision_for_step("emergency_lockdown_mode", step) == "blocked"


def test_phase20n5_profile_application_cannot_bypass_system_decision() -> None:
    steps = [
        {
            "step_id": "buy_domain",
            "action_type": "buy_domain",
            "lane": "financial_action",
            "system_decision": "human_approval_required",
        }
    ]

    result = apply_delegation_profile_to_steps(
        mission_id="mission_001",
        mission_run_id="run_001",
        plan_id="plan_001",
        profile="trusted_operator_mode",
        steps=steps,
    )

    resolution = result["lattice_result"]["resolutions"][0]
    assert resolution["effective_decision"] == "human_approval_required"
    assert result["runtime_mount_allowed"] is True


def test_phase20n5_profile_application_blocks_unsafe_user_downgrade() -> None:
    steps = [
        {
            "step_id": "deploy",
            "action_type": "deploy_to_production",
            "lane": "deployment_action",
            "system_decision": "human_approval_required",
            "user_override": "autonomous",
        }
    ]

    result = apply_delegation_profile_to_steps(
        mission_id="mission_001",
        mission_run_id="run_001",
        plan_id="plan_001",
        profile="trusted_operator_mode",
        steps=steps,
    )

    assert result["runtime_mount_allowed"] is False
    assert result["lattice_result"]["policy_override_violation_count"] == 1


def test_phase20n5_safe_draft_mode_keeps_safe_internal_autonomous() -> None:
    steps = [
        {
            "step_id": "draft_copy",
            "action_type": "draft_copy",
            "lane": "creation",
            "system_decision": "autonomous",
        }
    ]

    result = apply_delegation_profile_to_steps(
        mission_id="mission_001",
        mission_run_id="run_001",
        plan_id="plan_001",
        profile="safe_draft_mode",
        steps=steps,
    )

    resolution = result["lattice_result"]["resolutions"][0]
    assert resolution["effective_decision"] == "autonomous"


def test_phase20n5_emergency_lockdown_profile_blocks_safe_internal() -> None:
    steps = [
        {
            "step_id": "draft_copy",
            "action_type": "draft_copy",
            "lane": "creation",
            "system_decision": "autonomous",
        }
    ]

    result = apply_delegation_profile_to_steps(
        mission_id="mission_001",
        mission_run_id="run_001",
        plan_id="plan_001",
        profile="emergency_lockdown_mode",
        steps=steps,
    )

    resolution = result["lattice_result"]["resolutions"][0]
    assert resolution["effective_decision"] == "blocked"
    assert result["runtime_mount_allowed"] is True


def test_phase20n5_profile_application_hash_is_deterministic() -> None:
    steps = [
        {
            "step_id": "draft_copy",
            "action_type": "draft_copy",
            "lane": "creation",
            "system_decision": "autonomous",
        }
    ]

    first = apply_delegation_profile_to_steps(
        mission_id="mission_001",
        mission_run_id="run_001",
        plan_id="plan_001",
        profile="business_setup_mode",
        steps=steps,
    )
    second = apply_delegation_profile_to_steps(
        mission_id="mission_001",
        mission_run_id="run_001",
        plan_id="plan_001",
        profile="business_setup_mode",
        steps=steps,
    )

    assert first["profile_application_hash"] == second["profile_application_hash"]


def test_phase20n5_profile_summary_shows_no_unapproved_live_actions() -> None:
    summary = profile_summary("trusted_operator_mode")

    assert summary["unapproved_spend_allowed"] is False
    assert summary["unapproved_public_posts_allowed"] is False
    assert summary["unapproved_deployments_allowed"] is False
    assert summary["summary_hash"].startswith("sha256:")
