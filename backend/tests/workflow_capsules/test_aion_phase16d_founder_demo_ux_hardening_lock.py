from pathlib import Path

APP = Path("desktop/mac/src/app.js")
CSS = Path("desktop/mac/src/styles.css")
DOC = Path("docs/rfc/aion_phase16d_founder_demo_ux_hardening_lock.tex")
SUITE = Path("scripts/run_goal_engine_focused_lock_suite.sh")


def _extract_function(text: str, name: str) -> str:
    start = text.index(f"function {name}")
    next_fn = text.find("\nfunction ", start + 1)
    if next_fn == -1:
        next_fn = len(text)
    return text[start:next_fn]


def test_phase16d_lock_markers_exist():
    text = APP.read_text()
    css = CSS.read_text()
    assert "PHASE 16D LOCK" in text
    assert "PHASE 16D LOCK" in css


def test_phase16d_agentmap_hash_is_truncated_not_raw_overflow():
    text = APP.read_text()
    assert "function aionShortHash" in text
    panel = _extract_function(text, "renderBoardroomAgentMapWebsiteInstallCard")
    assert "aionShortHash(hash)" in panel
    assert "title=" in panel
    assert "aion-hash-line" in panel


def test_phase16d_install_and_form_have_copy_ready_code_cards():
    text = APP.read_text()
    assert "renderBoardroomCopyCodeBlock" in text
    assert "Website install tag" in text
    assert "Generated website form snippet" in text
    assert "navigator.clipboard" in text


def test_phase16d_workflow_widget_connects_to_a2a_route():
    text = APP.read_text()
    panel = _extract_function(text, "renderBoardroomWorkflowWidgetPanel")
    for phrase in [
        "website_widget",
        "public_intent_gateway",
        "guard_envelope",
        "capability_route",
        "quote_preview",
        "human_review",
    ]:
        assert phrase in panel


def test_phase16d_proof_replay_prioritises_founder_demo_path():
    text = APP.read_text()
    panel = _extract_function(text, "renderBoardroomProofReplayPanel")
    for phrase in [
        "Home Fixed widget request",
        "Public Intent Gateway",
        "Guard Envelope",
        "Machine Cart quote preview",
        "Human Review handoff",
        "Proof receipt preview",
        "Boardroom replay",
    ]:
        assert phrase in panel


def test_phase16d_side_effect_guards_are_visible_on_proof_card():
    text = APP.read_text()
    panel = _extract_function(text, "renderBoardroomProofReplayPanel")
    for phrase in [
        "No booking created",
        "No payment created",
        "No escrow created",
        "No external message sent",
        "No live chain write",
        "Human review required",
        "Replay/hash proof available",
    ]:
        assert phrase in panel


def test_phase16d_advanced_runtime_drawer_is_controlled_scroll_area():
    css = CSS.read_text()
    assert "aion-controlled-debug-drawer[open]" in css
    assert "max-height: 620px" in css
    assert "overflow: auto" in css


def test_phase16d_focused_suite_membership_and_doc():
    assert "test_aion_phase16d_founder_demo_ux_hardening_lock.py" in SUITE.read_text()
    assert DOC.exists()
