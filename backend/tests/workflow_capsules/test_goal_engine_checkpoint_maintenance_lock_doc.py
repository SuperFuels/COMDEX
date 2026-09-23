from pathlib import Path

DOC = Path("docs/rfc/aion_goal_engine_checkpoint_maintenance_lock.tex")


def test_checkpoint_maintenance_lock_doc_exists():
    assert DOC.exists()


def test_checkpoint_maintenance_lock_names_trace_blocks():
    text = DOC.read_text()
    assert "checkpoint_compaction_preview" in text
    assert "checkpoint_prune_preview" in text


def test_checkpoint_maintenance_lock_names_safety_invariants():
    text = DOC.read_text()
    for token in [
        "dry_run_only = true",
        "would_delete = false",
        "would_write_external = false",
        "would_grant_permission = false",
        "human_review_required",
        "guarded_checkpoint_persistence_required",
    ]:
        assert token in text


def test_checkpoint_maintenance_lock_has_footer():
    text = DOC.read_text()
    assert "Lock ID: AION-GOAL-ENGINE-CHECKPOINT-MAINTENANCE-V1" in text
    assert "Status: LOCKED" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
