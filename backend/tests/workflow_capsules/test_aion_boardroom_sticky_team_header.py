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
    assert "Board in session" in spatial
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
    assert '[data-aion-boardroom-sticky-member][data-active="true"]' in STYLES
    assert "@media (max-width: 1080px)" in STYLES
    assert "@media (max-width: 760px)" in STYLES
