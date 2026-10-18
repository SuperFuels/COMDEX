from pathlib import Path

APP = Path("desktop/mac/src/app.js")


def read_app() -> str:
    return APP.read_text(encoding="utf-8")


def test_visible_boardroom_goal_preview_renderer_exists():
    text = read_app()

    assert "renderAionGoalEngineBoardroomPreviewSummaryPanelV1" in text
    assert "getAionGoalEngineBoardroomPreviewSummaryV1" in text
    assert 'data-aion-goal-engine-boardroom-preview-panel="true"' in text


def test_visible_boardroom_goal_preview_shows_required_fields():
    text = read_app()

    assert "Boardroom Goal Preview" in text
    assert "Active goals" in text
    assert "Variants" in text
    assert "Loop iterations" in text
    assert "Outcome score" in text
    assert "Risk score" in text
    assert "Budget remaining" in text
    assert "Recommended action" in text


def test_visible_boardroom_goal_preview_install_wrapper_exists():
    text = read_app()

    assert "installAionGoalEngineBoardroomPreviewSummaryPanelV1" in text
    assert "__aionGoalEngineBoardroomPreviewSummaryPanelV1" in text
    assert "renderBoardroomWithGoalEnginePreviewV1" in text
    assert "data-aion-goal-engine-boardroom-preview-panel" in text
