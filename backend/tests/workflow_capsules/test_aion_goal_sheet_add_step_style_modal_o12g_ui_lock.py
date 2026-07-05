from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def test_o12g_add_step_style_modal_installed():
    assert "BEGIN AION O12G GOAL SHEET ADD-STEP STYLE DOCUMENT MODAL" in APP_JS
    assert "Goal Sheet Add Step-style document modal installed" in APP_JS


def test_o12g_removes_remaining_boardroom_graph_crash_source():
    assert "boardroomGraph" not in APP_JS


def test_o12g_modal_is_centered_not_right_drawer():
    assert "left: 50% !important" in APP_JS
    assert "top: 50% !important" in APP_JS
    assert "transform: translate(-50%, -50%) !important" in APP_JS
    assert "width: min(1080px, calc(100vw - 220px)) !important" in APP_JS


def test_o12g_modal_has_no_blackout_background():
    assert "background: transparent !important" in APP_JS
    assert "backdrop-filter: none !important" in APP_JS
    assert "pointer-events: none !important" in APP_JS


def test_o12g_modal_keeps_document_interaction_and_linked_workflows():
    assert "data-aion-goal-sheet-document-modal" in APP_JS
    assert "data-aion-goal-sheet-document-close" in APP_JS
    assert "data-aion-o12b-open-linked-workflow" in APP_JS
    assert "Escape" in APP_JS
