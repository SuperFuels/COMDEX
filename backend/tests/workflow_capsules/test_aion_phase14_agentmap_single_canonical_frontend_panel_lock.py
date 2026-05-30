from pathlib import Path

APP = Path("desktop/mac/src/app.js")


def _text() -> str:
    return APP.read_text()


def _boardroom_dashboard_block() -> str:
    text = _text()
    start = text.find("function renderBoardroomDashboardView")
    end = text.find("function renderBoardroomSpatialView")
    assert start != -1
    assert end != -1
    return text[start:end]



def _extract_function(text: str, name: str) -> str:
    marker = f"function {name}"
    start = text.find(marker)
    if start == -1:
        raise AssertionError(f"Could not find function {name}")

    next_function = text.find("\nfunction ", start + len(marker))
    if next_function == -1:
        next_function = len(text)

    return text[start:next_function]

def test_phase14m_keeps_single_active_agentmap_panel_in_boardroom():
    boardroom = _boardroom_dashboard_block()

    agentmap_mount_count = boardroom.count("renderAgentMapDashboardPanel()")
    agentmap_wrapper_count = boardroom.count("renderBoardroomA2ASetupPanel(snapshot)")
    agentmap_card_count = boardroom.count("renderBoardroomAgentMapWebsiteInstallCard(snapshot)")
    assert agentmap_mount_count + agentmap_wrapper_count + agentmap_card_count >= 1
    assert "renderAgentMapMachineDiscoveryPanel()" not in boardroom
    assert "renderAgentMapFrontendVisibilityPanel()" not in boardroom


def test_phase14m_canonical_panel_contains_full_frontend_actions():
    text = _text()
    start = text.find("function renderAgentMapDashboardPanel")
    end = text.find("function renderBoardroomDashboardView")
    assert start != -1
    assert end != -1

    panel = text[start:end]

    for required in [
        "data-agentmap-generate-button",
        "data-agentmap-regenerate-button",
        "data-agentmap-copy-url-button",
        "data-agentmap-download-json-button",
        "data-agentmap-copy-install-tag-button",
        "agentmap_hash",
        "Live verification",
        "Hosted URL",
        "Self-hosted URL",
        "Machine Discovery settings",
        "Generated agentmap.json preview",
    ]:
        assert required in panel


def test_phase14m_legacy_renderers_are_not_boardroom_mounted():
    text = _text()
    boardroom = _boardroom_dashboard_block()

    # Legacy functions may remain for old lock/test visibility, but must not be mounted.
    assert "function renderAgentMapFrontendVisibilityPanel()" in text
    assert "function renderAgentMapMachineDiscoveryPanel()" in text
    assert "renderAgentMapFrontendVisibilityPanel()" not in boardroom
    assert "renderAgentMapMachineDiscoveryPanel()" not in boardroom


def test_phase14m_boardroom_agentmap_order_is_before_approvals():
    text = APP.read_text()
    boardroom = _extract_function(text, "renderBoardroomDashboardView")

    agentmap_markers = [
        "renderAgentMapDashboardPanel()",
        "renderBoardroomA2ASetupPanel(snapshot)",
        "renderBoardroomAgentMapWebsiteInstallCard(snapshot)",
    ]
    approval_markers = [
        "renderBoardroomHumanReviewQueuePanel(runtimeApprovals)",
        "renderBoardroomWorkflowCapsuleApprovalQueue(runtimeApprovals)",
    ]

    agentmap_idx = min(
        [boardroom.find(marker) for marker in agentmap_markers if boardroom.find(marker) != -1],
        default=-1,
    )
    approvals_idx = min(
        [boardroom.find(marker) for marker in approval_markers if boardroom.find(marker) != -1],
        default=-1,
    )

    assert agentmap_idx != -1
    assert approvals_idx != -1
    assert agentmap_idx < approvals_idx


def test_phase14m_no_undefined_safety_values_in_canonical_panel():
    text = _text()
    start = text.find("function renderAgentMapDashboardPanel")
    end = text.find("function renderBoardroomDashboardView")
    panel = text[start:end]

    assert "agentMapSafeFallback" in panel
    assert "preview.safety_profile || {}" in panel
    assert "Cannot read properties of undefined" not in panel
