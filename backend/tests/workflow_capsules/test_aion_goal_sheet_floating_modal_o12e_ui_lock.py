from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def test_o12e_floating_modal_installed():
    assert "BEGIN AION O12E FLOATING GOAL SHEET DOCUMENT MODAL" in APP_JS
    assert "floating Goal Sheet document modal installed" in APP_JS
    assert "aion-o12e-floating-goal-sheet-document-modal-style" in APP_JS


def test_o12e_removes_blackout_full_page_overlay():
    assert "background: transparent !important" in APP_JS
    assert "background-color: transparent !important" in APP_JS
    assert "pointer-events: none !important" in APP_JS
    assert "inset: auto !important" in APP_JS


def test_o12e_positions_modal_below_tabs_and_above_bottom_toolbar():
    assert "top: 188px !important" in APP_JS
    assert "right: 28px !important" in APP_JS
    assert "bottom: 118px !important" in APP_JS
    assert "max-height: calc(100vh - 306px) !important" in APP_JS


def test_o12e_preserves_canvas_chrome_clickability():
    assert ".aion-workflow-floating-toolbar" in APP_JS
    assert ".aion-workflow-zoom" in APP_JS
    assert "pointer-events: auto !important" in APP_JS
