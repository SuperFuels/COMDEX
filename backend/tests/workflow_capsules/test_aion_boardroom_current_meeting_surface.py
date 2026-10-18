from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
APP = (ROOT / "desktop/mac/src/app.js").read_text(encoding="utf-8")
BOARDROOM_WORLD_PAGE = (
    ROOT / "frontend/pages/aion-business.tsx"
).read_text(encoding="utf-8")
FRONTEND_APP = (ROOT / "frontend/pages/_app.tsx").read_text(encoding="utf-8")
ELECTRON_MAIN = (ROOT / "desktop/mac/electron/main.js").read_text(encoding="utf-8")
ELECTRON_PRELOAD = (ROOT / "desktop/mac/electron/preload.js").read_text(encoding="utf-8")
UNITY_ROOM = (
    ROOT / "unity/spatial-boardroom-mvp/Assets/Scripts/SpatialBoardroomBootstrap.cs"
).read_text(encoding="utf-8")


def _boardroom_surface() -> str:
    start = APP.index("function renderBoardroomSurface()")
    end = APP.index("/* AION COMMUNICATIONS WORKSPACE", start)
    return APP[start:end]


def test_boardroom_opens_the_current_meeting_surface_only():
    surface = _boardroom_surface()

    assert 'data-aion-boardroom-current-meeting="true"' in surface
    assert "renderBoardroomSpatialView(snapshot, workspaceMode)" in surface
    assert "renderBoardroomDashboardView" not in surface


def test_live_debate_renderer_uses_the_current_result_and_builds_complete_department_packages():
    renderer_start = APP.index("function renderAionDebatePlanRoundHtmlV2()")
    renderer_end = APP.index("function normaliseAionTextForRoutingV1", renderer_start)
    renderer = APP[renderer_start:renderer_end]
    package_start = APP.index("/* BEGIN AION O14A BOARDROOM PACKAGE TO DEPARTMENT PILOT INBOX */")
    package_end = APP.index("/* END AION O14A BOARDROOM PACKAGE TO DEPARTMENT PILOT INBOX */", package_start)
    package_bridge = APP[package_start:package_end]

    assert 'renderAionDiscoveryQuestionInboxHtmlV1(result, "debate_plan")' in renderer
    assert 'renderAionDiscoveryQuestionInboxHtmlV1(debate, "debate_plan")' not in renderer
    assert 'data-aion-ratify-board-direction="true"' in renderer
    assert 'const DEPARTMENTS = ["marketing", "sales", "finance", "operations", "support", "hr"]' in package_bridge
    assert "Missing founder or operating decisions are not a reason to withhold the business plan" in APP
    assert "Do not refuse to create a department plan because information is missing" in APP
    assert 'const departments = ["marketing", "sales", "finance", "operations", "support", "hr"]' in APP
    assert "ensureAionDepartmentTaskCoverageV1" in APP
    assert "compactAionBoardroomRoundOneForProviderV1(sourceResult, plan)" in APP
    assert "compactAionDebateForProviderV1(debate)" in APP
    assert "source_round_1_result: sourceResult" not in APP
    assert "source_debate_round: debate" not in APP
    assert "The standard position/recommendations/risks/missing_inputs/plan_changes/confidence fields are mandatory" in APP


def test_legacy_provider_panel_and_view_switch_are_not_on_boardroom_surface():
    surface = _boardroom_surface()

    assert "renderAionProviderCouncilPanelSafeV1" not in surface
    assert "data-boardroom-view" not in surface
    assert "3D Boardroom" not in surface


def test_current_boardroom_preserves_the_sticky_team_and_expandable_room():
    surface = _boardroom_surface()
    spatial_start = APP.index("function renderBoardroomSpatialView")
    spatial_end = APP.index("function renderAionExecutiveStickyHeaderV1", spatial_start)
    spatial = APP[spatial_start:spatial_end]

    assert "renderBoardroomSpatialView(snapshot, workspaceMode)" in surface
    assert 'data-aion-boardroom-full-room-region="true"' in spatial
    assert "renderBoardroomCouncilSessionTerminal()" in spatial


