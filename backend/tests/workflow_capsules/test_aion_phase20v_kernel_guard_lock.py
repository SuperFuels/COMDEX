from backend.services.aion_mission_mode.kernel_guard import (
    RESTRICTED_ACTION_REGISTRY,
    inspect_kernel_batch,
    inspect_kernel_payload,
)


def test_phase20v_kernel_guard_registry_contains_restricted_actions() -> None:
    assert RESTRICTED_ACTION_REGISTRY["send_email_live"] == "external_action"
    assert RESTRICTED_ACTION_REGISTRY["capture_payment_live"] == "financial_action"
    assert RESTRICTED_ACTION_REGISTRY["deploy_production_live"] == "deployment_action"
    assert RESTRICTED_ACTION_REGISTRY["write_live_reputation"] == "memory_mutation"


def test_phase20v_safe_action_mounts_runtime() -> None:
    decision = inspect_kernel_payload({
        "action_type": "draft_offer",
        "title": "Draft campaign offer",
        "decision": "safe_autonomous",
    })

    assert decision.final_decision == "safe_autonomous"
    assert decision.runtime_mount_allowed is True
    assert decision.requires_checkpoint is False
    assert decision.reason == "kernel_safe_verified"


def test_phase20v_restricted_action_overrides_safe_label() -> None:
    decision = inspect_kernel_payload({
        "action_type": "send_email_live",
        "title": "Send customer email",
        "decision": "safe_autonomous",
    })

    assert decision.final_decision == "checkpoint_required"
    assert decision.runtime_mount_allowed is False
    assert decision.requires_checkpoint is True
    assert decision.override_applied is True
    assert decision.reason == "kernel_restricted_action_override"


def test_phase20v_restricted_financial_action_overrides_safe_label() -> None:
    decision = inspect_kernel_payload({
        "action_type": "capture_payment_live",
        "decision": "safe_autonomous",
    })

    assert decision.final_decision == "checkpoint_required"
    assert decision.lane == "financial_action"
    assert decision.runtime_mount_allowed is False


def test_phase20v_nested_runtime_flag_is_forbidden() -> None:
    decision = inspect_kernel_payload({
        "action_type": "draft_offer",
        "decision": "safe_autonomous",
        "payload": {
            "Live-Execution-Enabled": True,
        },
    })

    assert decision.final_decision == "forbidden"
    assert decision.runtime_mount_allowed is False
    assert decision.reason.startswith("kernel_forbidden_runtime_flag:")


def test_phase20v_batch_blocks_runtime_if_one_step_checkpointed() -> None:
    result = inspect_kernel_batch([
        {"action_type": "draft_offer", "decision": "safe_autonomous"},
        {"action_type": "publish_advert", "decision": "safe_autonomous"},
    ])

    assert result["runtime_mount_allowed"] is False
    assert result["mission_runtime_state"] == "waiting_human_review"
    assert result["blocked_or_checkpointed_count"] == 1
    assert result["boardroom_alerts"]
    assert result["kernel_guard_run_hash"].startswith("sha256:")


def test_phase20v_batch_all_safe_can_mount_runtime() -> None:
    result = inspect_kernel_batch([
        {"action_type": "draft_offer", "decision": "safe_autonomous"},
        {"action_type": "draft_facebook_advert", "decision": "safe_autonomous"},
        {"action_type": "create_workflow_preview", "decision": "safe_autonomous"},
    ])

    assert result["runtime_mount_allowed"] is True
    assert result["mission_runtime_state"] == "ready_for_runtime"
    assert result["blocked_or_checkpointed_count"] == 0
    assert result["kernel_guard_run_hash"].startswith("sha256:")


def test_phase20v_guard_hash_is_deterministic() -> None:
    first = inspect_kernel_payload({
        "action_type": "draft_offer",
        "decision": "safe_autonomous",
    })
    second = inspect_kernel_payload({
        "action_type": "draft_offer",
        "decision": "safe_autonomous",
    })

    assert first.guard_hash == second.guard_hash
    assert len(first.guard_hash) == 64


def test_phase20v1_action_type_case_bypass_is_blocked() -> None:
    decision = inspect_kernel_payload({
        "action_type": "send_Email_live",
        "decision": "safe_autonomous",
    })

    assert decision.action_type == "send_email_live"
    assert decision.final_decision == "checkpoint_required"
    assert decision.runtime_mount_allowed is False
    assert decision.reason == "kernel_restricted_action_override"


def test_phase20v1_action_type_hyphen_bypass_is_blocked() -> None:
    decision = inspect_kernel_payload({
        "action_type": "send-email-live",
        "decision": "safe_autonomous",
    })

    assert decision.action_type == "send_email_live"
    assert decision.final_decision == "checkpoint_required"
    assert decision.runtime_mount_allowed is False


def test_phase20v1_action_type_zero_width_space_bypass_is_blocked() -> None:
    decision = inspect_kernel_payload({
        "action_type": "send_\u200bemail_live",
        "decision": "safe_autonomous",
    })

    assert decision.action_type == "send_email_live"
    assert decision.final_decision == "checkpoint_required"
    assert decision.runtime_mount_allowed is False


def test_phase20v1_action_type_unicode_whitespace_bypass_is_blocked() -> None:
    decision = inspect_kernel_payload({
        "action_type": "capture\u00a0payment\u2009live",
        "decision": "safe_autonomous",
    })

    assert decision.action_type == "capture_payment_live"
    assert decision.final_decision == "checkpoint_required"
    assert decision.lane == "financial_action"
    assert decision.runtime_mount_allowed is False
