from pathlib import Path

APP = Path("desktop/mac/src/app.js")


def test_goal_engine_live_kpi_panel_renderer_exists():
    text = APP.read_text()
    assert "function renderAionGoalEngineLiveKpiPanelV1" in text
    assert 'data-aion-goal-engine-live-kpis="v1"' in text
    assert "Goal Engine Live KPIs" in text


def test_goal_engine_live_kpi_panel_reads_live_payload_fields():
    text = APP.read_text()
    block = text[
        text.index("function renderAionGoalEngineLiveKpiPanelV1"):
        text.index("/* AION PATCH: Goal Engine Provider Degradation Feed Boardroom Visibility v1 */")
    ]

    for field in [
        "active_goals",
        "loop_iteration_count",
        "approvals_waiting",
        "blocked_reasons",
        "outcome_score",
        "goal_runtime_summary",
        "machine_trace",
        "goal_engine_boardroom_runtime_preview",
    ]:
        assert field in block


def test_goal_engine_live_kpi_panel_visible_labels_are_present():
    text = APP.read_text()
    block = text[
        text.index("function renderAionGoalEngineLiveKpiPanelV1"):
        text.index("/* AION PATCH: Goal Engine Provider Degradation Feed Boardroom Visibility v1 */")
    ]

    for label in [
        "Active goals",
        "Loop iterations",
        "Approvals waiting",
        "Blocked reasons",
        "Outcome score",
    ]:
        assert label in block


def test_goal_engine_live_kpi_panel_is_visibility_only():
    text = APP.read_text()
    block = text[
        text.index("function renderAionGoalEngineLiveKpiPanelV1"):
        text.index("/* AION PATCH: Goal Engine Provider Degradation Feed Boardroom Visibility v1 */")
    ]

    assert "Visibility only" in block
    assert "does not mutate goals or approvals" in block


def test_goal_engine_live_kpi_panel_mounts_before_provider_runtime_metrics():
    text = APP.read_text()
    assert "renderAionGoalEngineLiveKpiPanelV1(snapshot)" in text
    assert text.index("renderAionGoalEngineLiveKpiPanelV1(snapshot)") < text.index(
        "renderAionGoalEngineProviderRuntimeMetricsPanelV1(snapshot)"
    )


def test_goal_engine_live_kpi_panel_exported_to_window():
    text = APP.read_text()
    assert "window.renderAionGoalEngineLiveKpiPanelV1" in text
