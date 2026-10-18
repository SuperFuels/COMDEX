from pathlib import Path

APP = Path("desktop/mac/src/app.js")


def read_app() -> str:
    return APP.read_text(encoding="utf-8")


def test_goal_engine_architect_catalogue_has_valid_group_shape():
    text = read_app()

    assert 'group: "Goal Engine"' in text
    assert 'group_id: "goal_engine"' in text
    assert 'description: "Managed-agent goals' in text
    assert 'modules: [' in text


def test_goal_engine_architect_catalogue_exposes_required_modules():
    text = read_app()

    assert 'id: "goal_engine.goal"' in text
    assert 'id: "goal_engine.experiment"' in text
    assert 'id: "goal_engine.loop"' in text
    assert 'id: "goal_engine.outcome_evaluation"' in text
    assert 'id: "goal_engine.reflect_learn"' in text
    assert 'id: "goal_engine.state_delta_accumulator"' in text
    assert 'id: "goal_engine.environment_revalidation"' in text


def test_goal_engine_architect_picker_uses_group_id_and_modules():
    text = read_app()

    assert "window.__aionArchitectModulePickerGroup" in text
    assert 'data-aion-architect-module-group' in text
    assert "selectedGroup.modules.map" in text
    assert 'data-aion-architect-pick-module' in text