def test_board_and_executive_team_are_separate_top_level_modes():
    surface = _boardroom_surface()
    spatial_start = APP.index("function normaliseAionBoardroomWorkspaceModeV1")
    spatial_end = APP.index("function renderAionExecutiveStickyHeaderV1", spatial_start)
    spatial = APP[spatial_start:spatial_end]

    assert '>Si Board<' in surface
    assert '>Si Executive Team<' in surface
    assert 'data-aion-boardroom-workspace-mode-control="board"' in surface
    assert 'data-aion-boardroom-workspace-mode-control="executive"' in surface
    assert "window.__aionBoardroomFullRoomExpandedV2 = false" in spatial
    assert 'type: "team_mode"' in spatial
    assert "await mountAionEmbeddedBoardroomV1(true)" in spatial
    assert "mode: getAionBoardroomWorkspaceModeV1()" in APP
    assert '"tessaris-mode": mode' in ELECTRON_MAIN
    assert "bridge.events = []" in ELECTRON_MAIN
    assert 'if (key == "tessaris-mode") initialMode = value;' in UNITY_ROOM
    assert "renderAionExecutiveMeetingWorkspaceV1()" in spatial
    assert 'data-aion-executive-meeting-workspace="true"' in spatial
    assert 'aionOperationsConversationRequest("executive-status"' in spatial
    assert 'aionOperationsConversationRequest("morning-briefing"' in spatial
    assert "COO · central operating terminal" in spatial


def test_boardroom_world_button_launches_native_room_and_keeps_web_preview_separate():
    surface = _boardroom_surface()

    assert 'data-aion-boardroom-world-launch="true"' in surface
    assert 'data-aion-open-boardroom-world="true"' in surface
    assert "Open Native Boardroom World" in surface
    assert "openAionBoardroomWorldV1()" in surface
    assert "launchSpatialBoardroom" in APP
    assert "previewAionBoardroomWorldV1()" in surface
    assert "window.__aionBoardroomWorldEmbeddedV1 = true" in APP
    assert 'querySelector(\'[data-aion-boardroom-world-embedded="true"]\')' in APP
    assert 'mode: "embedded_preview"' in APP
    assert 'data-aion-boardroom-world-frame="true"' in surface
    assert "aion-business?desktopView=boardroom&amp;embed=tessaris" in surface
    assert "Return to Boardroom" in surface
    assert "openIsolatedBrowser" not in surface
    assert "openExternalUrl" not in surface


def test_native_room_uses_opaque_loopback_bridge_and_existing_governed_chat():
    assert 'ipcRenderer.invoke("aion-launch-spatial-boardroom"' in ELECTRON_PRELOAD
    assert 'ipcRenderer.on("aion-spatial-boardroom-action"' in ELECTRON_PRELOAD
    assert 'bridge.server.listen(0, "127.0.0.1"' in ELECTRON_MAIN
    assert 'crypto.randomBytes(32).toString("base64url")' in ELECTRON_MAIN
    assert '"open_board_member_chat"' in ELECTRON_MAIN
    assert "AionBoardroomSeatConversation?.open" in APP
    assert 'openAionExecutiveDepartmentFromStickyHeaderV1("pilot")' in APP
    assert "--tessaris-actions=" in UNITY_ROOM
    assert 'bridge?.SendAction("open_board_member_chat"' in UNITY_ROOM


def test_native_room_never_receives_provider_secrets():
    launch_start = ELECTRON_MAIN.index('ipcMain.handle("aion-launch-spatial-boardroom"')
    launch_end = ELECTRON_MAIN.index('ipcMain.handle("aion-spatial-boardroom-event"', launch_start)
    launch = ELECTRON_MAIN[launch_start:launch_end]
    forbidden = ("api_key", "secret_key", "access_token", "provider_secret", "password")
    assert not any(value in launch.lower() for value in forbidden)


def test_embedded_boardroom_world_route_has_no_public_website_shell():
    assert "<BoardroomPage />" in BOARDROOM_WORLD_PAGE
    assert 'data-aion-business-embedded-in-tessaris="true"' in BOARDROOM_WORLD_PAGE
    assert "if (embeddedInTessaris)" in BOARDROOM_WORLD_PAGE
    assert 'router.query.embed === "tessaris"' in FRONTEND_APP
