from pathlib import Path

APP = Path("desktop/mac/src/app.js")
CSS = Path("desktop/mac/src/styles.css")
DOC = Path("docs/rfc/aion_phase17e_boardroom_ticket_ui_simplification_lock.tex")
SUITE = Path("scripts/run_goal_engine_focused_lock_suite.sh")


def test_phase17e_lock_markers_exist():
    text = APP.read_text()
    css = CSS.read_text()

    assert "PHASE 17E LOCK: Boardroom website intake ticket UI simplification" in text
    assert "PHASE 17E LOCK: Boardroom website intake ticket UI simplification" in css
    assert DOC.exists()


def test_phase17e_ticket_card_function_exists():
    text = APP.read_text()

    assert "function getAionPhase17EWebsiteTicketPreview" in text
    assert "function renderAionPhase17EBoardroomTicketCard" in text
    assert "data-aion-phase17e-boardroom-ticket-card" in text


def test_phase17e_ticket_shows_simple_business_fields():
    text = APP.read_text()

    for phrase in [
        "New Website Enquiry",
        "Website customer",
        "Pergola / roof repair",
        "Arboleas, Almería",
        "Medium / rain-related",
        "Home Fixed website form",
        "home_fixed_new_enquiry",
        "Workflow preview ready",
    ]:
        assert phrase in text


def test_phase17e_ticket_has_simple_actions():
    text = APP.read_text()

    for phrase in [
        "Run workflow preview",
        "Approve next action",
        "Request more info",
        "Show technical trace",
    ]:
        assert phrase in text


def test_phase17e_reduces_guard_repetition_to_compact_line():
    text = APP.read_text()

    assert "data-aion-phase17e-compact-safety-line" in text
    assert "Safe mode: no booking, payment, escrow, external message, or chain write. Human review required." in text
    assert "data-aion-phase17e-technical-trace-drawer" in text


def test_phase17e_keeps_manual_founder_controls_as_fallback():
    text = APP.read_text()

    assert "renderAionPhase17EBoardroomTicketCard()" in text
    assert "renderBoardroomFounderDemoLoopPanel(snapshot)" in text


def test_phase17e_css_has_ticket_layout():
    css = CSS.read_text()

    for selector in [
        ".aion-phase17e-ticket-card",
        ".aion-phase17e-ticket-head",
        ".aion-phase17e-ticket-grid",
        ".aion-phase17e-workflow-strip",
        ".aion-phase17e-action-row",
        ".aion-phase17e-safety-line",
        ".aion-phase17e-technical-trace",
    ]:
        assert selector in css


def test_phase17e_is_in_focused_suite():
    suite = SUITE.read_text()
    assert "test_aion_phase17e_boardroom_ticket_ui_simplification_lock.py" in suite
