from pathlib import Path


APP = Path("desktop/mac/src/app.js")


def test_boardroom_ui_references_goal_decomposition_runtime_summary():
    text = APP.read_text()

    assert "goal_decomposition_runtime_summary" in text
    assert "goal_engine_decomposition_runtime_summary" in text
    assert "renderAionGoalEngineDecompositionSummaryV1" in text
    assert "Goal Decomposition Summary" in text


def test_boardroom_decomposition_panel_shows_core_counts():
    text = APP.read_text()

    for needle in [
        "decomposition_count",
        "sub_goal_count",
        "bounded_decomposition_count",
        "human_review_required_count",
    ]:
        assert needle in text


def test_boardroom_decomposition_panel_shows_decomposition_details():
    text = APP.read_text()

    for needle in [
        "decomposition_previews",
        "decomposition_id",
        "parent_goal_id",
        "decomposition_strategy",
        "max_depth",
        "max_sub_goals",
    ]:
        assert needle in text


def test_boardroom_decomposition_panel_is_in_visible_runtime_preview():
    text = APP.read_text()

    block_start = text.index("function renderAionGoalEngineVisibleBoardroomPanelsV1")
    block = text[block_start:block_start + 2200]

    assert "renderAionGoalEngineDecompositionSummaryV1(source)" in block
    assert "Goal Engine Runtime Preview" in block
