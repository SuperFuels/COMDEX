from pathlib import Path

APP = Path("desktop/mac/src/app.js")
SUITE = Path("scripts/run_goal_engine_focused_lock_suite.sh")
DOC = Path("docs/rfc/aion_phase17h_functional_website_intake_actions_lock.tex")


def text() -> str:
    return APP.read_text()


def test_phase17h_lock_markers_exist() -> None:
    source = text()
    assert "PHASE 17H LOCK: Functional Website Intake actions" in source
    assert "END PHASE 17H LOCK" in source


def test_phase17h_provider_selection_handler_exists() -> None:
    source = text()
    assert "function selectAionPhase17HWebsiteIntakeProvider" in source
    assert "selected_provider" in source
    assert "data-aion-intake-provider-option" in source
    assert "is-selected" in source


def test_phase17h_gmail_readiness_action_updates_visible_result_state() -> None:
    source = text()
    assert "function testAionPhase17HGmailIntakeReadiness" in source
    assert "getAionPhase17GGmailVaultReadiness" in source
    assert "ready_for_guarded_read" in source
    assert "vault_missing_or_incomplete" in source
    assert "Gmail OAuth is not ready yet" in source


def test_phase17h_copy_handler_uses_clipboard_and_visible_status() -> None:
    source = text()
    assert "function copyAionPhase17HWebsiteIntakeValue" in source
    assert "navigator.clipboard.writeText" in source
    assert "copied_field" in source
    assert "Copied field" in source


def test_phase17h_local_payload_test_wraps_phase17g_preview_only() -> None:
    source = text()
    assert "function sendAionPhase17HLocalPayloadTest" in source
    assert "sendAionPhase17GHomeFixedTestEnquiry" in source
    assert "local_payload_test" in source
    assert "preview ticket only" in source


def test_phase17h_result_panel_is_mounted() -> None:
    source = text()
    assert "function renderAionPhase17HWebsiteIntakeActionResultPanel" in source
    assert "renderAionPhase17HWebsiteIntakeActionResultPanel()" in source
    assert "data-aion-phase17h-action-result" in source


def test_phase17h_no_raw_passwords_and_no_live_send() -> None:
    source = text()
    assert "Raw passwords" in source
    assert "Not allowed" in source
    assert "Live send" in source
    assert "Locked" in source
    assert "live_send_allowed: false" in source


def test_phase17h_is_in_focused_suite_and_doc_exists() -> None:
    assert DOC.exists()
    assert "test_aion_phase17h_functional_website_intake_actions_lock.py" in SUITE.read_text()

def test_phase17h_click_bindings_are_delegated_and_installed() -> None:
    source = text()
    assert "installAionPhase17HWebsiteIntakeClickBindings" in source
    assert "data-aion-phase17h-action" in source
    assert "document.addEventListener(\"click\"" in source
    assert "Phase 17H Website Intake click bindings installed" in source


def test_phase17h_functions_are_exported_to_window_for_inline_fallback() -> None:
    source = text()
    assert "window.testAionPhase17HGmailIntakeReadiness" in source
    assert "window.copyAionPhase17HWebsiteIntakeValue" in source
    assert "window.sendAionPhase17HLocalPayloadTest" in source
    assert "window.selectAionPhase17HWebsiteIntakeProvider" in source


def test_phase17h_has_visible_top_action_status() -> None:
    source = text()
    assert "data-aion-phase17h-top-status" in source
    assert "Action status:" in source
    assert "latest_action" in source

