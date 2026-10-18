from pathlib import Path

APP = Path("desktop/mac/src/app.js")


def read_app() -> str:
    return APP.read_text(encoding="utf-8")


def test_goal_engine_architect_inspector_persistence_installed():
    text = read_app()

    assert "Goal Engine architect inspector field persistence v1" in text
    assert "__syncAionGoalEngineConfigForStepV1" in text
    assert "__aionGoalEngineArchitectInspectorFieldPersistenceV1" in text


def test_goal_engine_architect_inspector_fields_persist_to_config():
    text = read_app()

    assert "data-aion-goal-engine-field" in text
    assert "metric_target" in text
    assert "metric_name" in text
    assert "max_iterations" in text
    assert "evidence_refs" in text
    assert "config[key] = step[key]" in text


def test_goal_engine_architect_inspector_normalises_safe_fields():
    text = read_app()

    assert "normaliseGoalEngineFieldValue" in text
    assert "Math.max(0, Math.min(n, 100))" in text
    assert '.split(",")' in text
    assert "persistAionWorkflowDraftState" in text
