from pathlib import Path


BRIDGE = Path("backend/modules/workflow_capsules/execution/goal_engine_dry_run_bridge.py")


def test_bridge_attaches_goal_decomposition_runtime_summary_from_bundle():
    text = BRIDGE.read_text()

    assert 'canonical_goal_decomposition_runtime_summary = bundle_payload.get("goal_decomposition_runtime_summary")' in text
    assert 'setattr(dry_result, "goal_engine_goal_decomposition_runtime_summary", canonical_goal_decomposition_runtime_summary)' in text
    assert 'setattr(dry_result, "goal_decomposition_runtime_summary", canonical_goal_decomposition_runtime_summary)' in text


def test_bridge_payload_exposes_goal_decomposition_runtime_summary_legacy_mirror():
    text = BRIDGE.read_text()

    assert 'payload["goal_engine_goal_decomposition_runtime_summary"] = canonical_goal_decomposition_runtime_summary' in text
    assert 'payload["goal_decomposition_runtime_summary"] = canonical_goal_decomposition_runtime_summary' in text


def test_bridge_does_not_rebuild_goal_decomposition_runtime_summary():
    text = BRIDGE.read_text()

    marker = 'canonical_goal_decomposition_runtime_summary = bundle_payload.get("goal_decomposition_runtime_summary")'
    assert marker in text

    section = text[text.index(marker):]

    assert "build_goal_decomposition_preview(" not in section
    assert "_build_goal_decomposition_runtime_summary(" not in section
    assert "GoalDecompositionContract(" not in section
    assert "SubGoalContract(" not in section
