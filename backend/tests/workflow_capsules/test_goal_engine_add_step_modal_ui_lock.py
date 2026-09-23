from pathlib import Path

APP = Path("desktop/mac/src/app.js")


def read_app() -> str:
    return APP.read_text(encoding="utf-8")


def test_goal_engine_add_step_category_exists_and_is_filterable():
    text = read_app()

    assert "Goal Engine" in text
    assert "goal_engine" in text
    assert "selected" in text.lower()
    assert "category" in text.lower()


def test_goal_engine_add_step_modules_are_visible_in_modal_contract():
    text = read_app()

    required = [
        "goal_engine.goal",
        "goal_engine.experiment",
        "goal_engine.loop",
        "goal_engine.outcome_evaluation",
        "goal_engine.reflect_learn",
        "goal_engine.state_delta_accumulator",
        "goal_engine.environment_revalidation",
    ]

    for item in required:
        assert item in text


def test_goal_engine_add_step_modal_uses_alias_resolution_before_node_creation():
    text = read_app()

    alias_idx = text.find("__resolveAionGoalEngineWorkflowActionAlias")
    create_idx = min(
        idx for idx in [
            text.find("create", alias_idx),
            text.find("add", alias_idx),
            text.find("node", alias_idx),
        ]
        if idx != -1
    )

    assert alias_idx != -1
    assert create_idx != -1
    assert alias_idx < create_idx
