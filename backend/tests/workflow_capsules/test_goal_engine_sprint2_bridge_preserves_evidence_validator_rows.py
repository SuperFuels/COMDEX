from pathlib import Path


BRIDGE = Path("backend/modules/workflow_capsules/execution/goal_engine_dry_run_bridge.py")


def test_bridge_preserves_goal_runtime_summary_validator_rows_from_bundle():
    text = BRIDGE.read_text()

    assert 'canonical_goal_runtime_summary = bundle_payload.get("goal_runtime_summary")' in text
    assert 'payload["goal_runtime_summary"] = canonical_goal_runtime_summary' in text
    assert 'payload["goal_engine_goal_runtime_summary"] = canonical_goal_runtime_summary' in text


def test_bridge_does_not_rebuild_outcome_evidence_summary():
    text = BRIDGE.read_text()
    section_marker = "# AION PATCH: Goal Engine canonical preview bundle bridge final override v13"

    assert section_marker in text
    section = text[text.index(section_marker):]

    assert "summarize_outcome_evidence_state(" not in section
    assert "summarize_evidence_sources(" not in section
    assert "build_outcome_score_preview(" not in section


def test_bridge_comment_documents_bundle_owns_evidence_rows():
    text = BRIDGE.read_text()

    assert "GoalEnginePreviewBundle is the single source of truth" in text
    assert "validator rows" in text
    assert "outcome_evidence_summary" in text
