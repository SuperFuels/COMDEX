from pathlib import Path

APP = Path("desktop/mac/src/app.js")
CSS = Path("desktop/mac/src/styles.css")
DOC = Path("docs/rfc/aion_phase17g_home_fixed_live_test_actions_lock.tex")
SUITE = Path("scripts/run_goal_engine_focused_lock_suite.sh")


def test_phase17g_lock_markers_exist():
    text = APP.read_text()
    css = CSS.read_text()

    assert "PHASE 17G LOCK: Home Fixed live intake test actions" in text
    assert "PHASE 17G LOCK: Home Fixed live intake test actions" in css
    assert DOC.exists()


def test_phase17g_installation_panel_has_gmail_vault_setup_actions():
    text = APP.read_text()

    for phrase in [
        "Gmail",
        "Vault",
        "Copy webhook endpoint",
        "sendAionPhase17GHomeFixedTestEnquiry",
        "data-aion-phase17g-live-actions",
    ]:
        assert phrase in text


def test_phase17g_no_fake_hosted_mailbox_is_visible():
    text = APP.read_text()

    assert "home_fixed@intake.tessaris.ai" not in text
    assert "https://api.tessaris.ai/public/intake/home_fixed" in text


def test_phase17g_test_submission_payload_is_realistic():
    text = APP.read_text()

    for phrase in [
        "buildAionPhase17GHomeFixedTestSubmission",
        "ticket_home_fixed_live_test_001",
        "home_fixed_new_enquiry",
        "website_intake.trigger.created",
        "workflow_ticket_preview_created",
        "Pergola / roof repair",
        "Arboleas, Almería",
    ]:
        assert phrase in text


def test_phase17g_send_test_enquiry_updates_boardroom_state():
    text = APP.read_text()

    for phrase in [
        "sendAionPhase17GHomeFixedTestEnquiry",
        "setAionFounderDemoLoopState",
        "Home Fixed live test enquiry received",
        "Workflow ticket preview created",
        "machine_cart_quote_preview",
    ]:
        assert phrase in text


def test_phase17g_result_panel_is_mounted():
    text = APP.read_text()

    assert "function renderAionPhase17GLiveTestResultPanel" in text
    assert "renderAionPhase17GLiveTestResultPanel()" in text
    assert "data-aion-phase17g-test-result" in text


def test_phase17g_preserves_side_effect_guards():
    text = APP.read_text()

    for phrase in [
        "booking_created: false",
        "payment_created: false",
        "escrow_created: false",
        "external_message_sent: false",
        "live_chain_write: false",
        "human_review_required: true",
    ]:
        assert phrase in text


def test_phase17g_is_in_focused_suite():
    suite = SUITE.read_text()
    assert "test_aion_phase17g_home_fixed_live_test_actions_lock.py" in suite
