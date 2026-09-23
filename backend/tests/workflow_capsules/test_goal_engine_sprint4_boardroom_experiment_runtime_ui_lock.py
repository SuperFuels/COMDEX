from pathlib import Path


APP = Path("desktop/mac/src/app.js")


def test_boardroom_ui_references_experiment_runtime_summary():
    text = APP.read_text()

    assert "experiment_runtime_summary" in text
    assert "goal_engine_experiment_runtime_summary" in text


def test_boardroom_ui_has_experiment_runtime_renderer():
    text = APP.read_text()

    assert "renderAionGoalEngineExperimentRuntimeSummaryV1" in text
    assert "getAionGoalEngineExperimentRuntimeSummaryV1" in text
    assert "Experiment Runtime Summary" in text


def test_boardroom_ui_shows_experiment_policy_counts_and_blocks():
    text = APP.read_text()

    for expected in [
        "Experiments",
        "Bounded",
        "Unbounded",
        "Variants",
        "Metrics",
        "Unbounded experiment plan blocked",
        "Premature convergence blocked",
    ]:
        assert expected in text


def test_boardroom_ui_shows_exploration_policy_fields():
    text = APP.read_text()

    for expected in [
        "exploration_factor",
        "exploration_decay",
        "min_exploration_floor",
        "confidence_threshold",
        "max_iterations",
        "max_runtime_minutes",
    ]:
        assert expected in text
