from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def test_o12j_patch_installed():
    assert "BEGIN AION O12J GOAL SHEET MODAL FINAL POLISH" in APP_JS
    assert "Goal Sheet modal final polish installed" in APP_JS


def test_o12j_removes_cream_overlay_and_backdrop():
    assert "removeCreamOverlayFromAncestors" in APP_JS
    assert "data-aion-o12j-neutralised-cream-overlay" in APP_JS
    assert "background-color\", \"transparent\"" in APP_JS
    assert "background-image\", \"none\"" in APP_JS
    assert "backdrop-filter\", \"none\"" in APP_JS


def test_o12j_removes_modal_shadow():
    assert "box-shadow: none !important" in APP_JS
    assert 'modal.style.setProperty("box-shadow", "none", "important")' in APP_JS


def test_o12j_moves_modal_down_below_tab_bar():
    assert "top: calc(50% + 42px) !important" in APP_JS
    assert 'modal.style.setProperty("top", "calc(50% + 42px)", "important")' in APP_JS


def test_o12j_auto_hides_goal_sheet_status_badge():
    assert "Boardroom Goal Sheet staged" in APP_JS
    assert "Pilot queue preview" in APP_JS
    assert "aion-o12j-hide-goal-sheet-status" in APP_JS
    assert "window.__aionO12JHideStatusTimer" in APP_JS


def test_o12j_exposes_console_helper():
    assert "window.aionPolishGoalSheetDocumentModalO12J" in APP_JS
