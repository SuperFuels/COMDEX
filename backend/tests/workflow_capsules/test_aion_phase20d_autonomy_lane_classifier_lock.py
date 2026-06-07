from backend.services.aion_mission_mode.autonomy_lane_classifier import (
    classify_action_type,
    classify_mission_step,
    classify_mission_steps,
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
    assert "Blocked payload token" in result["reason"]


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
    assert len(result["classifier_run_hash"]) == 64

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
