from pathlib import Path


DOC = Path("docs/rfc/aion_goal_engine_sprint2_outcome_evidence_lock.tex")


def test_sprint2_outcome_evidence_lock_doc_exists():
    assert DOC.exists()


def test_sprint2_outcome_evidence_lock_records_core_principle():
    text = DOC.read_text()

    assert "Completed workflow execution is not treated as business success" in text
    assert "Evidence existence alone is insufficient" in text
    assert "typed, sourced, verified, confidence-scored" in text


def test_sprint2_outcome_evidence_lock_records_canonical_runtime_summary():
    text = DOC.read_text()

    assert "goal_runtime_summary.outcome_evidence_summary.validations" in text
    assert "validator rows are preserved" in text


def test_sprint2_outcome_evidence_lock_records_bridge_mirror_rule():
    text = DOC.read_text()

    assert "The Workflow Capsule dry-run bridge mirrors the canonical bundle only" in text
    assert "MUST NOT rebuild" in text


def test_sprint2_outcome_evidence_lock_records_boardroom_visibility():
    text = DOC.read_text()

    assert "evidence freshness" in text
    assert "evidence provenance" in text
    assert "source connector" in text
    assert "verified state" in text


def test_sprint2_outcome_evidence_lock_footer():
    text = DOC.read_text()

    assert "Lock ID: AION-GOAL-ENGINE-SPRINT-2-OUTCOME-EVIDENCE-LOCK-V1" in text
    assert "Status: LOCKED" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
