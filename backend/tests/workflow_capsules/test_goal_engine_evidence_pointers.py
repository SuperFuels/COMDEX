from backend.modules.aion.goal_engine.evidence_sources import (
    EVIDENCE_POINTER_SCHEMA_VERSION,
    build_evidence_pointer_preview,
    stable_evidence_hash,
)


def test_evidence_pointer_preview_builds_hash_and_reference():
    preview = build_evidence_pointer_preview(
        evidence_type="utm_click",
        reference_pointer="utm://campaign/costa-connect/ad-1",
        source="analytics",
        payload={"clicks": 12, "campaign": "spring"},
        confidence=0.8,
    )

    assert preview["schema_version"] == EVIDENCE_POINTER_SCHEMA_VERSION
    assert preview["trace_type"] == "evidence_pointer_preview"
    assert preview["reference_pointer"] == "utm://campaign/costa-connect/ad-1"
    assert len(preview["evidence_hash"]) == 64
    assert preview["valid"] is True
    assert preview["dry_run_only"] is True


def test_evidence_hash_is_order_independent():
    left = {"b": 2, "a": {"z": 1, "y": 0}}
    right = {"a": {"y": 0, "z": 1}, "b": 2}

    assert stable_evidence_hash(left) == stable_evidence_hash(right)


def test_evidence_pointer_rejects_missing_reference():
    preview = build_evidence_pointer_preview(
        evidence_type="gmail_reply",
        reference_pointer="",
        source="gmail",
    )

    assert preview["valid"] is False
    assert "reference_pointer_required" in preview["blocked_reasons"]


def test_evidence_pointer_rejects_unknown_type():
    preview = build_evidence_pointer_preview(
        evidence_type="unknown_source",
        reference_pointer="x://1",
        source="unknown",
    )

    assert preview["valid"] is False
    assert "unsupported_evidence_pointer_type" in preview["blocked_reasons"]


def test_evidence_pointer_never_reads_or_writes_external_systems():
    preview = build_evidence_pointer_preview(
        evidence_type="payment",
        reference_pointer="payment://stripe/pi_123",
        source="stripe",
    )

    assert preview["would_read_external"] is False
    assert preview["would_write_external"] is False
    assert preview["would_grant_permission"] is False
    assert preview["resolved"] is False
