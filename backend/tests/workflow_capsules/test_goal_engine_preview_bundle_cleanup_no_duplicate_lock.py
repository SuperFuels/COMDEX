from pathlib import Path

PREVIEW = Path("backend/modules/aion/goal_engine/preview_bundle.py")
APP = Path("desktop/mac/src/app.js")


def test_goal_engine_preview_bundle_has_single_dataclass_and_builder():
    text = PREVIEW.read_text()

    assert text.count("class GoalEnginePreviewBundle:") == 1
    assert text.count("def build_goal_engine_preview_bundle(") == 1
    assert text.count("def to_dict(self) -> dict[str, Any]:") == 1


def test_goal_engine_preview_bundle_has_single_runtime_summary_builders():
    text = PREVIEW.read_text()

    assert text.count("def _build_orchestrator_parent_child_aggregation_runtime_summary(") == 1
    assert text.count("def _build_goal_decomposition_runtime_summary(") == 1
    assert text.count("def _build_memory_runtime_summary(") == 1


def test_preview_bundle_keeps_canonical_top_level_preview_fields():
    text = PREVIEW.read_text()

    required = [
        "goal_decomposition_previews: list[dict[str, Any]]",
        "memory_record_previews: list[dict[str, Any]]",
        "memory_policy_previews: list[dict[str, Any]]",
        "parent_child_aggregation_previews: list[dict[str, Any]]",
    ]

    for token in required:
        assert token in text


def test_preview_bundle_keeps_compatibility_mirrors_explicit_only():
    text = PREVIEW.read_text()

    # These mirrors are still intentional because Boardroom/dry-run bridge tests read them.
    required_mirrors = [
        '"goal_engine_decomposition_runtime_summary"',
        '"decomposition_previews"',
        '"child_goal_previews"',
        '"goal_engine_memory_record_previews"',
        '"goal_engine_memory_policy_previews"',
        '"orchestrator_parent_child_aggregation_runtime_summary"',
        '"orchestrator_parent_child_aggregation_previews"',
    ]

    for token in required_mirrors:
        assert token in text


def test_preview_bundle_machine_trace_gets_each_attachment_once():
    text = PREVIEW.read_text()

    # Assignment should exist once in the canonical build function, not be appended repeatedly.
    assert text.count('machine_trace["parent_child_aggregation_runtime_summary"] = parent_child_aggregation_runtime_summary') == 1
    assert text.count('machine_trace["goal_decomposition_runtime_summary"] = goal_decomposition_runtime_summary') == 1
    assert text.count('machine_trace["memory_runtime_summary"] = memory_runtime_summary') == 1

    assert text.count('machine_trace["parent_child_aggregation_previews"]') == 1
    assert text.count('machine_trace["goal_decomposition_previews"]') == 1
    assert text.count('machine_trace["memory_record_previews"]') == 1
    assert text.count('machine_trace["memory_policy_previews"]') == 1


def test_app_has_single_parent_child_panel_block():
    text = APP.read_text()

    assert text.count("AION-GOAL-ENGINE-PARENT-CHILD-ORCHESTRATION-PANEL-V1:START") == 1
    assert text.count("AION-GOAL-ENGINE-PARENT-CHILD-ORCHESTRATION-PANEL-V1:END") == 1
    assert text.count("function renderAionGoalEngineParentChildOrchestrationPanelV1") == 1


def test_app_visibility_polish_overrides_are_known_and_limited():
    text = APP.read_text()

    # These are currently intentional wrappers from the visibility polish lock.
    assert text.count("AION-GOAL-ENGINE-BOARDROOM-VISIBILITY-POLISH-V1:START") == 1
    assert text.count("AION-GOAL-ENGINE-BOARDROOM-VISIBILITY-POLISH-V1:END") == 1

    assert text.count("window.renderAionGoalEngineVariantComparisonViewerV1 = function renderAionGoalEngineVariantComparisonViewerV1") <= 1
    assert text.count("window.renderAionGoalEngineMemoryRuntimePanelV1 = function renderAionGoalEngineMemoryRuntimePanelV1") <= 1
