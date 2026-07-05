from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def block():
    assert "BEGIN AION O13G BOARDROOM GOAL SHEET PROGRESS SUMMARY" in APP_JS
    return APP_JS.split("BEGIN AION O13G BOARDROOM GOAL SHEET PROGRESS SUMMARY", 1)[1].split(
        "END AION O13G BOARDROOM GOAL SHEET PROGRESS SUMMARY", 1
    )[0]


def test_o13g_installed():
    b = block()
    assert "Boardroom Goal Sheet progress summary installed" in b
    assert "aionBuildBoardroomGoalSheetProgressSummaryO13G" in b
    assert "aionRenderBoardroomGoalSheetProgressSummaryO13G" in b


def test_o13g_tracks_full_goal_loop_progress():
    b = block()
    assert "linked_department_sheet_count" in b
    assert "pilot_task_count" in b
    assert "evidence_count" in b
    assert "next_board_decision_required" in b
    assert "department_summary" in b


def test_o13g_renders_visible_boardroom_summary():
    b = block()
    assert "data-aion-o13g-boardroom-goal-sheet-progress" in b
    assert "Boardroom Goal Sheet progress" in b
    assert "Goal loop status" in b
    assert "Board decision required" in b


def test_o13g_shows_all_loop_steps():
    b = block()
    assert "Department sheets" in b
    assert "Pilot tasks" in b
    assert "Evidence feedback" in b
    assert "Execution" in b
    assert "blocked" in b


def test_o13g_preview_safety_visible():
    b = block()
    assert "Preview only" in b
    assert "No execution" in b
    assert "No connector calls" in b
    assert "No persistence" in b
    assert "Founder approval required" in b


def test_o13g_wraps_existing_boardroom_actions_panel():
    b = block()
    assert "renderAionCentralApprovedBoardroomActionsPanel" in b
    assert "renderAionCentralApprovedBoardroomActionsPanelWithGoalProgress" in b
    assert "__aionO13GWrapped" in b
    assert "return `${panel}${originalHtml}`" in b


def test_o13g_uses_existing_o13c_o13f_state():
    b = block()
    assert "__aionGoalLoopPilotQueuePreview" in b
    assert "__aionGoalSheetPilotTaskQueueO13C" in b
    assert "__aionBoardroomGoalSheetEvidenceFeedbackO13F" in b
    assert "__aionGoalSheetEvidenceFeedbackPreview" in b


def test_o13g_supports_all_departments():
    b = block()
    for department in ["marketing", "sales", "finance", "operations", "support"]:
        assert f'"{department}"' in b


def test_o13g_not_floating_overlay():
    b = block()
    assert "position: fixed" not in b
    assert "document.body.appendChild" not in b
    assert "appendChild(shell)" not in b
    assert "return `${panel}${originalHtml}`" in b
