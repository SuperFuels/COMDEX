import pytest

from backend.services.aion_mission_mode.pilot_feedback_controls import (
    PilotFeedbackContractError,
    PilotFeedbackControls,
)


def base_payload(**overrides):
    payload = {
        "business_id": "home-fixed",
        "mission_id": "mission_pdf_001",
        "mission_run_id": "run_001",
        "step_id": "step_feedback_001",
        "actor_id": "kevin",
        "feedback_action": "revise",
        "feedback_text": "Make the document shorter and add a summary.",
        "current_state": "waiting_user_feedback",
        "mutation_targets": [],
    }
    payload.update(overrides)
    return payload


def test_phase21g_builds_governed_feedback_event():
    event = PilotFeedbackControls.build_feedback_event(base_payload())
    assert event["governed_feedback_event"] is True
    assert event["feedback_action"] == "revise"
    assert event["next_state"] == "revision_requested"
    assert event["feedback_event_hash"].startswith("sha256:")


def test_phase21g_all_controls_are_available():
    view = PilotFeedbackControls.build_feedback_controls_view(
        "mission_pdf_001",
        "run_001",
        "waiting_user_feedback",
    )
    for action in ["approve", "reject", "revise", "stop", "retry", "continue"]:
        assert action in view["available_controls"]
        assert view["visible_controls"][action] is True


def test_phase21g_private_reasoning_is_hidden():
    view = PilotFeedbackControls.build_feedback_controls_view(
        "mission_pdf_001",
        "run_001",
        "waiting_user_feedback",
    )
    assert view["private_reasoning_visible"] is False
    assert view["raw_tool_execution_visible"] is False


def test_phase21g_no_live_action_buttons_by_default():
    view = PilotFeedbackControls.build_feedback_controls_view(
        "mission_pdf_001",
        "run_001",
        "waiting_user_feedback",
    )
    assert view["live_external_action_buttons_visible"] is False


def test_phase21g_blocks_silent_memory_mutation():
    with pytest.raises(PilotFeedbackContractError) as exc:
        PilotFeedbackControls.build_feedback_event(
            base_payload(mutation_targets=["live_memory"])
        )
    assert "live_memory" in str(exc.value)


def test_phase21g_blocks_template_provider_and_reputation_mutation():
    for target in ["reusable_template", "provider_state", "reputation"]:
        with pytest.raises(PilotFeedbackContractError):
            PilotFeedbackControls.build_feedback_event(
                base_payload(mutation_targets=[target])
            )


def test_phase21g_blocks_external_side_effect_feedback_target():
    for target in ["payment", "deployment", "public_post", "message_send", "booking", "escrow"]:
        with pytest.raises(PilotFeedbackContractError):
            PilotFeedbackControls.build_feedback_event(
                base_payload(mutation_targets=[target])
            )


def test_phase21g_feedback_updates_mission_state_safely():
    event = PilotFeedbackControls.build_feedback_event(base_payload(feedback_action="stop"))
    state = PilotFeedbackControls.apply_feedback_to_mission_state(
        {"state": "running_safe_work"},
        event,
    )
    assert state["state"] == "stopped_by_user"
    assert state["external_side_effect_executed"] is False
    assert state["live_memory_mutated"] is False
    assert state["mission_state_hash"].startswith("sha256:")


def test_phase21g_approve_routes_to_existing_approval_chain():
    event = PilotFeedbackControls.build_feedback_event(base_payload(feedback_action="approve"))
    assert event["next_state"] == "waiting_approval_chain"
    assert event["requires_existing_aion_approval_chain"] is True
    assert event["approval_lattice_bypass_allowed"] is False


def test_phase21g_hash_is_deterministic():
    a = PilotFeedbackControls.build_feedback_event(base_payload())
    b = PilotFeedbackControls.build_feedback_event(base_payload())
    assert a["feedback_event_hash"] == b["feedback_event_hash"]
