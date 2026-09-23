from pathlib import Path

APP = Path("desktop/mac/src/app.js")


def test_goal_engine_decomposition_tree_renderer_exists():
    text = APP.read_text()
    assert "function renderAionGoalEngineDecompositionTreePanelV1" in text
    assert 'data-aion-goal-engine-decomposition-tree="v1"' in text
    assert "Goal Decomposition Tree" in text


def test_goal_engine_decomposition_tree_reads_live_payload_fields():
    text = APP.read_text()
    block = text[
        text.index("function renderAionGoalEngineDecompositionTreePanelV1"):
        text.index("/* AION PATCH: Goal Engine Exploration Exploitation Boardroom Visibility v1 */")
    ]

    for field in [
        "decomposition_summary",
        "goal_decomposition_summary",
        "hierarchical_goal_decomposition",
        "child_goals",
        "children",
        "subgoals",
        "tree_depth",
        "parent_goal",
        "parent_goal_id",
        "machine_trace",
        "goal_engine_boardroom_runtime_preview",
    ]:
        assert field in block


def test_goal_engine_decomposition_tree_visible_labels_are_present():
    text = APP.read_text()
    block = text[
        text.index("function renderAionGoalEngineDecompositionTreePanelV1"):
        text.index("/* AION PATCH: Goal Engine Exploration Exploitation Boardroom Visibility v1 */")
    ]

    for label in [
        "Parent goal",
        "Child goals",
        "Tree depth",
        "Blocked",
        "No child goals attached yet.",
        "No parent goal attached yet.",
    ]:
        assert label in block


def test_goal_engine_decomposition_tree_is_read_only():
    text = APP.read_text()
    block = text[
        text.index("function renderAionGoalEngineDecompositionTreePanelV1"):
        text.index("/* AION PATCH: Goal Engine Exploration Exploitation Boardroom Visibility v1 */")
    ]

    assert "Read-only parent/child goal structure" in block
    assert "addSection" not in block


def test_goal_engine_decomposition_tree_mounts_after_exploration_panel():
    text = APP.read_text()
    assert "renderAionGoalEngineDecompositionTreePanelV1(snapshot)" in text
    assert text.index("renderAionGoalEngineExplorationExploitationPanelV1(snapshot)") < text.index(
        "renderAionGoalEngineDecompositionTreePanelV1(snapshot)"
    )


def test_goal_engine_decomposition_tree_exported_to_window():
    text = APP.read_text()
    assert "window.renderAionGoalEngineDecompositionTreePanelV1" in text
