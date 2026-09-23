from pathlib import Path

APP = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")
RENDERER = Path("desktop/mac/src/lib/desktop-boardroom-renderer.js").read_text(encoding="utf-8")


def test_marketing_pilot_workspace_includes_121_boardroom():
    assert 'renderAionDepartment121BoardroomPanelO14D("marketing")' in APP
    assert APP.index('renderAionDepartment121BoardroomPanelO14D("marketing")') < APP.index('renderAionDepartmentScopedPilotSurface("marketing"')


def test_marketing_manual_workspace_also_includes_121_boardroom():
    assert APP.count('renderAionDepartment121BoardroomPanelO14D("marketing")') >= 2
    assert "data-aion-phase23y-marketing-manual-workspace" in APP


def test_renderer_is_throttled_for_scroll_performance():
    assert "AION O14I performance lock" in RENDERER
    assert "lastRenderAt" in RENDERER
    assert "now - (current.lastRenderAt || 0) >= 33" in RENDERER
    assert "rect.bottom >= 0" in RENDERER
    assert "rect.top <= (global.innerHeight || 0)" in RENDERER


def test_renderer_pixel_ratio_is_capped_lower_for_mac_scroll():
    assert "renderer.setPixelRatio(Math.min(global.devicePixelRatio || 1, 1.5));" in RENDERER
    assert "renderer.setPixelRatio(Math.min(global.devicePixelRatio || 1, 2.25));" not in RENDERER
