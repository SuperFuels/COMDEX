from pathlib import Path

DOC = Path("docs/rfc/aion_goal_engine_evidence_source_preview_bundle_lock.tex")
SUITE = Path("scripts/run_goal_engine_focused_lock_suite.sh")


def test_evidence_source_preview_bundle_lock_doc_exists():
    assert DOC.exists()


def test_evidence_source_preview_bundle_lock_names_canonical_fields():
    text = DOC.read_text()

    for token in [
        "evidence_source_runtime_summary",
        "evidence_source_previews",
        "evidence_pointer_previews",
        "goal_engine_evidence_source_runtime_summary",
        "goal_engine_evidence_pointer_previews",
    ]:
        assert token in text


def test_evidence_source_preview_bundle_lock_names_supported_types():
    text = DOC.read_text()

    for token in [
        "gmail\\_reply",
        "crm\\_lead",
        "utm\\_click",
        "booking",
        "payment",
        "file",
        "screenshot",
    ]:
        assert token in text


def test_evidence_source_preview_bundle_lock_records_safety_invariants():
    text = DOC.read_text()

    for token in [
        "dry_run_only = true",
        "would_read_external = false",
        "would_write_external = false",
        "would_grant_permission = false",
        "visibility-only",
    ]:
        assert token in text


def test_evidence_source_preview_bundle_lock_has_footer():
    text = DOC.read_text()

    assert "Lock ID: AION-GOAL-ENGINE-EVIDENCE-SOURCE-PREVIEW-BUNDLE-LOCK-V1" in text
    assert "Status: LOCKED" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text


def test_focused_suite_includes_evidence_source_lock_doc():
    text = SUITE.read_text()
    assert "test_goal_engine_evidence_source_preview_bundle_lock_doc.py" in text
