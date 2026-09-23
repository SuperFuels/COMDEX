from backend.services.aion_mission_mode.autonomy_lane_classifier import (
    classify_action_type,
    classify_mission_step,
    classify_mission_steps,
    verify_runtime_queue_hash,
)
from backend.services.aion_mission_mode.mission_planner import create_home_fixed_lead_campaign_plan


def test_phase20d_safe_creation_step_is_autonomous() -> None:
    result = classify_mission_step({
        "action_type": "draft_offer",
        "lane": "external_action",
        "decision": "safe_autonomous",
    })

    assert result["lane"] == "creation"
    assert result["decision"] == "safe_autonomous"
    assert result["safe_autonomous"] is True
    assert result["requires_checkpoint"] is False
    assert result["planner_labels_are_advisory_only"] if "planner_labels_are_advisory_only" in result else True


def test_phase20d_external_action_is_checkpoint_required_even_if_planner_says_safe() -> None:
    result = classify_mission_step({
        "action_type": "publish_advert",
        "lane": "creation",
        "decision": "safe_autonomous",
    })

    assert result["lane"] == "external_action"
    assert result["decision"] == "checkpoint_required"
    assert result["safe_autonomous"] is False
    assert result["requires_checkpoint"] is True


def test_phase20d_financial_action_cannot_be_safe_autonomous() -> None:
    lane, decision, reason = classify_action_type("take_payment")

    assert lane == "financial_action"
    assert decision == "checkpoint_required"
    assert "Financial" in reason


def test_phase20d_live_raw_actions_are_forbidden() -> None:
    result = classify_mission_step({
        "action_type": "send_whatsapp_live",
        "lane": "research",
        "decision": "safe_autonomous",
    })

    assert result["decision"] == "forbidden"
    assert result["safe_autonomous"] is False
    assert result["requires_checkpoint"] is True


def test_phase20d_payload_token_blocks_hallucinated_lane_bypass() -> None:
    result = classify_mission_step({
        "action_type": "draft_offer",
        "lane": "creation",
        "decision": "safe_autonomous",
        "payload": {
            "live_execution_enabled": True,
            "external_writes_enabled": True,
        },
    })

    assert result["decision"] == "forbidden"
    assert ("Blocked payload token" in result["reason"]) or ("forbidden_payload_shape" in result["reason"])


def test_phase20d_unknown_action_is_blocked_not_autonomous() -> None:
    result = classify_mission_step({
        "action_type": "invent_new_unregistered_tool",
        "lane": "research",
        "decision": "safe_autonomous",
    })

    assert result["lane"] == "internal_ops"
    assert result["decision"] == "blocked"
    assert result["safe_autonomous"] is False


def test_phase20d_classifies_home_fixed_plan() -> None:
    plan = create_home_fixed_lead_campaign_plan()
    result = classify_mission_steps(plan["steps"])

    assert result["schema_version"] == "aion.autonomy_lane_classifier.v0"
    assert result["planner_labels_are_advisory_only"] is True
    assert result["safe_autonomous_count"] >= 5
    assert result["checkpoint_required_count"] >= 1
    assert result["classifier_run_hash"].startswith("sha256:")
    assert len(result["classifier_run_hash"].removeprefix("sha256:")) == 64

    publish = [
        item for item in result["classifications"]
        if item["action_type"] == "publish_advert"
    ][0]

    assert publish["decision"] == "checkpoint_required"


def test_phase20d_classifier_hash_is_deterministic() -> None:
    step = {
        "action_type": "create_workflow_preview",
        "lane": "external_action",
        "decision": "safe_autonomous",
    }

    first = classify_mission_step(step)
    second = classify_mission_step(step)

    assert first["classifier_hash"] == second["classifier_hash"]
    assert len(first["classifier_hash"]) == 64


def test_phase20d1_safe_action_with_unknown_parameter_is_blocked() -> None:
    result = classify_mission_step({
        "action_type": "draft_offer",
        "title": "Draft offer",
        "unexpected_exec_block": {"note": "not allowed"},
    })

    assert result["decision"] == "blocked"
    assert result["safe_autonomous"] is False
    assert "unapproved_parameter" in result["reason"]


