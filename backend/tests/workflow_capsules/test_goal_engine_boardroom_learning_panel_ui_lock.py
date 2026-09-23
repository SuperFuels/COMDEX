from pathlib import Path

APP = Path("desktop/mac/src/app.js")


def test_goal_engine_learning_panel_renderer_exists():
    text = APP.read_text()
    assert "function renderAionGoalEngineLearningPanelV1" in text
    assert 'data-aion-goal-engine-learning-panel="v1"' in text
    assert "What AION Learned" in text


def test_goal_engine_learning_panel_reads_live_payload_fields():
    text = APP.read_text()
    block = text[
        text.index("function renderAionGoalEngineLearningPanelV1"):
        text.index("/* AION PATCH: Goal Engine Live KPI Boardroom Visibility v1 */")
    ]

    for field in [
        "learning_runtime_summary",
        "learning_reflection_summary",
        "goal_engine_learning_runtime_summary",
        "learning_items",
        "reflections",
        "insights",
        "confidence",
        "next_action",
        "machine_trace",
        "goal_engine_boardroom_runtime_preview",
    ]:
        assert field in block


def test_goal_engine_learning_panel_visible_labels_are_present():
    text = APP.read_text()
    block = text[
        text.index("function renderAionGoalEngineLearningPanelV1"):
        text.index("/* AION PATCH: Goal Engine Live KPI Boardroom Visibility v1 */")
    ]

    for label in [
        "Learning items",
        "Confidence",
        "Next:",
        "No learning reflections attached yet.",
    ]:
        assert label in block


def test_goal_engine_learning_panel_is_read_only():
    text = APP.read_text()
    block = text[
        text.index("function renderAionGoalEngineLearningPanelV1"):
        text.index("/* AION PATCH: Goal Engine Live KPI Boardroom Visibility v1 */")
    ]

    assert "Read-only learning/reflection telemetry" in block
    assert "addSection" not in block


def test_goal_engine_learning_panel_mounts_after_live_kpis():
    text = APP.read_text()
    assert "renderAionGoalEngineLearningPanelV1(snapshot)" in text
    assert text.index("renderAionGoalEngineLiveKpiPanelV1(snapshot)") < text.index(
        "renderAionGoalEngineLearningPanelV1(snapshot)"
    )


def test_goal_engine_learning_panel_exported_to_window():
    text = APP.read_text()
    assert "window.renderAionGoalEngineLearningPanelV1" in text
