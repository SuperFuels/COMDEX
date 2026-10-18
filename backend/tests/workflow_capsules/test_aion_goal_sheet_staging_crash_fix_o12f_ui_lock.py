from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def test_o12f_staging_crash_fix_installed():
    assert "BEGIN AION O12F GOAL SHEET STAGING CRASH FIX" in APP_JS
    assert "Goal Sheet staging crash fix installed" in APP_JS
    assert "O12F recovered from Goal Sheet stage crash" in APP_JS


def test_o12f_removes_boardroom_graph_undefined_reference():
    # The actual stale assignment must be gone.
    assert "window.__aionGoalLoopWorkflowGraph = boardroomGraph;" not in APP_JS
    assert "window.__aionPendingGoalLoopFromBoardroomO12B = boardroomGraph;" not in APP_JS
    assert "workflow_id: boardroomGraph.workflow_id" not in APP_JS


def test_o12f_guarantees_non_empty_goal_sheet_graph():
    assert "makeFallbackBoardroomGoalSheetGraph" in APP_JS
    assert "ensureNonEmptyGoalSheetGraph" in APP_JS
    assert "nodes.length === 0" in APP_JS
    assert "workflow_goal_loop_boardroom_goal_sheet" in APP_JS


def test_o12f_fallback_has_expected_boardroom_nodes():
    for label in [
        "Board meeting minutes",
        "Board decision",
        "Actual goal",
        "Success criteria",
        "Linked department sheets",
        "Pilot queue preview",
        "Evidence feedback",
    ]:
        assert label in APP_JS


def test_o12f_preserves_preview_safety_contract():
    assert "creates_second_canvas: false" in APP_JS
    assert "creates_second_pilot: false" in APP_JS
    assert "connector_call_required: false" in APP_JS
    assert "external_side_effects: false" in APP_JS
    assert "execution_allowed_now: false" in APP_JS
