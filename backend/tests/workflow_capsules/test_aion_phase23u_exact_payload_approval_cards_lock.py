from backend.services.aion_mission_mode.department_execution_queue import create_department_queue_item
from backend.services.aion_mission_mode.pilot_tool_approval_cards import (
    apply_exact_payload_approval_to_tool_execution_item,
    create_exact_payload_approval_card,
    create_exact_payload_approval_decision,
    evaluate_exact_payload_approval,
)
from backend.services.aion_mission_mode.pilot_tool_execution_queue import create_tool_execution_item


def make_live_tool_item():
    queue_item = create_department_queue_item(
        business_id="home-fixed",
        mission_id="mission_23u",
        mission_run_id="run_001",
        department_id="marketing",
        capability="social.publish",
        title="Publish post",
        task_type="marketing_live_action",
        task_index=0,
    )
    return create_tool_execution_item(
        queue_item=queue_item,
        evaluation_time=100,
    )


def test_phase23u_creates_exact_payload_approval_card_for_live_tool_item():
    tool_item = make_live_tool_item()
    card = create_exact_payload_approval_card(
        tool_execution_item=tool_item,
        approval_expires_at=200,
    )

    assert card["approval_type"] == "exact_payload_approval"
    assert card["expected_payload_hash"] == tool_item["payload_hash"]
    assert card["approval_required"] is True
    assert card["approval_state"] == "waiting_exact_payload_approval"
    assert card["live_execution_allowed"] is False
    assert card["external_side_effect_executed"] is False
    assert card["approval_card_hash"].startswith("sha256:")


def test_phase23u_missing_approval_is_blocked():
    tool_item = make_live_tool_item()
    card = create_exact_payload_approval_card(
        tool_execution_item=tool_item,
        approval_expires_at=200,
    )

    evaluation = evaluate_exact_payload_approval(
        approval_card=card,
        approval_decision=None,
        evaluation_time=100,
    )

    assert evaluation["allowed"] is False
    assert "approval_card_hash_mismatch" in evaluation["reasons"]
    assert "approval_not_granted" in evaluation["reasons"]
    assert "missing_approval_hash" in evaluation["reasons"]
    assert evaluation["external_side_effect_executed"] is False


def test_phase23u_mismatched_payload_hash_is_blocked():
    tool_item = make_live_tool_item()
    card = create_exact_payload_approval_card(
        tool_execution_item=tool_item,
        approval_expires_at=200,
    )
    decision = create_exact_payload_approval_decision(
        approval_card=card,
        approved=True,
        approved_payload_hash="sha256:wrong",
        approval_time=100,
        approval_expires_at=200,
    )

    evaluation = evaluate_exact_payload_approval(
        approval_card=card,
        approval_decision=decision,
        evaluation_time=100,
    )

    assert evaluation["allowed"] is False
    assert "approved_payload_hash_mismatch" in evaluation["reasons"]


def test_phase23u_expired_approval_is_blocked():
    tool_item = make_live_tool_item()
    card = create_exact_payload_approval_card(
        tool_execution_item=tool_item,
        approval_expires_at=120,
    )
    decision = create_exact_payload_approval_decision(
        approval_card=card,
        approved=True,
        approval_time=100,
        approval_expires_at=120,
    )

    evaluation = evaluate_exact_payload_approval(
        approval_card=card,
        approval_decision=decision,
        evaluation_time=121,
    )

    assert evaluation["allowed"] is False
    assert "approval_expired" in evaluation["reasons"]


def test_phase23u_valid_exact_approval_passes_gateway_but_does_not_execute_live_action():
    tool_item = make_live_tool_item()
    card = create_exact_payload_approval_card(
        tool_execution_item=tool_item,
        approval_expires_at=200,
    )
    decision = create_exact_payload_approval_decision(
        approval_card=card,
        approved=True,
        approval_time=100,
        approval_expires_at=200,
    )

    approved_item = apply_exact_payload_approval_to_tool_execution_item(
        tool_execution_item=tool_item,
        approval_card=card,
        approval_decision=decision,
        evaluation_time=100,
    )

    assert approved_item["exact_payload_approval"]["allowed"] is True
    assert approved_item["gateway_allowed"] is True
    assert approved_item["gateway_state"] == "allowed"
    assert approved_item["status"] == "waiting_live_executor"
    assert approved_item["execution_allowed"] is False
    assert approved_item["live_execution_allowed"] is False
    assert approved_item["external_side_effect_executed"] is False
    assert approved_item["approval_hash"].startswith("sha256:")


def test_phase23u_current_payload_hash_change_requires_fresh_approval():
    tool_item = make_live_tool_item()
    card = create_exact_payload_approval_card(
        tool_execution_item=tool_item,
        approval_expires_at=200,
    )
    decision = create_exact_payload_approval_decision(
        approval_card=card,
        approved=True,
        approval_time=100,
        approval_expires_at=200,
    )

    evaluation = evaluate_exact_payload_approval(
        approval_card=card,
        approval_decision=decision,
        current_payload_hash="sha256:changed",
        evaluation_time=100,
    )

    assert evaluation["allowed"] is False
    assert "current_payload_hash_mismatch_requires_fresh_approval" in evaluation["reasons"]
