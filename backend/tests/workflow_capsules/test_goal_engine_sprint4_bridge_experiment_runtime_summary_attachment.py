from pathlib import Path


BRIDGE = Path("backend/modules/workflow_capsules/execution/goal_engine_dry_run_bridge.py")


def test_bridge_attaches_experiment_runtime_summary_from_bundle():
    text = BRIDGE.read_text()

    assert 'canonical_experiment_runtime_summary = bundle_payload.get("experiment_runtime_summary")' in text
    assert 'setattr(dry_result, "goal_engine_experiment_runtime_summary", canonical_experiment_runtime_summary)' in text
    assert 'setattr(dry_result, "experiment_runtime_summary", canonical_experiment_runtime_summary)' in text


def test_bridge_payload_exposes_experiment_runtime_summary_legacy_mirror():
    text = BRIDGE.read_text()

    assert 'payload["goal_engine_experiment_runtime_summary"] = canonical_experiment_runtime_summary' in text
    assert 'payload["experiment_runtime_summary"] = canonical_experiment_runtime_summary' in text


def test_bridge_does_not_rebuild_experiment_runtime_summary():
    text = BRIDGE.read_text()

    marker = "# AION PATCH: Goal Engine canonical preview bundle bridge final override v13"
    section = text[text.index(marker):]

    assert "build_experiment_policy_preview(" not in section
    assert "_build_experiment_runtime_summary(" not in section
    assert "ExperimentPolicyContract(" not in section
