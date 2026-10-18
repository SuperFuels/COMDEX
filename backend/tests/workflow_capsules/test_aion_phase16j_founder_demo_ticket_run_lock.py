from pathlib import Path

APP = Path("desktop/mac/src/app.js")
CSS = Path("desktop/mac/src/styles.css")
DOC = Path("docs/rfc/aion_phase16j_founder_demo_ticket_run_lock.tex")
SUITE = Path("scripts/run_goal_engine_focused_lock_suite.sh")


def test_phase16j_lock_markers_exist():
    text = APP.read_text()
    css = CSS.read_text()
    assert "PHASE 16J LOCK: Founder demo ticket run + guard declutter" in text
    assert "PHASE 16J LOCK: Founder demo ticket run + guard declutter" in css
    assert DOC.exists()


def test_phase16j_ticket_state_and_run_handler_exist():
    text = APP.read_text()
    for phrase in [
        "AION_FOUNDER_DEMO_TICKET_STEPS",
        "getAionFounderDemoTicketState",
        "handleAionFounderDemoTicketRun",
        "renderAionFounderDemoTicketRunPanel",
        "HF-DEMO-001",
    ]:
        assert phrase in text


def test_phase16j_ticket_has_full_guided_sequence():
    text = APP.read_text()
    for phrase in [
        "Received",
        "Routed",
        "Guarded",
        "AgentMap",
        "Quoted",
        "Review",
        "Proof",
        "Replay",
        "Website widget",
        "Public Intent Gateway",
        "Guard Envelope",
        "Machine Cart quote preview",
        "Human review required",
        "Boardroom replay ready",
    ]:
        assert phrase in text


def test_phase16j_has_single_run_full_demo_button_and_next_step():
    text = APP.read_text()
    for phrase in [
        "Run Full Founder Demo",
        "Next ticket step",
        "Reset ticket",
        "Current artifact",
        "data-aion-founder-demo-ticket",
    ]:
        assert phrase in text


def test_phase16j_compact_guard_strip_replaces_repeated_noise():
    text = APP.read_text()
    css = CSS.read_text()
    assert "data-aion-founder-single-guard-strip" in text
    assert "Preview mode · No booking · No payment · No escrow · No external message · No live chain write" in text
    assert ".aion-founder-demo-loop-panel > .aion-founder-safety-grid" in css
    assert "display: none" in css


def test_phase16j_mounts_before_visible_output_panel():
    text = APP.read_text()
    assert "renderAionFounderDemoTicketRunPanel()" in text
    assert text.index("renderAionFounderDemoTicketRunPanel()") < text.index("renderAionFounderDemoVisibleOutputPanel(state)")


def test_phase16j_is_in_focused_suite():
    suite = SUITE.read_text()
    assert "test_aion_phase16j_founder_demo_ticket_run_lock.py" in suite
