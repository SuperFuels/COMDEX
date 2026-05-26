from pathlib import Path

APP = Path("desktop/mac/src/app.js")


def read_app() -> str:
    return APP.read_text(encoding="utf-8")


def test_goal_engine_alias_resolves_before_create_action_usage():
    text = read_app()

    raw_idx = text.find('const rawActionType = actionButton.getAttribute("data-aion-workflow-create-action");')
    resolver_idx = text.find("__resolveAionGoalEngineWorkflowActionAlias", raw_idx)
    action_type_idx = text.find("const actionType", raw_idx)

    assert raw_idx != -1
    assert resolver_idx != -1
    assert action_type_idx != -1
    assert raw_idx < action_type_idx
    assert resolver_idx < text.find("add", action_type_idx) or resolver_idx < text.find("create", action_type_idx)


def test_goal_engine_alias_resolution_is_synchronous_not_deferred():
    text = read_app()

    resolver_block_idx = text.find("window.__resolveAionGoalEngineWorkflowActionAlias")
    assert resolver_block_idx != -1

    nearby = text[resolver_block_idx:resolver_block_idx + 1200]

    assert "setTimeout" not in nearby
    assert "Promise" not in nearby
    assert "await" not in nearby
    assert "async" not in nearby


def test_picker_alias_values_stay_mapped_to_canonical_catalog_ids():
    text = read_app()

    assert 'goal_engine_goal: "goal_engine.goal"' in text
    assert 'goal_engine_experiment: "goal_engine.experiment"' in text
    assert 'goal_engine_loop: "goal_engine.loop"' in text
    assert 'goal_engine_outcome_evaluation: "goal_engine.outcome_evaluation"' in text
    assert 'goal_engine_reflect_learn: "goal_engine.reflect_learn"' in text
    assert 'goal_engine_state_delta_accumulator: "goal_engine.state_delta_accumulator"' in text
    assert 'goal_engine_environment_revalidation: "goal_engine.environment_revalidation"' in text
