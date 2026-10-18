from pathlib import Path

APP = Path("desktop/mac/src/app.js")
CSS = Path("desktop/mac/src/styles.css")
DOC = Path("docs/rfc/aion_phase16_boardroom_front_page_simplification_lock.tex")
SUITE = Path("scripts/run_goal_engine_focused_lock_suite.sh")


def _extract_function(text: str, name: str) -> str:
    start = text.index(f"function {name}")
    next_start = text.find("\nfunction ", start + 1)
    if next_start == -1:
        return text[start:]
    return text[start:next_start]


def test_phase16b_front_page_renderer_exists():
    text = APP.read_text()
    assert "function renderBoardroomFounderDemoLoopPanel" in text
    assert "function renderBoardroomA2ASetupPanel" in text
    assert "function renderBoardroomWorkflowWidgetPanel" in text
    assert "function renderBoardroomProofReplayPanel" in text
    assert "data-aion-boardroom-frontpage-simplified" in text


def test_phase16b_top_dashboard_keeps_business_operator_and_demo_loop():
    text = APP.read_text()
    dashboard = _extract_function(text, "renderBoardroomDashboardView")

    assert "${renderBoardroomOperatorPresence()}" in dashboard
    assert "${renderBoardroomFounderDemoLoopPanel(snapshot)}" in dashboard
    assert "${renderBoardroomA2ASetupPanel(snapshot)}" in dashboard
    assert "${renderBoardroomWorkflowWidgetPanel(snapshot)}" in dashboard
    assert (
        "${renderBoardroomHumanReviewQueuePanel(runtimeApprovals)}" in dashboard
        or "${renderBoardroomWorkflowCapsuleApprovalQueue(runtimeApprovals)}" in dashboard
    )
    assert "${renderBoardroomProofReplayPanel(snapshot)}" in dashboard


def test_phase16b_demo_loop_records_required_founder_proof_steps():
    text = APP.read_text()
    panel = _extract_function(text, "renderBoardroomFounderDemoLoopPanel")

    for phrase in [
        "Website/widget request",
        "Public Intent Gateway",
        "Guard Envelope",
        "AgentMap route",
        "Machine Cart quote preview",
        "Human Review handoff",
        "Founder decision preview",
        "FulfilmentJob preview",
        "Evidence preview",
        "Proof receipt",
        "ETS preview",
        "Boardroom replay",
    ]:
        assert phrase in panel or phrase in text


def test_phase16b_demo_loop_keeps_side_effect_boundary_visible():
    text = APP.read_text()
    panel = _extract_function(text, "renderBoardroomFounderDemoLoopPanel")

    for phrase in [
        "No booking created",
        "No payment created",
        "No escrow created",
        "No external message sent",
        "No live chain write",
        "Replay/hash proof available",
    ]:
        assert phrase in panel or phrase in text


def test_phase16b_runtime_debug_panels_are_not_top_level_dashboard_mounts():
    text = APP.read_text()
    dashboard = _extract_function(text, "renderBoardroomDashboardView")

    assert "${renderBoardroomAdvancedRuntimeDrawer(snapshot)}" in dashboard
    assert "${renderAionGoalEngineVisibleBoardroomPanelsV1(snapshot)}" not in dashboard
    assert "${renderAionGoalEngineContainerProjectionV1(snapshot)}" not in dashboard
    assert "${renderAionProviderCapabilityManifestV1(snapshot)}" not in dashboard
    assert "${renderAxoReadinessDashboardPanel()}" not in dashboard
    assert "${renderAxoHumanReviewDecisionPreviewPanel()}" not in dashboard
    assert "${renderTrustedFeedbackAcceptancePanel()}" not in dashboard


def test_phase16b_old_departments_and_bindings_are_not_front_page_clutter():
    text = APP.read_text()
    dashboard = _extract_function(text, "renderBoardroomDashboardView")

    assert "${renderBoardroomDepartments(departments)}" not in dashboard
    assert "${renderBoardroomBindings(bindingsByCategory)}" not in dashboard
    assert "Container Bindings" not in dashboard


def test_phase16b_workflow_widget_links_workflows_to_a2a_and_embed_code():
    text = APP.read_text()
    panel = _extract_function(text, "renderBoardroomWorkflowWidgetPanel")

    for phrase in [
        "Workflow → Website Form",
        "Generate Customer Intake Flow",
        "Public Intent Gateway",
        "operator approval",
        "Generate workflow form preview",
        "Copy embed code preview",
        "Verify A2A route preview",
    ]:
        assert phrase in panel or phrase in text


def test_phase16b_css_and_doc_are_locked():
    css = CSS.read_text()
    doc = DOC.read_text()
    suite = SUITE.read_text()

    assert "PHASE 16B LOCK: Boardroom front page simplification" in css
    assert "aion-boardroom-frontpage-simplified" in css
    assert "Phase 16B" in doc
    assert "Boardroom Front Page Simplification" in doc
    assert "PHASE16B-BOARDROOM-FRONT-PAGE-SIMPLIFICATION-LOCK" in doc
    assert "test_aion_phase16_boardroom_front_page_simplification_lock.py" in suite
