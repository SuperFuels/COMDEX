from pathlib import Path


BRIDGE = Path("backend/modules/workflow_capsules/execution/goal_engine_dry_run_bridge.py")


def test_bridge_attaches_goal_runtime_summary_from_canonical_bundle():
    text = BRIDGE.read_text()

    assert "canonical_goal_runtime_summary" in text
    assert 'bundle_payload.get("goal_runtime_summary")' in text
    assert 'setattr(dry_result, "goal_engine_goal_runtime_summary", canonical_goal_runtime_summary)' in text


def test_bridge_payload_exposes_goal_runtime_summary_legacy_mirror():
    text = BRIDGE.read_text()

    assert 'payload["goal_engine_goal_runtime_summary"] = canonical_goal_runtime_summary' in text
    assert 'payload["goal_runtime_summary"] = canonical_goal_runtime_summary' in text


def test_bridge_runtime_summary_attachment_stays_inside_v13_final_override():
    text = BRIDGE.read_text()

    marker = "# AION PATCH: Goal Engine canonical preview bundle bridge final override v13"
    section = text[text.index(marker):]

    assert "canonical_goal_runtime_summary" in section
    assert "goal_engine_goal_runtime_summary" in section
