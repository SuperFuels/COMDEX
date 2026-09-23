from pathlib import Path


BRIDGE = Path("backend/modules/workflow_capsules/execution/goal_engine_dry_run_bridge.py")


def test_bridge_has_final_preview_bundle_override_v13():
    text = BRIDGE.read_text()

    assert "Goal Engine canonical preview bundle bridge final override v13" in text
    assert "build_goal_engine_preview_bundle" in text
    assert "GoalEnginePreviewBundle is the single source of truth" in text


def test_bridge_uses_contracts_for_current_preview_bundle_signature():
    text = BRIDGE.read_text()

    assert "def _aion_goal_engine_contracts_from_capsule_v13" in text
    assert "contracts = _aion_goal_engine_contracts_from_capsule_v13(capsule)" in text
    assert "contracts=contracts" in text


def test_bridge_attaches_bundle_and_legacy_mirrors():
    text = BRIDGE.read_text()

    assert 'payload["goal_engine_preview_bundle"] = bundle_payload' in text
    assert 'payload["goal_engine_manifest"] = canonical_manifest' in text
    assert 'payload["goal_engine"] = canonical_manifest' in text
    assert 'payload["goal_engine_step_trace"] = canonical_step_trace' in text
    assert 'payload["goal_engine_boardroom_trace"] = canonical_boardroom_trace' in text
    assert 'payload["goal_engine_machine_trace"] = canonical_machine_trace' in text


def test_final_attach_override_does_not_call_duplicate_step_trace_attachment():
    text = BRIDGE.read_text()

    marker = "# AION PATCH: Goal Engine canonical preview bundle bridge final override v13"
    section = text[text.index(marker):]

    assert "attach_goal_engine_step_trace_rows_to_dry_result(" not in section
