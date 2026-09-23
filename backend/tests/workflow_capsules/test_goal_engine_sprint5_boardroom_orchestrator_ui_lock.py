from pathlib import Path


APP = Path("desktop/mac/src/app.js")


def test_boardroom_ui_references_orchestrator_runtime_summary():
    text = APP.read_text()

    assert "orchestrator_runtime_summary" in text
    assert "goal_engine_orchestrator_runtime_summary" in text


def test_boardroom_ui_has_orchestrator_summary_renderer():
    text = APP.read_text()

    assert "renderAionGoalEngineOrchestratorSummaryV1" in text
    assert "getAionGoalEngineOrchestratorRuntimeSummaryV1" in text
    assert "Orchestrator Runtime Summary" in text


def test_boardroom_ui_shows_orchestrator_counts_and_policy():
    text = APP.read_text()

    for expected in [
        "Orchestrators",
        "Agents",
        "Bounded",
        "Unbounded",
        "coordination_mode",
        "conflict_policy",
        "max_parallel_agents",
        "child_timeout_seconds",
    ]:
        assert expected in text


def test_boardroom_ui_shows_orchestrator_warnings_and_agent_rows():
    text = APP.read_text()

    for expected in [
        "Unbounded orchestration blocked",
        "unbounded_orchestration_blocked",
        "Agent assignments",
        "glyph_code",
        "role",
    ]:
        assert expected in text
