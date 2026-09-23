from pathlib import Path


BRIDGE = Path("backend/modules/workflow_capsules/execution/goal_engine_dry_run_bridge.py")


def test_bridge_attaches_orchestrator_runtime_summary_from_bundle():
    text = BRIDGE.read_text()

    assert 'canonical_orchestrator_runtime_summary = bundle_payload.get("orchestrator_runtime_summary")' in text
    assert 'setattr(dry_result, "goal_engine_orchestrator_runtime_summary", canonical_orchestrator_runtime_summary)' in text
    assert 'setattr(dry_result, "orchestrator_runtime_summary", canonical_orchestrator_runtime_summary)' in text


def test_bridge_payload_exposes_orchestrator_runtime_summary_legacy_mirror():
    text = BRIDGE.read_text()

    assert 'payload["goal_engine_orchestrator_runtime_summary"] = canonical_orchestrator_runtime_summary' in text
    assert 'payload["orchestrator_runtime_summary"] = canonical_orchestrator_runtime_summary' in text


def test_bridge_does_not_rebuild_orchestrator_runtime_summary():
    text = BRIDGE.read_text()
    marker = 'canonical_orchestrator_runtime_summary = bundle_payload.get("orchestrator_runtime_summary")'
    assert marker in text

    section = text[text.index(marker):]

    assert "build_orchestrator_preview(" not in section
    assert "_build_orchestrator_runtime_summary(" not in section
    assert "OrchestratorContract(" not in section
    assert "AgentAssignmentContract(" not in section