def test_phase20d1_safe_action_with_nested_forbidden_payload_is_forbidden() -> None:
    result = classify_mission_step({
        "action_type": "draft_offer",
        "title": "Draft offer",
        "raw_terminal_exec": {"cmd": "rm -rf /"},
    })

    assert result["decision"] == "forbidden"
    assert result["safe_autonomous"] is False
    assert "forbidden_payload_shape" in result["reason"]


def test_phase20d1_batch_with_blocked_step_cannot_mount_runtime() -> None:
    result = classify_mission_steps([
        {"action_type": "draft_offer", "title": "Draft offer"},
        {"action_type": "unknown_tool", "title": "Unknown tool"},
    ])

    assert result["batch_valid"] is False
    assert result["runtime_mount_allowed"] is False
    assert result["mission_runtime_state"] == "waiting_human_review"
    assert result["blocked_count"] == 1


def test_phase20d1_batch_with_forbidden_step_blocks_mission() -> None:
    result = classify_mission_steps([
        {"action_type": "draft_offer", "title": "Draft offer"},
        {"action_type": "send_email_live", "title": "Send live email"},
    ])

    assert result["batch_valid"] is False
    assert result["runtime_mount_allowed"] is False
    assert result["mission_runtime_state"] == "blocked"
    assert result["forbidden_count"] == 1


def test_phase20d1_classifier_run_hash_uses_sha256_prefix_and_is_stable() -> None:
    steps = [
        {"action_type": "draft_offer", "title": "Draft offer"},
        {"action_type": "publish_advert", "title": "Publish advert"},
    ]

    first = classify_mission_steps(steps)
    second = classify_mission_steps(steps)

    assert first["classifier_run_hash"] == second["classifier_run_hash"]
    assert first["classifier_run_hash"].startswith("sha256:")


def test_phase20d2_forbidden_key_case_bypass_is_normalised() -> None:
    result = classify_mission_step({
        "action_type": "draft_offer",
        "Live_Execution_Enabled": True,
    })

    assert result["decision"] == "forbidden"
    assert "forbidden_payload_shape" in result["reason"]


def test_phase20d2_forbidden_key_hyphen_bypass_is_normalised() -> None:
    result = classify_mission_step({
        "action_type": "draft_offer",
        "live-execution-enabled": True,
    })

    assert result["decision"] == "forbidden"
    assert "forbidden_payload_shape" in result["reason"]


def test_phase20d2_forbidden_key_unicode_whitespace_bypass_is_normalised() -> None:
    result = classify_mission_step({
        "action_type": "draft_offer",
        " live\u00a0execution\u2009enabled ": True,
    })

    assert result["decision"] == "forbidden"
    assert "forbidden_payload_shape" in result["reason"]


def test_phase20d2_jit_runtime_queue_hash_accepts_unchanged_batch() -> None:
    classifier_result = classify_mission_steps([
        {"action_type": "draft_offer", "title": "Draft offer"},
        {"action_type": "publish_advert", "title": "Publish advert"},
    ])

    verify = verify_runtime_queue_hash(
        classifier_result=classifier_result,
        runtime_classifications=classifier_result["classifications"],
    )

    assert verify["ok"] is True
    assert verify["runtime_mount_allowed"] is True
    assert verify["trace_event"] is None


def test_phase20d2_jit_runtime_queue_hash_blocks_mutated_batch() -> None:
    classifier_result = classify_mission_steps([
        {"action_type": "draft_offer", "title": "Draft offer"},
        {"action_type": "publish_advert", "title": "Publish advert"},
    ])

    mutated = list(classifier_result["classifications"])
    mutated[0] = {**mutated[0], "action_type": "send_email_live"}

    verify = verify_runtime_queue_hash(
        classifier_result=classifier_result,
        runtime_classifications=mutated,
    )

    assert verify["ok"] is False
    assert verify["runtime_mount_allowed"] is False
    assert verify["mission_runtime_state"] == "blocked"
    assert verify["trace_event"] == "classifier_runtime_hash_mismatch"
    assert "hash mismatch" in verify["boardroom_alert"].lower()
