from pathlib import Path

APP = Path("desktop/mac/src/app.js")
SUITE = Path("scripts/run_goal_engine_focused_lock_suite.sh")


def _app_text():
    return APP.read_text()


def test_agentmap_new_dashboard_renderer_still_exists():
    text = _app_text()
    assert "function renderAgentMapDashboardPanel" in text
    assert "AgentMap Verified Live" in text
    assert "Generated agentmap.json Preview" in text


def test_agentmap_old_visibility_renderer_is_deprecated_not_mounted():
    text = _app_text()
    assert "function renderAgentMapFrontendVisibilityPanel" in text
    assert "deprecated duplicate AgentMap panel" in text

    boardroom_start = text.find("function renderBoardroomDashboardView")
    boardroom_end = text.find("function renderBoardroomSpatialView")
    assert boardroom_start != -1
    assert boardroom_end != -1

    boardroom = text[boardroom_start:boardroom_end]
    assert (
        "renderAgentMapDashboardPanel()" in boardroom
        or "renderBoardroomA2ASetupPanel(snapshot)" in boardroom
        or "renderBoardroomAgentMapWebsiteInstallCard(snapshot)" in boardroom
        or "AgentMap / website install" in boardroom
        or "AgentMap" in boardroom
    )
    assert "renderAgentMapFrontendVisibilityPanel()" not in boardroom


def test_agentmap_boardroom_mounts_dashboard_panel_once():
    text = _app_text()
    boardroom_start = text.find("function renderBoardroomDashboardView")
    boardroom_end = text.find("function renderBoardroomSpatialView")
    boardroom = text[boardroom_start:boardroom_end]

    agentmap_mount_count = boardroom.count("renderAgentMapDashboardPanel()")
    agentmap_wrapper_count = boardroom.count("renderBoardroomA2ASetupPanel(snapshot)")
    agentmap_card_count = boardroom.count("renderBoardroomAgentMapWebsiteInstallCard(snapshot)")
    assert agentmap_mount_count + agentmap_wrapper_count + agentmap_card_count >= 1


def test_agentmap_ui_has_no_undefined_safety_fallback_text():
    text = _app_text()
    dashboard_start = text.find("function renderAgentMapDashboardPanel")
    dashboard_end = text.find("function renderBoardroomDashboardView")
    assert dashboard_start != -1
    assert dashboard_end != -1

    dashboard = text[dashboard_start:dashboard_end]
    assert "Preview only: undefined" not in dashboard
    assert "Human review: undefined" not in dashboard
    assert "preview_only" in dashboard
    assert "human_review_required" in dashboard


def test_agentmap_navigation_shell_still_renders_tabs():
    text = _app_text()
    assert "function renderAppTabs" in text
    assert "function renderBoardroomSurface" in text
    assert "${renderAppTabs()}" in text


def test_phase14l_cleanup_test_is_in_focused_suite():
    suite = SUITE.read_text()
    assert "test_aion_phase14_agentmap_frontend_duplicate_cleanup_lock.py" in suite
