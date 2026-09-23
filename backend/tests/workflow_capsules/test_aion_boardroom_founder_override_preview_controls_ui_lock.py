from pathlib import Path

APP = Path("desktop/mac/src/app.js")

def _text() -> str:
    assert APP.exists(), "desktop/mac/src/app.js must exist"
    return APP.read_text()

def test_founder_override_preview_controls_renderer_exists():
    text = _text()
    assert "installBoardroomFounderOverridePreviewControlsV0" in text
    assert "renderBoardroomFounderOverridePreviewControlsV0" in text
    assert "window.renderBoardroomFounderOverridePreviewControlsV0" in text
    assert "boardroom-founder-override-preview-controls-v0" in text

def test_founder_override_preview_actions_are_present():
    text = _text()
    section_start = text.find("installBoardroomFounderOverridePreviewControlsV0")
    assert section_start >= 0
    section = text[section_start:]

    for term in [
        "approve",
        "reject",
        "request_evidence",
        "escalate",
        "pause",
        "Approve",
        "Reject",
        "Request Evidence",
        "Escalate",
        "Pause",
    ]:
        assert term in section

def test_founder_override_controls_are_disabled_preview_only():
    text = _text()
    section_start = text.find("installBoardroomFounderOverridePreviewControlsV0")
    assert section_start >= 0
    section = text[section_start:]

    for term in [
        "Preview only",
        "disabled",
        "aria-disabled",
        "future_guarded_approval_path",
        "human_review_required",
    ]:
        assert term in section

def test_founder_override_preserves_no_live_action_boundary():
    text = _text()
    section_start = text.find("installBoardroomFounderOverridePreviewControlsV0")
    assert section_start >= 0
    section = text[section_start:]

    for term in [
        "autonomous_execution_allowed",
        "would_execute_workflow",
        "would_create_booking",
        "would_move_money",
        "would_move_pho",
        "would_require_wallet",
        "would_create_payment",
        "would_create_escrow",
        "would_send_external_message",
        "public_a2a_route_exposed",
    ]:
        assert term in section

def test_founder_override_does_not_expose_live_execution_copy():
    text = _text()
    section_start = text.find("installBoardroomFounderOverridePreviewControlsV0")
    assert section_start >= 0
    section = text[section_start:]

    banned = [
        "Execute Now",
        "Run Live",
        "Create Booking",
        "Take Payment",
        "Create Escrow",
        "Send Message",
        "Charge Customer",
        "Submit Public A2A",
    ]

    for term in banned:
        assert term not in section
