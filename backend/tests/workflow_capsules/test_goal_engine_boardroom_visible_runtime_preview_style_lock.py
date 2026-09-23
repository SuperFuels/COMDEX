from pathlib import Path


APP = Path("desktop/mac/src/app.js")
CSS = Path("desktop/mac/src/styles.css")


def test_boardroom_dashboard_calls_visible_goal_engine_panel():
    text = APP.read_text()

    assert "function renderAionGoalEngineVisibleBoardroomPanelsV1" in text
    assert "${renderAionGoalEngineVisibleBoardroomPanelsV1(snapshot)}" in text
    assert 'data-aion-goal-engine-visible-boardroom-panels="true"' in text
    assert "Goal Engine Runtime Preview" in text


def test_boardroom_goal_engine_panel_includes_all_runtime_sections():
    text = APP.read_text()

    required = [
        "Outcome Evidence Summary",
        "Checkpoint / Resume Summary",
        "Resume Revalidation Summary",
        "Experiment Runtime Summary",
        "Orchestrator Runtime Summary",
        "Goal Decomposition Summary",
    ]

    for item in required:
        assert item in text


def test_boardroom_goal_engine_panel_includes_warning_states():
    text = APP.read_text()

    required = [
        "outcome_success_requires_evidence",
        "Resume requires environment revalidation",
        "External state changed",
        "Unbounded experiment plan blocked",
        "Premature convergence blocked",
        "Unbounded orchestration blocked",
    ]

    for item in required:
        assert item in text


def test_boardroom_goal_engine_panel_exposes_evidence_freshness_and_provenance():
    text = APP.read_text()

    assert "Evidence Freshness" in text
    assert "Evidence Provenance" in text
    assert "source_connector" in text
    assert "source_ref" in text


def test_boardroom_goal_engine_runtime_preview_has_style_classes():
    css = CSS.read_text()

    required = [
        ".aion-goal-engine-visible-boardroom-panels",
        ".aion-boardroom-runtime-summary",
        ".aion-boardroom-runtime-grid",
        ".aion-boardroom-warning",
        ".aion-boardroom-mini-row",
        ".aion-boardroom-evidence-row",
    ]

    for item in required:
        assert item in css
