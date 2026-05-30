from pathlib import Path


APP = Path("desktop/mac/src/app.js")


def test_boardroom_ui_has_goal_engine_container_projection_renderer():
    text = APP.read_text()

    assert "renderAionGoalEngineContainerProjectionV1" in text
    assert "goal_engine_container_projection" in text
    assert "Persistent Goal Engine State" in text
    assert "business_containers" in text


def test_boardroom_ui_projection_displays_container_truth_counts():
    text = APP.read_text()

    for needle in [
        "goal_count",
        "active_goal_count",
        "memory_count",
        "evidence_count",
        "verified_evidence_count",
        "experiment_count",
        "loop_count",
        "bounded_loop_count",
        "outcome_count",
    ]:
        assert needle in text


def test_boardroom_ui_projection_is_separate_from_preview_bundle():
    text = APP.read_text()

    projection_start = text.index("function renderAionGoalEngineContainerProjectionV1")
    projection_block = text[projection_start:projection_start + 3500]

    assert "goal_engine_container_projection" in projection_block
    assert "goal_engine_preview_bundle" not in projection_block
    assert "dry-run" not in projection_block.lower()


def test_boardroom_dashboard_renders_container_projection_before_runtime_preview():
    text = APP.read_text()

    dashboard_start = text.index("function renderBoardroomDashboardView")
    dashboard = text[dashboard_start:dashboard_start + 6500]

    assert (
        "${renderAionGoalEngineContainerProjectionV1(snapshot)}" in dashboard
        or "${renderAionGoalEngineContainerProjectionV1(snapshot)}" in text
    )
    assert (
        "${renderAionGoalEngineVisibleBoardroomPanelsV1(snapshot)}" in dashboard
        or "${renderAionGoalEngineVisibleBoardroomPanelsV1(snapshot)}" in text
        or "Advanced Runtime Drawer" in text
        or "advanced-runtime-drawer" in text
        or "boardroom-advanced-runtime" in text
    )

    assert dashboard.index("${renderAionGoalEngineContainerProjectionV1(snapshot)}") < dashboard.index(
        "${renderAionGoalEngineVisibleBoardroomPanelsV1(snapshot)}"
    )
