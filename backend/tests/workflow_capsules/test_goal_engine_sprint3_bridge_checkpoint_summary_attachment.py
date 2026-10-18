from pathlib import Path


BRIDGE = Path("backend/modules/workflow_capsules/execution/goal_engine_dry_run_bridge.py")


def test_bridge_attaches_checkpoint_runtime_summary_from_bundle():
    text = BRIDGE.read_text()

    assert 'canonical_checkpoint_runtime_summary = bundle_payload.get("checkpoint_runtime_summary")' in text
    assert 'setattr(dry_result, "goal_engine_checkpoint_runtime_summary", canonical_checkpoint_runtime_summary)' in text
    assert 'setattr(dry_result, "checkpoint_runtime_summary", canonical_checkpoint_runtime_summary)' in text


def test_bridge_payload_exposes_checkpoint_runtime_summary_legacy_mirror():
    text = BRIDGE.read_text()

    assert 'payload["goal_engine_checkpoint_runtime_summary"] = canonical_checkpoint_runtime_summary' in text
    assert 'payload["checkpoint_runtime_summary"] = canonical_checkpoint_runtime_summary' in text


def test_bridge_does_not_rebuild_checkpoint_state_delta_summary():
    text = BRIDGE.read_text()
    marker = "# AION PATCH: Goal Engine canonical preview bundle bridge final override v13"

    assert marker in text
    section = text[text.index(marker):]

    assert "build_checkpoint_preview(" not in section
    assert "build_state_delta_preview(" not in section
    assert "_build_checkpoint_runtime_summary(" not in section
