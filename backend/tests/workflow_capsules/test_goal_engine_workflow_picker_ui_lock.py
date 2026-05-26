from pathlib import Path

APP = Path("desktop/mac/src/app.js")


def read_app():
    return APP.read_text(encoding="utf-8")


def test_goal_engine_section_visible_in_workflow_picker():
    text = read_app()

    assert "Goal Engine" in text
    assert 'data-aion-workflow-create-action="goal_engine_goal"' in text
    assert 'data-aion-workflow-create-action="goal_engine_experiment"' in text
    assert 'data-aion-workflow-create-action="goal_engine_loop"' in text
    assert 'data-aion-workflow-create-action="goal_engine_outcome_evaluation"' in text
    assert 'data-aion-workflow-create-action="goal_engine_reflect_learn"' in text
    assert 'data-aion-workflow-create-action="goal_engine_state_delta_accumulator"' in text
    assert 'data-aion-workflow-create-action="goal_engine_environment_revalidation"' in text


def test_goal_engine_catalog_nodes_are_dry_run_safe():
    text = read_app()

    assert 'action_id: "goal_engine.goal"' in text
    assert 'action_id: "goal_engine.experiment"' in text
    assert 'action_id: "goal_engine.loop"' in text
    assert 'action_id: "goal_engine.outcome_evaluation"' in text
    assert 'action_id: "goal_engine.reflect_learn"' in text
    assert 'action_id: "goal_engine.state_delta_accumulator"' in text
    assert 'action_id: "goal_engine.environment_revalidation"' in text

    assert "Dry-run only" in text or "dry-run only" in text
    assert "grants no permission" in text
    assert "no unbounded execution" in text


def test_goal_engine_aliases_map_picker_to_catalog_actions():
    text = read_app()

    assert 'goal_engine_goal: "goal_engine.goal"' in text
    assert 'goal_engine_experiment: "goal_engine.experiment"' in text
    assert 'goal_engine_loop: "goal_engine.loop"' in text
    assert 'goal_engine_outcome_evaluation: "goal_engine.outcome_evaluation"' in text
    assert 'goal_engine_reflect_learn: "goal_engine.reflect_learn"' in text
    assert 'goal_engine_state_delta_accumulator: "goal_engine.state_delta_accumulator"' in text
    assert 'goal_engine_environment_revalidation: "goal_engine.environment_revalidation"' in text
