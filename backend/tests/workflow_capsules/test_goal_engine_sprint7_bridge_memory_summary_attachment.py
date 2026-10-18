from pathlib import Path


BRIDGE = Path("backend/modules/workflow_capsules/execution/goal_engine_dry_run_bridge.py")


def test_bridge_attaches_memory_runtime_summary_from_bundle():
    text = BRIDGE.read_text()

    assert 'canonical_memory_runtime_summary = bundle_payload.get("memory_runtime_summary")' in text
    assert 'setattr(dry_result, "goal_engine_memory_runtime_summary", canonical_memory_runtime_summary)' in text
    assert 'setattr(dry_result, "memory_runtime_summary", canonical_memory_runtime_summary)' in text


def test_bridge_payload_exposes_memory_runtime_summary_legacy_mirror():
    text = BRIDGE.read_text()

    assert 'payload["goal_engine_memory_runtime_summary"] = canonical_memory_runtime_summary' in text
    assert 'payload["memory_runtime_summary"] = canonical_memory_runtime_summary' in text


def test_bridge_does_not_rebuild_memory_runtime_summary():
    text = BRIDGE.read_text()

    marker = 'canonical_memory_runtime_summary = bundle_payload.get("memory_runtime_summary")'
    assert marker in text

    section = text[text.index(marker): text.index("return dry_result", text.index(marker))]

    assert "_build_memory_runtime_summary(" not in section
    assert "build_memory_record_preview(" not in section
    assert "build_memory_policy_preview(" not in section
