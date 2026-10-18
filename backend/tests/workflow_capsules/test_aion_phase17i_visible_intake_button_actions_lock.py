from pathlib import Path

APP = Path("desktop/mac/src/app.js")
TEXT = APP.read_text()


def test_phase17i_lock_exists():
    assert "PHASE 17I LOCK: Visible Website Intake button action results" in TEXT
    assert "getAionPhase17IWebsiteIntakeActionState" in TEXT
    assert "setAionPhase17IWebsiteIntakeActionState" in TEXT


def test_phase17i_buttons_call_visible_action_functions():
    assert "testAionPhase17IWebsiteIntakeGmailReadiness" in TEXT
    assert "copyAionPhase17IWebsiteIntakeValue" in TEXT
    assert "sendAionPhase17ILocalPayloadTest" in TEXT


def test_phase17i_result_panel_is_mounted():
    assert "renderAionPhase17IWebsiteIntakeActionResultPanel()" in TEXT
    assert "data-aion-phase17i-action-result" in TEXT
    assert "Website Intake Action Result" in TEXT


def test_phase17i_local_payload_creates_ticket_preview_state():
    assert "ticket_home_fixed_local_payload_test_001" in TEXT
    assert "home_fixed_new_enquiry" in TEXT
    assert "website_intake.trigger.created" in TEXT
    assert "local_preview_ready" in TEXT


def test_phase17i_preserves_safe_mode_guards():
    for phrase in [
        "booking_created: false",
        "payment_created: false",
        "escrow_created: false",
        "external_message_sent: false",
        "live_chain_write: false",
        "live_execution_allowed: false",
        "human_review_required: true",
        "preview_only: true",
    ]:
        assert phrase in TEXT

def test_phase17i_hard_binds_gmail_readiness_button() -> None:
    source = APP.read_text()
    assert "PHASE 17I HOTFIX: Hard-bind visible Gmail readiness button" in source
    assert "runAionPhase17IVisibleGmailReadinessCheck" in source
    assert "installAionPhase17IHardButtonBindings" in source
    assert 'label === "test gmail intake readiness"' in source
    assert 'latest_action: "gmail_readiness_test"' in source
    assert 'readiness_status: status' in source

