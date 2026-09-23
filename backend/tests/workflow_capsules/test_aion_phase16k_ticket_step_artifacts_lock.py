from pathlib import Path

APP = Path("desktop/mac/src/app.js")
CSS = Path("desktop/mac/src/styles.css")
DOC = Path("docs/rfc/aion_phase16k_ticket_step_artifacts_lock.tex")
SUITE = Path("scripts/run_goal_engine_focused_lock_suite.sh")


def test_phase16k_lock_markers_exist():
    text = APP.read_text()
    css = CSS.read_text()
    assert "PHASE 16K LOCK: Ticket step artifacts" in text
    assert "PHASE 16K LOCK: Ticket step artifacts" in css
    assert DOC.exists()


def test_phase16k_artifact_functions_exist():
    text = APP.read_text()
    assert "function getAionFounderDemoTicketStepArtifact" in text
    assert "function renderAionFounderDemoTicketStepArtifactPanel" in text
    assert "data-aion-ticket-step-artifact" in text


def test_phase16k_every_ticket_step_has_visible_artifact():
    text = APP.read_text()
    for phrase in [
        "Website request received",
        "Inbound request normalized",
        "Safety boundary applied",
        "Business capability selected",
        "Quote preview generated",
        "Founder approval required",
        "Proof receipt preview available",
        "Replay timeline ready",
    ]:
        assert phrase in text


def test_phase16k_artifact_panel_is_mounted_after_ticket_panel():
    text = APP.read_text()
    assert "renderAionFounderDemoTicketRunPanel()" in text
    assert "renderAionFounderDemoTicketStepArtifactPanel(state)" in text
    assert text.index("renderAionFounderDemoTicketRunPanel()") < text.index("renderAionFounderDemoTicketStepArtifactPanel(state)")


def test_phase16k_artifacts_keep_side_effect_boundary_visible_once():
    text = APP.read_text()
    assert "No booking · No payment · No escrow · No external message · No live chain write" in text


def test_phase16k_css_exists():
    css = CSS.read_text()
    for selector in [
        ".aion-ticket-step-artifact",
        ".aion-ticket-step-artifact-head",
        ".aion-ticket-step-artifact-grid",
    ]:
        assert selector in css


def test_phase16k_is_in_focused_suite():
    suite = SUITE.read_text()
    assert "test_aion_phase16k_ticket_step_artifacts_lock.py" in suite
