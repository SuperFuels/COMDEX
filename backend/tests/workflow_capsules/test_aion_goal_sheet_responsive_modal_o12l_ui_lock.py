from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def test_o12l_installed():
    assert "BEGIN AION O12L RESPONSIVE GOAL SHEET MODAL FIX" in APP_JS
    assert "responsive Goal Sheet modal fix installed" in APP_JS


def test_o12k_heavy_observer_disabled():
    assert "O12K disabled by O12L" in APP_JS
    assert "whole-DOM MutationObserver caused sluggish canvas response" in APP_JS


def test_o12l_has_no_mutation_observer():
    block = APP_JS.split("BEGIN AION O12L RESPONSIVE GOAL SHEET MODAL FIX", 1)[1]
    block = block.split("END AION O12L RESPONSIVE GOAL SHEET MODAL FIX", 1)[0]
    assert "MutationObserver" not in block


def test_o12l_modal_is_white_no_shadow():
    assert "data-aion-o12l-goal-modal" in APP_JS
    assert "background: #ffffff" in APP_JS
    assert "box-shadow: none" in APP_JS
    assert "top: 55%" in APP_JS


def test_o12l_close_button_works():
    assert "closeGoalDocModal" in APP_JS
    assert "data-aion-o12l-close" in APP_JS
    assert "window.aionCloseGoalSheetModalO12L" in APP_JS


def test_o12l_can_restage_empty_goal_sheet():
    assert "ensureGoalSheetGraphIfEmpty" in APP_JS
    assert "nodeCount === 0" in APP_JS
    assert "aionStageBoardroomGoalSheetO12B" in APP_JS
