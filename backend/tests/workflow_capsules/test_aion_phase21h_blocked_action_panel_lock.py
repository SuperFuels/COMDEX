from backend.services.aion_mission_mode.pilot_blocked_action_panel import (
    PilotBlockedActionPanel,
    PilotBlockedActionPanelError,
)


def base_blocked_action(**overrides):
    payload = {
        "business_id": "home-fixed",
        "mission_id": "mission_pdf_001",
        "mission_run_id": "run_001",
        "step_id": "step_domain_001",
        "action_id": "blocked_domain_purchase_001",
        "action_type": "domain_purchase",
        "blocked_reason": "Domain purchase requires exact payload approval.",
        "would_have_happened": "AION would have purchased a live domain.",
        "safe_alternative": "Prepare a domain checkout preview and wait for approval.",
        "required_approval": "exact_payload_approval",
        "timeline_hash": "sha256:timeline",
        "proof_hash": "sha256:proof",
        "outcome_summary_hash": "sha256:outcome",
    }
    payload.update(overrides)
    return payload


def test_phase21h_builds_blocked_action_record():
    record = PilotBlockedActionPanel.build_blocked_action_record(base_blocked_action())
    assert record["blocked_state"] == "blocked_for_safety"
    assert record["live_action_blocked"] is True
    assert record["blocked_action_hash"].startswith("sha256:")


def test_phase21h_record_shows_required_safety_fields():
    record = PilotBlockedActionPanel.build_blocked_action_record(base_blocked_action())
    assert record["blocked_reason"]
    assert record["would_have_happened"]
    assert record["safe_alternative"]
    assert record["required_approval"] == "exact_payload_approval"


def test_phase21h_record_links_to_timeline_proof_and_outcome():
    record = PilotBlockedActionPanel.build_blocked_action_record(base_blocked_action())
    assert record["timeline_hash"] == "sha256:timeline"
    assert record["proof_hash"] == "sha256:proof"
    assert record["outcome_summary_hash"] == "sha256:outcome"


def test_phase21h_panel_renders_all_safety_fields():
    record = PilotBlockedActionPanel.build_blocked_action_record(base_blocked_action())
    panel = PilotBlockedActionPanel.build_panel_view([record])
    assert panel["shows_blocked_reason"] is True
    assert panel["shows_would_have_happened"] is True
    assert panel["shows_safe_alternative"] is True
    assert panel["shows_required_approval"] is True


def test_phase21h_panel_is_read_model_not_execution_surface():
    record = PilotBlockedActionPanel.build_blocked_action_record(base_blocked_action())
    panel = PilotBlockedActionPanel.build_panel_view([record])
    assert panel["live_external_action_buttons_visible"] is False
    assert panel["raw_tool_execution_visible"] is False
    assert panel["private_reasoning_visible"] is False


def test_phase21h_blocked_live_action_cannot_continue_without_approval():
    record = PilotBlockedActionPanel.build_blocked_action_record(base_blocked_action())
    assertion = PilotBlockedActionPanel.assert_cannot_continue_without_exact_approval(record)
    assert assertion["continue_allowed"] is False
    assert assertion["reason"] == "blocked_action_cannot_continue_without_exact_approval"


def test_phase21h_exact_approval_can_clear_continue_assertion():
    record = PilotBlockedActionPanel.build_blocked_action_record(base_blocked_action())
    assertion = PilotBlockedActionPanel.assert_cannot_continue_without_exact_approval(
        record,
        {
            "approval_type": "exact_payload_approval",
            "approved": True,
            "payload_hash": "sha256:payload",
            "expected_payload_hash": "sha256:payload",
        },
    )
    assert assertion["continue_allowed"] is True
    assert assertion["external_side_effect_executed"] is False


def test_phase21h_invalid_required_approval_is_rejected():
    try:
        PilotBlockedActionPanel.build_blocked_action_record(
            base_blocked_action(required_approval="random_approval")
        )
    except PilotBlockedActionPanelError as exc:
        assert "unsupported required approval" in str(exc)
    else:
        raise AssertionError("expected PilotBlockedActionPanelError")


def test_phase21h_hash_is_deterministic():
    a = PilotBlockedActionPanel.build_blocked_action_record(base_blocked_action())
    b = PilotBlockedActionPanel.build_blocked_action_record(base_blocked_action())
    assert a["blocked_action_hash"] == b["blocked_action_hash"]


def test_phase21h_required_safety_message_is_present():
    record = PilotBlockedActionPanel.build_blocked_action_record(base_blocked_action())
    panel = PilotBlockedActionPanel.build_panel_view([record])
    assert panel["safety_message"] == "AION stopped itself before doing anything risky."
