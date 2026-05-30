from pathlib import Path

APP = Path("desktop/mac/src/app.js")
CSS = Path("desktop/mac/src/styles.css")
DOC = Path("docs/rfc/aion_phase16c_founder_demo_ux_polish_lock.tex")
SUITE = Path("scripts/run_goal_engine_focused_lock_suite.sh")


def _extract_function(text: str, name: str) -> str:
    marker = f"function {name}"
    start = text.index(marker)
    next_start = text.find("\nfunction ", start + len(marker))
    if next_start == -1:
        next_start = len(text)
    return text[start:next_start]


def test_phase16c_lock_markers_exist():
    text = APP.read_text()
    assert "PHASE 16C LOCK: Founder demo UX polish + workflow/A2A preview bridge" in text
    css = CSS.read_text()
    assert "PHASE 16C LOCK: Founder demo UX polish + Workflow/A2A preview bridge" in css


def test_phase16c_front_page_has_founder_demo_loop():
    text = APP.read_text()
    dashboard = _extract_function(text, "renderBoardroomDashboardView")
    assert "renderBoardroomFounderDemoLoopPanel(snapshot)" in dashboard
    assert "renderBoardroomA2ASetupPanel(snapshot)" in dashboard
    assert "renderBoardroomHumanReviewQueuePanel(runtimeApprovals)" in dashboard
    assert "renderBoardroomProofReplayPanel(snapshot)" in dashboard


def test_phase16c_agentmap_is_compact_install_card_not_raw_hash_dump():
    text = APP.read_text()
    assert "function renderBoardroomAgentMapWebsiteInstallCard" in text
    card = _extract_function(text, "renderBoardroomAgentMapWebsiteInstallCard")
    assert "AgentMap hash" in card
    assert "shortHash" in card or "aionShortHash" in card
    assert "Copy install tag" in card
    assert "Download JSON" in card
    assert "renderAgentMapDashboardPanel()" not in _extract_function(text, "renderBoardroomDashboardView")


def test_phase16c_workflow_to_widget_bridge_exists():
    text = APP.read_text()
    assert "function renderBoardroomWorkflowWebsiteFormCard" in text
    card = _extract_function(text, "renderBoardroomWorkflowWebsiteFormCard")
    assert "Generate Customer Intake Flow" in card
    assert "Public Intent Gateway" in card
    assert "data-aion-widget-embed-preview" in card
    assert "home_fixed_repair_intake" in text
    assert "home_repair.quote_preview" in text


def test_phase16c_safety_boundary_is_visible():
    text = APP.read_text()
    assert "function renderBoardroomSafetyStrip" in text
    for phrase in [
        "No booking",
        "No payment",
        "No escrow",
        "No external message",
        "No live chain write",
        "Human review required",
    ]:
        assert phrase in text


def test_phase16c_proof_replay_is_home_fixed_not_marketing_first():
    text = APP.read_text()
    panel = _extract_function(text, "renderBoardroomProofReplayPanel")
    assert "Home Fixed Website Request Preview" in panel or "Home Fixed widget request" in panel
    assert "proof_available" in panel or "payload.proof_available" in panel or "Proof receipt" in panel or "proof receipt" in panel
    assert "Marketing Content Draft" not in panel


def test_phase16c_advanced_runtime_drawer_remains_last():
    text = APP.read_text()
    dashboard = _extract_function(text, "renderBoardroomDashboardView")
    assert "renderBoardroomAdvancedRuntimeDrawer(snapshot)" in dashboard
    assert dashboard.index("renderBoardroomProofReplayPanel(snapshot)") < dashboard.index("renderBoardroomAdvancedRuntimeDrawer(snapshot)")


def test_phase16c_focused_suite_membership_and_doc():
    assert "test_aion_phase16c_founder_demo_ux_polish_lock.py" in SUITE.read_text()
    assert DOC.exists()
    doc = DOC.read_text()
    for phrase in [
        "Founder Demo UX Polish",
        "Workflow/A2A Preview Bridge",
        "No booking created",
        "No payment created",
        "No escrow created",
        "No external message sent",
        "No live chain write",
        "Human review required",
    ]:
        assert phrase in doc
