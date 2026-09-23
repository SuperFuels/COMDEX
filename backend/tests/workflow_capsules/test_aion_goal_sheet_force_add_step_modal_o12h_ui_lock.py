from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def test_o12h_force_modal_patch_installed():
    assert "BEGIN AION O12H FORCE GOAL SHEET DOCUMENT ADD STEP MODAL" in APP_JS
    assert "force Goal Sheet document Add Step-style modal installed" in APP_JS


def test_o12h_finds_goal_sheet_document_by_actual_rendered_text():
    assert "BOARDROOM GOAL SHEET DOCUMENT" in APP_JS
    assert "SAFETY CONTRACT" in APP_JS
    assert "findGoalSheetDocumentModal" in APP_JS


def test_o12h_forces_centered_add_step_modal_geometry():
    assert 'data-aion-o12h-goal-sheet-document-modal' in APP_JS
    assert 'left: 50% !important' in APP_JS
    assert 'top: 50% !important' in APP_JS
    assert 'transform: translate(-50%, -50%) !important' in APP_JS
    assert 'width: min(1080px, calc(100vw - 220px)) !important' in APP_JS
    assert 'height: min(720px, calc(100vh - 150px)) !important' in APP_JS


def test_o12h_removes_backdrop_blackout():
    assert 'data-aion-o12h-goal-sheet-document-backdrop' in APP_JS
    assert 'background: transparent !important' in APP_JS
    assert 'backdrop-filter: none !important' in APP_JS


def test_o12h_exposes_console_helper():
    assert "window.aionForceGoalSheetDocumentAddStepModalO12H" in APP_JS
