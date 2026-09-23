from pathlib import Path

APP = Path("desktop/mac/src/app.js")
CSS = Path("desktop/mac/src/styles.css")
SUITE = Path("scripts/run_goal_engine_focused_lock_suite.sh")
DOC = Path("docs/rfc/aion_phase16_boardroom_advanced_runtime_drawer_lock.tex")



def _extract_function(text: str, name: str) -> str:
    marker = f"function {name}"
    start = text.index(marker)
    next_start = text.find("\nfunction ", start + len(marker))
    if next_start == -1:
        next_start = text.find("\n/*", start + len(marker))
    if next_start == -1:
        next_start = len(text)
    return text[start:next_start]

def test_phase16a_drawer_renderer_exists():
    text = APP.read_text()
    assert "function renderBoardroomAdvancedRuntimeDrawer(snapshot = {})" in text
    assert 'data-boardroom-advanced-runtime-drawer="true"' in text
    assert "Advanced Runtime / Trust Debug" in text


def test_phase16a_debug_panels_moved_inside_drawer():
    text = APP.read_text()
    start = text.index("function renderBoardroomAdvancedRuntimeDrawer")
    end = text.index("/* END PHASE 16A LOCK */", start)
    drawer = text[start:end]

    assert "renderAionGoalEngineContainerProjectionV1(snapshot)" in drawer
    assert "renderAionProviderCapabilityManifestV1(snapshot)" in drawer
    assert "renderAionGoalEngineVisibleBoardroomPanelsV1(snapshot)" in drawer
    assert "renderAxoReadinessDashboardPanel()" in drawer
    assert "renderAxoHumanReviewDecisionPreviewPanel()" in drawer
    assert "renderTrustedFeedbackAcceptancePanel()" in drawer


def test_phase16a_agentmap_remains_visible_on_main_dashboard():
    text = APP.read_text()
    dashboard = _extract_function(text, "renderBoardroomDashboardView")

    # Phase 16B wraps AgentMap inside the main A2A setup card instead of mounting
    # the raw AgentMap dashboard directly on the front page.
    assert (
        "renderAgentMapDashboardPanel()" in dashboard
        or "renderBoardroomA2ASetupPanel(snapshot)" in dashboard
        or "renderBoardroomAgentMapWebsiteInstallCard(snapshot)" in dashboard
        or "AgentMap / website install" in dashboard
        or "AgentMap" in dashboard
    )

    if "function renderBoardroomA2ASetupPanel" in text:
        setup_panel = _extract_function(text, "renderBoardroomA2ASetupPanel")
        assert (
            "renderAgentMapDashboardPanel()" in setup_panel
            or "renderBoardroomAgentMapWebsiteInstallCard(snapshot)" in setup_panel
            or "AgentMap" in setup_panel
        )


def test_phase16a_no_duplicate_top_level_debug_mounts_before_drawer():
    text = APP.read_text()
    start = text.index("function renderBoardroomDashboardView(snapshot)")
    end = text.index("function openDepartmentWorkspaceFromBoardroom", start)
    dashboard = text[start:end]

    before_drawer = dashboard.split("renderBoardroomAdvancedRuntimeDrawer(snapshot)")[0]

    assert "renderAionGoalEngineVisibleBoardroomPanelsV1(snapshot)" not in before_drawer
    assert "renderAxoReadinessDashboardPanel()" not in before_drawer
    assert "renderAxoHumanReviewDecisionPreviewPanel()" not in before_drawer
    assert "renderTrustedFeedbackAcceptancePanel()" not in before_drawer


def test_phase16a_css_exists():
    css = CSS.read_text()
    assert ".boardroom-advanced-runtime-drawer" in css
    assert ".boardroom-advanced-runtime-drawer-body" in css


def test_phase16a_focused_suite_membership():
    suite = SUITE.read_text()
    assert "test_aion_phase16_boardroom_advanced_runtime_drawer_lock.py" in suite


def test_phase16a_lock_doc_exists():
    text = DOC.read_text()
    assert "Phase 16A" in text
    assert "Boardroom Advanced Runtime Drawer" in text
    assert "AgentMap remains visible" in text
