from pathlib import Path


LOCK = Path("docs/rfc/aion_goal_engine_sprint3_checkpoint_resume_lock.tex")


def test_sprint3_lock_doc_exists():
    assert LOCK.exists()


def test_sprint3_lock_records_checkpoint_and_state_delta_contracts():
    text = LOCK.read_text()

    assert "STATE_DELTA_SCHEMA_VERSION" in text
    assert "CHECKPOINT_SCHEMA_VERSION" in text
    assert "full_payload_not_allowed" in text
    assert "resume_requires_environment_revalidation" in text


def test_sprint3_lock_records_resume_revalidation_contract():
    text = LOCK.read_text()

    assert "RESUME_REVALIDATION_SCHEMA_VERSION" in text
    assert "approval_not_valid" in text
    assert "vault_not_ready" in text
    assert "connectors_not_ready" in text
    assert "parent_goal_no_longer_required" in text
    assert "external_state_changed" in text


def test_sprint3_lock_records_safe_stop_semantics():
    text = LOCK.read_text()

    assert "safe_stop_required = true" in text
    assert 'suggested_next_action = "stop_or_replan_before_resume"' in text


def test_sprint3_lock_records_bundle_and_bridge_ownership():
    text = LOCK.read_text()

    assert "GoalEnginePreviewBundle" in text
    assert "single source of truth" in text
    assert "checkpoint_runtime_summary" in text
    assert "resume_revalidation_summary" in text
    assert "MUST NOT rebuild" in text


def test_sprint3_lock_records_boardroom_visibility():
    text = LOCK.read_text()

    assert "Checkpoint / Resume Summary" in text
    assert "Resume Revalidation Summary" in text
    assert "would_resume" in text


def test_sprint3_lock_footer_is_present():
    text = LOCK.read_text()

    assert "Lock ID: AION-GOAL-ENGINE-SPRINT-3-CHECKPOINT-RESUME-LOCK-V1" in text
    assert "Status: LOCKED" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
