from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
APP = (ROOT / "desktop/mac/src/app.js").read_text(encoding="utf-8")
STYLES = (ROOT / "desktop/mac/src/styles.css").read_text(encoding="utf-8")


def test_header_has_distinct_board_and_executive_team_groups():
    assert 'data-aion-boardroom-sticky-group="board"' in APP
    assert 'data-aion-boardroom-sticky-group="executive-team"' in APP
    assert ">Board<" in APP
    assert ">Executive Team<" in APP
    assert "Board in session" not in APP[APP.index("function renderAionExecutiveStickyHeaderV1"):APP.index("function normaliseAionBoardProviderKeyV1")]


def test_executive_agents_are_department_shortcuts():
    assert 'data-aion-o14l-executive-department="${escapeHtml(member.key)}"' in APP
    assert 'aria-label="Open ${escapeHtml(member.label)} workspace"' in APP
    assert 'setLiveAgentsWorkspace(key' in APP
    assert 'window.setAionSidebarActiveTabHardV1("live_agents")' in APP
    assert 'localStorage.setItem("aion.forcedMainTab.v2", "live_agents")' in APP
    assert 'window.__aionO16ASelectedLiveAgentsDepartment = key' in APP
    assert 'localStorage.setItem("aion.liveAgents.selectedDepartment", key)' in APP
    assert 'activeTab: "live_agents"' in (ROOT / "desktop/mac/src/boardroom_runtime.js").read_text(encoding="utf-8")


def test_sticky_shortcut_wins_before_legacy_pointerdown_authority():
    shortcut = APP.index('function openAionExecutiveDepartmentFromStickyHeaderV1')
    early_pointerdown = APP.index('window.addEventListener("pointerdown"', shortcut)
    legacy_authority = APP.index('function installAionO14MLiveAgentsDepartmentAuthorityLock')
    assert shortcut < early_pointerdown < legacy_authority
    assert 'localStorage.setItem("aion.forcedMainTab.v2", "live_agents")' in APP[shortcut:early_pointerdown]


def test_board_members_open_a_governed_direct_line():
    assert 'data-aion-board-member-direct-line="${escapeHtml(member.key)}"' in APP
    assert 'data-aion-board-direct-line-input="${escapeHtml(providerId)}"' in APP
    assert 'requested_providers: [cleanProviderId]' in APP
    assert 'fetch("http://127.0.0.1:8080/api/boardroom/ask"' in APP


def test_direct_line_only_lists_connected_real_providers():
    assert '!["ceo", "aion"].includes(provider.key)' in APP
    assert "provider.connected" in APP
    assert "No AI connected" in APP


def test_header_and_direct_line_have_interaction_styles():
    assert ".aion-executive-sticky-group-label" in STYLES
    assert ".aion-board-provider-avatar" in STYLES
    assert ".aion-board-direct-line" in STYLES


def test_department_pilots_use_the_shared_sticky_header_without_builder():
    nav_start = APP.index("function renderLiveAgentsExecutiveDepartmentNavO14P")
    nav_end = APP.index("/* BEGIN AION O17E", nav_start)
    nav = APP[nav_start:nav_end]
    assert "renderAionDepartmentPilotsStickyHeaderV1(activeDepartment)" in nav
    assert "Builder" not in nav
    assert 'data-aion-live-agents-sticky-header="true"' in APP
    assert 'key: "products_services", label: "Products"' in APP


def test_aion_board_member_routes_to_pilot_and_is_highlighted_there():
    assert '{ key: "aion", label: "AION", shortLabel: "A", connected: true, route: "pilot" }' in APP
    assert 'data-aion-board-member-pilot="true"' in APP
    assert 'openAionExecutiveDepartmentFromStickyHeaderV1("pilot")' in APP
    assert '"products_services",\n    "pilot",' in APP
    assert '.surface-shell[data-aion-o14p-live-agents-shell="true"]' in STYLES
    assert ".aion-executive-utility-avatar" in STYLES


def test_sticky_member_highlight_is_text_only():
    assert ".aion-executive-sticky-header .aion-executive-sticky-member[data-active=\"true\"]" in STYLES
    assert "color: #1677c8 !important;" in STYLES
    assert "background: transparent !important;" in STYLES
    assert "outline: 0 !important;" in STYLES
    assert "transform: none !important;" in STYLES


def test_shared_header_is_installed_on_primary_sidebar_pages():
    shared_start = APP.index("const AION_SHARED_EXECUTIVE_HEADER_TABS_V1")
    shared_end = APP.index("function focusAionVaultBoardroomProvidersV1", shared_start)
    shared = APP[shared_start:shared_end]
    for route in (
        "communications",
        "dashboard",
        "business_context",
        "operations_agents",
        "operations_flow",
        "vault",
    ):
        assert f'"{route}"' in shared
    assert 'data-aion-shared-page-executive-header="true"' in shared
    assert 'secondaryActionKey: "provider-council-add-key"' in shared
    assert "renderAionSharedPageExecutiveHeaderV1(state.activeTab)" in APP
    assert "aion-shared-executive-header-page" in APP
    assert ".desktop-workspace-main.aion-shared-executive-header-page" in STYLES


def test_sidebar_uses_ai_mark_for_boardroom_without_a_duplicate_aion_tab():
    tabs = APP[APP.index("const APP_TABS = ["):APP.index("];", APP.index("const APP_TABS = ["))]
    icons = APP[APP.index("function getAionMainSidebarIcon"):APP.index("function renderAppTabs")]
    assert '{ key: "aion_chat", label: "Aion"' not in tabs
    assert 'boardroom: "AI"' in icons
    assert 'aion_chat: "AI"' not in icons
