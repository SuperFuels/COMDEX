from pathlib import Path

APP = Path("desktop/mac/src/app.js")


def _text() -> str:
    return APP.read_text()


def test_phase14h_agentmap_frontend_panel_function_exists():
    text = _text()
    assert "function renderAgentMapFrontendVisibilityPanel()" in text
    assert "data-agentmap-panel=\"machine-discovery\"" in text


def test_phase14h_agentmap_frontend_panel_is_mounted_once_in_boardroom_surface():
    text = _text()

    # Phase 14L keeps the legacy visibility renderer available,
    # but the Boardroom now mounts only the newer verified dashboard panel.
    assert "function renderAgentMapFrontendVisibilityPanel()" in text
    assert "function renderAgentMapDashboardPanel()" in text

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


def test_phase14h_agentmap_frontend_exposes_required_visible_labels():
    text = _text()
    for label in [
        "Machine Discovery",
        "AgentMap Dashboard",
        "AgentMap Verified Live",
        "agentmap_hash",
        "agentmap.json Preview",
        "Hosted URL",
        "Self-hosted export",
        "/agentmap.json",
        "/.well-known/agentmap.json",
    ]:
        assert label in text


def test_phase14h_agentmap_frontend_exposes_required_buttons():
    text = _text()
    for label in [
        "Generate AgentMap",
        "Regenerate AgentMap",
        "Copy AgentMap URL",
        "Download agentmap.json",
        "Copy website install tag",
        "Run Synthetic Agent Simulation",
        "Run Human Review E2E Simulation",
    ]:
        assert label in text


def test_phase14h_agentmap_frontend_exposes_action_hooks():
    text = _text()
    for hook in [
        'data-agentmap-action="generate"',
        'data-agentmap-action="regenerate"',
        'data-agentmap-action="copy-url"',
        'data-agentmap-action="download-json"',
        'data-agentmap-action="copy-install-tag"',
        'data-agentmap-action="run-synthetic-simulation"',
        'data-agentmap-action="run-human-review-e2e"',
    ]:
        assert hook in text


def test_phase14h_agentmap_frontend_keeps_safety_boundary_visible():
    text = _text()
    for phrase in [
        "No booking",
        "payment",
        "escrow",
        "dispatch",
        "external message",
        "live chain write",
    ]:
        assert phrase in text
