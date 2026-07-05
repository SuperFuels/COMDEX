from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def test_o12o_installed():
    assert "BEGIN AION O12O STABLE GOAL SHEET STAGE TAKEOVER" in APP_JS
    assert "stable Goal Sheet stage takeover installed" in APP_JS


def test_o12o_bypasses_legacy_stage_handler():
    assert "stopImmediatePropagation" in APP_JS
    assert "broken_legacy_stage_handler_bypassed: true" in APP_JS
    assert "aionStageStableBoardroomGoalSheetO12O" in APP_JS


def test_o12o_builds_seven_node_goal_sheet():
    assert "buildStableBoardroomGoalSheetGraph" in APP_JS
    assert "Board meeting minutes" in APP_JS
    assert "Board decision" in APP_JS
    assert "Actual goal" in APP_JS
    assert "Success criteria" in APP_JS
    assert "Linked department sheets" in APP_JS
    assert "Pilot queue preview" in APP_JS
    assert "Evidence feedback" in APP_JS


def test_o12o_syncs_graph_without_second_canvas_or_pilot():
    assert "window.__aionWorkflowGraph = graph" in APP_JS
    assert "window.__aionGoalLoopWorkflowGraph = graph" in APP_JS
    assert "creates_second_canvas: false" in APP_JS
    assert "creates_second_pilot: false" in APP_JS


def test_o12o_skips_local_storage_persist():
    assert "local_storage_persist_skipped: true" in APP_JS
    assert "skip localStorage persistence to avoid quota overflow" in APP_JS


def test_o12o_manual_repair_hooks_exist():
    assert "window.aionStageStableBoardroomGoalSheetO12O" in APP_JS
    assert "window.aionBuildStableBoardroomGoalSheetGraphO12O" in APP_JS
    assert "window.aionRenderStableBoardroomGoalSheetO12O" in APP_JS
