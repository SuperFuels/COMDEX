from pathlib import Path

DOC = Path("docs/rfc/aion_goal_engine_preview_bundle_attachment_consolidation_lock.tex")


def test_preview_bundle_attachment_consolidation_lock_doc_exists():
    assert DOC.exists()


def test_preview_bundle_attachment_consolidation_lock_names_canonical_carrier():
    text = DOC.read_text()

    assert "GoalEnginePreviewBundle" in text
    assert "build_goal_engine_preview_bundle" in text
    assert "preview_bundle.py" in text


def test_preview_bundle_attachment_consolidation_lock_names_attachment_fields():
    text = DOC.read_text()

    required = [
        "parent_child_aggregation_runtime_summary",
        "goal_decomposition_runtime_summary",
        "memory_runtime_summary",
        "parent_child_aggregation_previews",
        "goal_decomposition_previews",
        "memory_record_previews",
        "memory_policy_previews",
    ]

    for token in required:
        assert token in text


def test_preview_bundle_attachment_consolidation_lock_names_safety_fields():
    text = DOC.read_text()

    required = [
        "dry_run_only = true",
        "would_mutate_parent_goal = false",
        "would_create_child_goals = false",
        "would_write_memory = false",
        "would_grant_permission = false",
    ]

    for token in required:
        assert token in text


def test_preview_bundle_attachment_consolidation_lock_footer():
    text = DOC.read_text()

    assert "Lock ID: AION-GOAL-ENGINE-PREVIEW-BUNDLE-ATTACHMENT-CONSOLIDATION-V1" in text
    assert "Status: LOCKED" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
