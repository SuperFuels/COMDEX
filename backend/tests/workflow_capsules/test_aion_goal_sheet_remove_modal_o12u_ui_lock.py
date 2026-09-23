from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def block():
    return APP_JS.split("BEGIN AION O12U REMOVE GOAL SHEET DOCUMENT MODAL COMPLETELY", 1)[1].split(
        "END AION O12U REMOVE GOAL SHEET DOCUMENT MODAL COMPLETELY", 1
    )[0]


def test_o12u_installed():
    assert "BEGIN AION O12U REMOVE GOAL SHEET DOCUMENT MODAL COMPLETELY" in APP_JS
    assert "Goal Sheet document modal removed completely" in APP_JS


def test_o12u_disables_old_modal_blocks():
    required_removed = ["O12D", "O12E", "O12G", "O12H", "O12I", "O12J", "O12K", "O12L", "O12M", "O12P", "O12Q", "O12S"]
    for marker in required_removed:
        assert f"{marker} removed by O12U" in APP_JS

    # O12T may not exist in every local branch, but O12U must still guard against its DOM/hooks.
    assert "aion-o12t-goal-sheet-document-modal" in APP_JS
    assert "aionOpenGoalSheetDocumentModalO12T" in APP_JS


def test_o12u_removes_known_modal_dom_selectors():
    b = block()
    assert "#aion-o12t-goal-sheet-document-modal" in b
    assert "[data-aion-o12l-goal-modal='true']" in b
    assert "[data-aion-goal-sheet-document-modal='true']" in b
    assert "el.remove()" in b


def test_o12u_clears_modal_state():
    b = block()
    assert "clearGoalSheetModalState" in b
    assert "__aionGoalSheetDocumentModalOpen = false" in b
    assert "__aionSelectedGoalSheetDocument = null" in b


def test_o12u_kills_public_modal_hooks():
    b = block()
    assert "window.openGoalSheetInspector = noOpModalFunction" in b
    assert "window.aionOpenGoalSheetDocumentModalO12T = noOpModalFunction" in b
    assert "window.aionRemoveGoalSheetDocumentModalO12U" in b


def test_o12u_intercepts_goal_sheet_node_clicks():
    b = block()
    assert '[data-aion-workflow-node-id]' in b
    assert "isBoardroomGoalSheetGraph()" in b
    assert "event.stopImmediatePropagation()" in b
