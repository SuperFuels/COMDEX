from pathlib import Path

APP = Path("desktop/mac/src/app.js")


def read_app():
    return APP.read_text(encoding="utf-8")


def test_goal_engine_inspector_renderer_is_installed():
    text = read_app()

    assert "Goal Engine node inspector contract fields v1" in text
    assert "window.__isAionGoalEngineNode" in text
    assert "window.__renderAionGoalEngineInspectorBlockV1" in text
    assert 'data-aion-goal-engine-inspector-fields="true"' in text


def test_goal_engine_inspector_shows_core_safety_contract():
    text = read_app()

    assert "Dry-run only" in text
    assert "Grants no permission" in text
    assert "Approval required before external writes" in text
    assert "No unbounded execution" in text
    assert "blocked while adr_active=true" in text


def test_goal_engine_inspector_exposes_runtime_guard_fields():
    text = read_app()

    assert "Max iterations" in text
    assert "Max runtime" in text
    assert "Max spend" in text
    assert "Checkpoint" in text
    assert "Resume revalidation" in text
    assert "Evidence" in text
    assert "Learning guard" in text


def test_goal_engine_inspector_detects_all_goal_engine_actions():
    text = read_app()

    assert 'action_id: "goal_engine.goal"' in text
    assert 'action_id: "goal_engine.experiment"' in text
    assert 'action_id: "goal_engine.loop"' in text
    assert 'action_id: "goal_engine.outcome_evaluation"' in text
    assert 'action_id: "goal_engine.reflect_learn"' in text
    assert 'action_id: "goal_engine.state_delta_accumulator"' in text
    assert 'action_id: "goal_engine.environment_revalidation"' in text
