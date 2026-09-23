from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def test_o12m_installed():
    assert "BEGIN AION O12M FINAL LIGHTWEIGHT GOAL SHEET MODAL POLISH" in APP_JS
    assert "final lightweight Goal Sheet modal polish installed" in APP_JS


def test_o12m_has_no_heavy_observer():
    block = APP_JS.split("BEGIN AION O12M FINAL LIGHTWEIGHT GOAL SHEET MODAL POLISH", 1)[1]
    block = block.split("END AION O12M FINAL LIGHTWEIGHT GOAL SHEET MODAL POLISH", 1)[0]
    assert "MutationObserver" not in block


def test_o12m_targets_real_goal_sheet_document_modal():
    assert "findGoalSheetDocumentModal" in APP_JS
    assert "BOARDROOM GOAL SHEET DOCUMENT" in APP_JS
    assert "SAFETY CONTRACT" in APP_JS


def test_o12m_hides_staged_status_while_modal_open():
    assert "hideStagedBadge" in APP_JS
    assert "Boardroom Goal Sheet staged" in APP_JS
    assert "Goal Loop staged" in APP_JS


def test_o12m_forces_white_surface():
    assert "forceWhiteModalSurface" in APP_JS
    assert "background-color\", \"#ffffff\"" in APP_JS
    assert "background-image\", \"none\"" in APP_JS


def test_o12m_close_is_click_and_escape_bound():
    assert "data-aion-o12m-close" in APP_JS
    assert "window.aionCloseGoalSheetModalO12M" in APP_JS
    assert "event.key !== \"Escape\"" in APP_JS
