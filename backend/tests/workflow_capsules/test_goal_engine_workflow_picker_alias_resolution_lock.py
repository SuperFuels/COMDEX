from pathlib import Path

APP = Path("desktop/mac/src/app.js")


def read_app():
    return APP.read_text(encoding="utf-8")


def test_goal_engine_alias_resolver_exists():
    text = read_app()

    assert "window.__aionGoalEngineWorkflowActionAliases" in text
    assert "window.__resolveAionGoalEngineWorkflowActionAlias" in text
    assert 'goal_engine_goal: "goal_engine.goal"' in text
    assert 'goal_engine_environment_revalidation: "goal_engine.environment_revalidation"' in text


def test_create_action_handler_resolves_goal_engine_aliases_before_node_creation():
    text = read_app()

    assert 'const rawActionType = actionButton.getAttribute("data-aion-workflow-create-action");' in text
    assert 'window.__resolveAionGoalEngineWorkflowActionAlias(rawActionType)' in text

    # There were two create-action handlers in app.js. Both should now resolve aliases.
    assert text.count("window.__resolveAionGoalEngineWorkflowActionAlias(rawActionType)") >= 2


def test_picker_uses_human_readable_goal_engine_aliases_not_raw_catalog_ids():
    text = read_app()

    assert 'data-aion-workflow-create-action="goal_engine_goal"' in text
    assert 'data-aion-workflow-create-action="goal_engine_experiment"' in text
    assert 'data-aion-workflow-create-action="goal_engine_loop"' in text
    assert 'data-aion-workflow-create-action="goal_engine_outcome_evaluation"' in text
    assert 'data-aion-workflow-create-action="goal_engine_reflect_learn"' in text
    assert 'data-aion-workflow-create-action="goal_engine_state_delta_accumulator"' in text
    assert 'data-aion-workflow-create-action="goal_engine_environment_revalidation"' in text


def test_catalog_uses_canonical_goal_engine_action_ids():
    text = read_app()

    assert 'action_id: "goal_engine.goal"' in text
    assert 'action_id: "goal_engine.experiment"' in text
    assert 'action_id: "goal_engine.loop"' in text
    assert 'action_id: "goal_engine.outcome_evaluation"' in text
    assert 'action_id: "goal_engine.reflect_learn"' in text
    assert 'action_id: "goal_engine.state_delta_accumulator"' in text
    assert 'action_id: "goal_engine.environment_revalidation"' in text
