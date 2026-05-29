from pathlib import Path

APP = Path("desktop/mac/src/app.js")


def _text() -> str:
    return APP.read_text()


def test_phase14m_legacy_agentmap_renderer_may_exist_but_is_not_mounted():
    text = _text()

    assert "function renderAgentMapFrontendVisibilityPanel()" in text
    assert "function renderAgentMapDashboardPanel()" in text

    assert "${renderAgentMapFrontendVisibilityPanel()}" not in text


def test_phase14m_boardroom_mounts_only_canonical_agentmap_dashboard_panel():
    text = _text()

    start = text.find("function renderBoardroomDashboardView")
    end = text.find("function renderBoardroomSpatialView")
    assert start != -1
    assert end != -1

    boardroom = text[start:end]
    assert "renderAgentMapDashboardPanel()" in boardroom
    assert "renderAgentMapFrontendVisibilityPanel()" not in boardroom


def test_phase14m_dashboard_surface_does_not_mount_stale_agentmap_panel():
    text = _text()

    start = text.find("function renderDashboardSurface")
    end = text.find("function renderMarketingRunCard")
    assert start != -1
    assert end != -1

    dashboard = text[start:end]
    assert "renderAgentMapFrontendVisibilityPanel()" not in dashboard


def test_phase14m_no_undefined_agentmap_safety_text_in_canonical_panel():
    text = _text()

    assert "Preview only: undefined" not in text
    assert "Human review: undefined" not in text
    assert "Human review required" in text
    assert "Live execution enabled" in text
    assert "Generated agentmap.json Preview" in text


def test_phase14m_canonical_agentmap_controls_remain_visible():
    text = _text()

    for phrase in [
        "Generate AgentMap",
        "Regenerate",
        "Copy AgentMap URL",
        "Download agentmap.json",
        "Copy website install tag",
        "/agentmap.json",
        "/.well-known/agentmap.json",
    ]:
        assert phrase in text
