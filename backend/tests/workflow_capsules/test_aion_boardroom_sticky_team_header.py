from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
APP = (ROOT / "desktop/mac/src/app.js").read_text(encoding="utf-8")
STYLES = (ROOT / "desktop/mac/src/styles.css").read_text(encoding="utf-8")


def test_spatial_room_collapses_into_sticky_executive_presence():
    start = APP.index("function renderBoardroomSpatialView")
    end = APP.index("/* AION PATCH: Safe Provider Council Panel fallback v1", start)
    spatial = APP[start:end]

    assert "renderAionBoardroomStickyTeamHeaderV1(snapshot)" in spatial
    assert 'data-aion-boardroom-sticky-team-header="true"' in spatial
    assert "Board in session" in spatial
    for department in ("marketing", "sales", "finance", "operations", "support", "hr"):
        assert f'key: "{department}"' in spatial


def test_sticky_board_has_head_crops_names_active_state_and_room_return():
    assert 'data-aion-boardroom-sticky-avatar="true"' in APP
    assert 'data-aion-boardroom-sticky-name="true"' in APP
    assert 'data-active="${active ? "true" : "false"}"' in APP
    assert 'data-aion-boardroom-return-full-room="true"' in APP
    assert "scrollIntoView?.({ behavior: \"smooth\", block: \"start\" })" in APP


def test_sticky_boardroom_header_is_responsive_and_visually_distinct():
    assert '[data-aion-boardroom-sticky-team-header="true"]' in STYLES
    assert "position: sticky" in STYLES
    assert "top: 0" in STYLES
    assert "backdrop-filter: blur(18px)" in STYLES
    assert '[data-aion-boardroom-sticky-member][data-active="true"]' in STYLES
    assert "@media (max-width: 1080px)" in STYLES
    assert "@media (max-width: 760px)" in STYLES
