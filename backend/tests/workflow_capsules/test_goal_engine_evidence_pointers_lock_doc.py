from pathlib import Path

DOC = Path("docs/rfc/aion_goal_engine_evidence_pointers_lock.tex")


def test_evidence_pointer_lock_doc_exists():
    assert DOC.exists()


def test_evidence_pointer_lock_names_canonical_block():
    text = DOC.read_text()
    assert "evidence_pointer_preview" in text
    assert "aion.goal_engine.evidence_pointer.v1" in text
    assert "reference_pointer" in text
    assert "evidence_hash" in text


def test_evidence_pointer_lock_names_supported_sources():
    text = DOC.read_text()
    for token in [
        "gmail_reply",
        "crm_lead",
        "utm_click",
        "booking",
        "payment",
        "revenue",
        "screenshot",
        "file",
        "manual",
    ]:
        assert token in text


def test_evidence_pointer_lock_names_safety_invariants():
    text = DOC.read_text()
    for token in [
        "dry_run_only = true",
        "resolved = false",
        "would_read_external = false",
        "would_write_external = false",
        "would_grant_permission = false",
    ]:
        assert token in text


def test_evidence_pointer_lock_has_footer():
    text = DOC.read_text()
    assert "Lock ID: AION-GOAL-ENGINE-EVIDENCE-POINTERS-V1" in text
    assert "Status: LOCKED" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
