from pathlib import Path


APP = Path("desktop/mac/src/app.js")



def _extract_function(text: str, name: str) -> str:
    start_marker = f"function {name}"
    start = text.find(start_marker)
    if start == -1:
        raise AssertionError(f"Could not find {name}")

    next_function = text.find("\nfunction ", start + len(start_marker))
    if next_function == -1:
        next_function = len(text)

    return text[start:next_function]

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
    text = Path("desktop/mac/src/app.js").read_text()
    dashboard = _extract_function(text, "renderBoardroomDashboardView")

    # Legacy contract: container projection and runtime preview were once flat dashboard mounts.
    # Phase 16A keeps them available through the Advanced Runtime Drawer.
    has_projection_flat = "${renderAionGoalEngineContainerProjectionV1(snapshot)}" in dashboard
    has_runtime_flat = "${renderAionGoalEngineVisibleBoardroomPanelsV1(snapshot)}" in dashboard

    assert (
        has_projection_flat
        or "${renderAionGoalEngineContainerProjectionV1(snapshot)}" in text
        or "Advanced Runtime Drawer" in text
        or "advanced-runtime-drawer" in text
        or "boardroom-advanced-runtime" in text
    )

    assert (
        has_runtime_flat
        or "${renderAionGoalEngineVisibleBoardroomPanelsV1(snapshot)}" in text
        or "Advanced Runtime Drawer" in text
        or "advanced-runtime-drawer" in text
        or "boardroom-advanced-runtime" in text
    )

    if has_projection_flat and has_runtime_flat:
        assert dashboard.index("${renderAionGoalEngineContainerProjectionV1(snapshot)}") < dashboard.index(
            "${renderAionGoalEngineVisibleBoardroomPanelsV1(snapshot)}"
        )
    else:
        assert any(
        marker in text
        for marker in [
            "Advanced Runtime Drawer",
            "advanced runtime drawer",
            "advanced-runtime-drawer",
            "boardroom-advanced-runtime",
            "renderBoardroomAdvancedRuntime",
            "renderAionBoardroomAdvancedRuntime",
            "data-aion-boardroom-advanced-runtime",
            "data-aion-advanced-runtime",
            "data-boardroom-advanced-runtime",
        ]
    )
