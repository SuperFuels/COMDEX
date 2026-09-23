from pathlib import Path


DOC = Path("docs/rfc/aion_goal_engine_human_approved_conflict_resolution_end_to_end_lock.tex")


def _text():
    return DOC.read_text()


def test_conflict_resolution_e2e_lock_doc_exists():
    assert DOC.exists()


def test_conflict_resolution_e2e_lock_doc_names_canonical_chain():
    text = _text()

    assert "child_agent_conflict_preview" in text
    assert "human_approved_conflict_resolution_preview" in text
    assert "GoalEnginePreviewBundle" in text
    assert "conflict_resolution_human_review" in text


def test_conflict_resolution_e2e_lock_doc_locks_safety_invariants():
    text = _text()

    assert "would_auto_resolve = false" in text
    assert "would_execute = false" in text
    assert "would_write_external = false" in text
    assert "would_grant_permission = false" in text
    assert "would_mutate_parent_goal = false" in text
    assert "would_mutate_child_goal = false" in text


def test_conflict_resolution_e2e_lock_doc_records_current_green_counts():
    text = _text()

    assert "5 passed" in text
    assert "31 passed" in text
    assert "494 passed" in text


def test_conflict_resolution_e2e_lock_doc_has_lock_footer():
    text = _text()

    assert "Lock ID: AION-GOAL-ENGINE-HUMAN-APPROVED-CONFLICT-RESOLUTION-E2E-v1" in text
    assert "Status: LOCKED" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
