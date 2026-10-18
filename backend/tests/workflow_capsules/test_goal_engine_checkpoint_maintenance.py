from backend.modules.aion.goal_engine.checkpointing import (
    CHECKPOINT_COMPACTION_SCHEMA_VERSION,
    CHECKPOINT_PRUNE_SCHEMA_VERSION,
    build_checkpoint_compaction_preview,
    build_checkpoint_prune_preview,
)


def test_checkpoint_compaction_preview_keeps_last_n():
    preview = build_checkpoint_compaction_preview(
        [
            {"checkpoint_id": "cp_1"},
            {"checkpoint_id": "cp_2"},
            {"checkpoint_id": "cp_3"},
            {"checkpoint_id": "cp_4"},
        ],
        keep_last=2,
    )

    assert preview["schema_version"] == CHECKPOINT_COMPACTION_SCHEMA_VERSION
    assert preview["trace_type"] == "checkpoint_compaction_preview"
    assert preview["retained_checkpoint_ids"] == ["cp_3", "cp_4"]
    assert preview["compactable_checkpoint_ids"] == ["cp_1", "cp_2"]
    assert preview["would_compact"] is True
    assert preview["would_delete"] is False
    assert preview["dry_run_only"] is True


def test_checkpoint_compaction_preview_never_grants_permission():
    preview = build_checkpoint_compaction_preview([{"checkpoint_id": "cp_1"}])

    assert preview["would_write_external"] is False
    assert preview["would_grant_permission"] is False
    assert "guarded_checkpoint_persistence_required" in preview["blocked_reasons"]


def test_checkpoint_prune_preview_marks_obsolete_statuses_only():
    preview = build_checkpoint_prune_preview(
        [
            {"checkpoint_id": "cp_active", "resume_status": "waiting_revalidation"},
            {"checkpoint_id": "cp_done", "resume_status": "completed"},
            {"checkpoint_id": "cp_failed", "resume_status": "failed"},
        ]
    )

    assert preview["schema_version"] == CHECKPOINT_PRUNE_SCHEMA_VERSION
    assert preview["trace_type"] == "checkpoint_prune_preview"
    assert preview["prune_candidate_checkpoint_ids"] == ["cp_done", "cp_failed"]
    assert preview["retained_checkpoint_ids"] == ["cp_active"]
    assert preview["would_prune"] is True
    assert preview["would_delete"] is False
    assert preview["dry_run_only"] is True


def test_checkpoint_prune_preview_requires_human_review():
    preview = build_checkpoint_prune_preview([{"checkpoint_id": "cp_1", "status": "obsolete"}])

    assert preview["would_write_external"] is False
    assert preview["would_grant_permission"] is False
    assert "human_review_required" in preview["blocked_reasons"]
