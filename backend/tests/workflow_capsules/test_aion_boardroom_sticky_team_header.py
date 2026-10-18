from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
APP = (ROOT / "desktop/mac/src/app.js").read_text(encoding="utf-8")
STYLES = (ROOT / "desktop/mac/src/styles.css").read_text(encoding="utf-8")


def test_spatial_room_collapses_into_sticky_executive_presence():
    start = APP.index("function renderBoardroomSpatialView")
    end = APP.index("/* AION PATCH: Safe Provider Council Panel fallback v1", start)
    spatial = APP[start:end]

    assert "renderAionBoardroomStickyTeamHeaderV1(snapshot, { fullRoomExpanded })" in spatial
    assert 'data-aion-boardroom-full-room-region="true"' in spatial
    assert '${fullRoomExpanded ? "" : "hidden"}' in spatial
    assert 'data-aion-boardroom-sticky-team-header="true"' in spatial
    assert "Board in session" not in spatial
    for department in ("marketing", "sales", "finance", "operations", "support", "hr"):
        assert f'key: "{department}"' in spatial


def test_sticky_board_has_head_crops_names_active_state_and_room_toggle():
    assert 'data-aion-boardroom-sticky-avatar="true"' in APP
    assert 'data-aion-boardroom-sticky-name="true"' in APP
    assert 'data-active="${active ? "true" : "false"}"' in APP
    assert 'data-aion-boardroom-return-full-room="true"' in APP
    assert 'data-aion-executive-header-action="${escapeHtml(actionKey)}"' in APP
    assert 'actionKey: "toggle-boardroom-full-room"' in APP
    assert "window.__aionBoardroomFullRoomExpandedV2 = !(window.__aionBoardroomFullRoomExpandedV2 === true)" in APP


def test_executive_header_is_reusable_outside_the_boardroom():
    assert "function renderAionExecutiveStickyHeaderV1" in APP
    assert 'data-aion-executive-sticky-header="true"' in APP
    assert 'data-aion-executive-header-scope="${escapeHtml(scope)}"' in APP
    assert "members = []" in APP
    assert "actionKey = \"\"" in APP


def test_expanded_room_has_no_redundant_spatial_title_or_view_switcher():
    start = APP.index("function renderBoardroomSpatialView")
    end = APP.index("function renderAionExecutiveStickyHeaderV1", start)
    spatial = APP[start:end]

    assert "Spatial Boardroom" not in spatial
    assert "Executive team view · board communication terminal below" not in spatial
    assert "2D Dashboard" not in spatial
    assert "3D Boardroom" not in spatial
    assert 'secondaryActionKey: "provider-council-add-key"' in APP
    assert 'secondaryActionLabel: "+"' in APP
    assert 'secondaryActionAriaLabel: "Add new LLM"' in APP
    assert 'data-aion-provider-council-add-key="true"' in APP


def test_header_uses_compact_symbols_in_both_room_states():
    assert '<span aria-hidden="true">${expanded ? "−" : "⤢"}</span>' in APP
    assert 'aria-label="${escapeHtml(expanded ? collapseLabel : expandLabel)}"' in APP
    assert "width: 38px" in STYLES
    assert "height: 38px" in STYLES


def test_add_llm_routes_to_and_focuses_vault_provider_setup():
    assert "function openAionVaultBoardroomProvidersV1" in APP
    assert 'window.setAionSidebarActiveTabHardV1("vault")' in APP
    assert 'setActiveTab("vault")' in APP
    assert 'safeAionDesktopPatch({ activeTab: nextTab })' in APP
    assert "function focusAionVaultBoardroomProvidersV1" in APP
    assert 'document.querySelector(\'[data-aion-vault-ai-providers="true"]\')' in APP
    assert 'panel.scrollIntoView?.({ behavior: "smooth", block: "start" })' in APP
    assert 'providerSelect?.focus?.({ preventScroll: true })' in APP
    assert '[data-aion-vault-ai-providers="true"][data-aion-vault-boardroom-focus="true"]' in STYLES


def test_sticky_boardroom_header_is_responsive_and_visually_distinct():
    assert '[data-aion-boardroom-sticky-team-header="true"]' in STYLES
    assert "position: sticky" in STYLES
    assert "top: 0" in STYLES
    assert "backdrop-filter: blur(18px)" in STYLES
    assert '.aion-executive-sticky-header .aion-executive-sticky-member[data-active="true"]' in STYLES
    assert "@media (max-width: 1080px)" in STYLES
    assert "@media (max-width: 760px)" in STYLES


def test_executive_strip_is_outside_the_contained_boardroom_panel():
    start = APP.index("function renderBoardroomSpatialView")
    end = APP.index("function renderAionExecutiveStickyHeaderV1", start)
    spatial = APP[start:end]

    header = spatial.index('data-aion-executive-page-header-bleed="true"')
    panel = spatial.index('data-aion-spatial-boardroom-main-panel="true"')
    assert header < panel
    assert 'data-aion-executive-page-header-scope="boardroom"' in spatial
    assert '[data-aion-executive-page-header-bleed="true"]' in STYLES
    assert "width: 100vw" in STYLES
    assert "position: fixed" in STYLES
    assert "left: 0" in STYLES
    assert "right: 0" in STYLES
    assert 'html body .surface-shell[data-aion-boardroom-view-mode]' in STYLES
    assert 'html body .surface-shell[data-aion-boardroom-view-mode]:has(.aion-main-sidebar)' in STYLES
    assert "padding: 95px 24px 32px !important" in STYLES


def test_executive_strip_uses_white_and_light_blue_controls():
    assert "background: rgba(255, 255, 255, .98)" in STYLES
    assert "border-bottom: 1px solid #d7e9f7" in STYLES
    assert "background: #eaf6ff" in STYLES
    assert "border: 1px solid #b9dcf7" in STYLES
    assert "background: #d8eeff" in STYLES
    assert ".aion-executive-sticky-action:focus-visible" in STYLES
    assert "padding: 9px 24px 9px 88px" in STYLES
    assert 'body.aion-workflow-sidebar-expanded [data-aion-boardroom-sticky-team-header="true"]' in STYLES
    assert "padding-left: 260px" in STYLES


def test_sidebar_remount_geometry_matches_the_root_sidebar():
    start = APP.index("function installAionMainLeftSidebarForcePhase25K")
    end = APP.index("function installAionPhase25KRootMountedSidebarLock", start)
    transient_sidebar = APP[start:end]

    assert "width: 64px !important" in transient_sidebar
    assert "gap: 0 !important" in transient_sidebar
    assert "padding: 0 !important" in transient_sidebar
    assert "height: 71px !important" in transient_sidebar
    assert "min-height: 71px !important" in transient_sidebar
    assert "html body > .aion-main-sidebar .aion-workflow-sidebar-toggle" in APP
