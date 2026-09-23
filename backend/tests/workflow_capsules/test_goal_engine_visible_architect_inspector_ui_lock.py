from pathlib import Path

APP = Path("desktop/mac/src/app.js")


def read_app() -> str:
    return APP.read_text(encoding="utf-8")


def test_visible_goal_engine_architect_inspector_renderer_exists():
    text = read_app()

    assert "renderAionGoalEngineArchitectInspectorBlockV1" in text
    assert "isAionGoalEngineArchitectStepV1" in text
    assert 'data-aion-goal-engine-architect-inspector="true"' in text


def test_visible_goal_engine_architect_inspector_has_safety_fields():
    text = read_app()

    assert "Dry-run only" in text
    assert "Grants permission" in text
    assert "External writes" in text
    assert "approval gated" in text
    assert "Bounded execution" in text
    assert "Learning guard" in text


def test_visible_goal_engine_architect_inspector_has_config_fields():
    text = read_app()

    assert 'data-aion-goal-engine-field="metric_target"' in text
    assert 'data-aion-goal-engine-field="metric_name"' in text
    assert 'data-aion-goal-engine-field="max_iterations"' in text
    assert 'data-aion-goal-engine-field="evidence_refs"' in text
