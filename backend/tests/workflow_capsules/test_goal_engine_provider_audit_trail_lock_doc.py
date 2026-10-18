from pathlib import Path

DOC = Path("docs/rfc/aion_goal_engine_provider_audit_trail_lock.tex")


def test_provider_audit_trail_lock_doc_exists():
    assert DOC.exists()


def test_provider_audit_trail_lock_names_canonical_block():
    text = DOC.read_text()

    assert "provider_audit" in text
    for field in [
        "provider",
        "model",
        "capability",
        "ok",
        "error_code",
        "fallback_used",
        "latency_ms",
        "local_only",
        "external_writes",
        "business_state_mutation",
        "capability_manifest_checked",
        "failed_closed",
        "workspace_id",
        "task_id",
    ]:
        assert field in text


def test_provider_audit_trail_lock_names_safety_invariants():
    text = DOC.read_text()

    assert "local_only = true" in text
    assert "external_writes = blocked" in text
    assert "business_state_mutation = blocked" in text
    assert "Business state mutations MUST remain human-review guarded" in text


def test_provider_audit_trail_lock_names_fail_closed_rule():
    text = DOC.read_text()

    assert "Unsupported provider capabilities MUST fail closed" in text
    assert "capability_manifest_checked = true" in text
    assert "fallback_used" in text


def test_provider_audit_trail_lock_has_footer():
    text = DOC.read_text()

    assert "Lock ID: AION-GOAL-ENGINE-PROVIDER-AUDIT-TRAIL-V1" in text
    assert "Status: LOCKED" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
