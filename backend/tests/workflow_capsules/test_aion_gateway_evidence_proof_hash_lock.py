from backend.modules.aion_gateway.evidence import (
    EVIDENCE_SCHEMA_VERSION,
    JOB_PROOF_SCHEMA_VERSION,
    build_evidence_item,
    build_job_proof_hash,
    hash_evidence_item,
)


def _job():
    return {
        "job_id": "job_001",
        "business_id": "biz_costa_001",
        "service_type": "plumber",
        "location": "Albox",
        "requested_outcome": "Fix leaking pipe",
        "current_stage": "completed",
    }


def test_evidence_item_contains_core_fields():
    item = build_evidence_item(
        evidence_id="ev_001",
        evidence_type="photo",
        source="customer_upload",
        captured_at="2026-05-27T00:00:00+00:00",
        provenance={"uploaded_by": "customer"},
        payload_ref={"uri": "file://before.jpg"},
        confidence=0.91,
        freshness="fresh",
    )

    assert item["schema_version"] == EVIDENCE_SCHEMA_VERSION
    assert item["evidence_id"] == "ev_001"
    assert item["evidence_type"] == "photo"
    assert item["source"] == "customer_upload"
    assert item["confidence"] == 0.91
    assert item["freshness"] == "fresh"
    assert item["evidence_hash"]


def test_evidence_hash_is_stable_for_payload_ordering():
    left = {
        "evidence_id": "ev_001",
        "evidence_type": "message",
        "source": "agent_protocol",
        "captured_at": "2026-05-27T00:00:00+00:00",
        "provenance": {"b": 2, "a": 1},
        "payload_ref": {"z": "last", "a": "first"},
        "confidence": 0.8,
        "freshness": "fresh",
    }
    right = {
        "freshness": "fresh",
        "confidence": 0.8,
        "payload_ref": {"a": "first", "z": "last"},
        "provenance": {"a": 1, "b": 2},
        "captured_at": "2026-05-27T00:00:00+00:00",
        "source": "agent_protocol",
        "evidence_type": "message",
        "evidence_id": "ev_001",
    }

    assert hash_evidence_item(left) == hash_evidence_item(right)


def test_changed_evidence_changes_evidence_hash():
    base = build_evidence_item(
        evidence_id="ev_001",
        evidence_type="photo",
        source="customer_upload",
        captured_at="2026-05-27T00:00:00+00:00",
        payload_ref={"uri": "file://before.jpg"},
        confidence=0.9,
        freshness="fresh",
    )
    changed = dict(base)
    changed["payload_ref"] = {"uri": "file://after.jpg"}

    assert hash_evidence_item(base) != hash_evidence_item(changed)


def test_job_proof_hash_uses_job_evidence_and_timeline():
    ev = build_evidence_item(
        evidence_id="ev_001",
        evidence_type="signature",
        source="customer",
        captured_at="2026-05-27T00:00:00+00:00",
        payload_ref={"signature_ref": "sig_001"},
        confidence=1.0,
        freshness="fresh",
    )

    proof = build_job_proof_hash(
        job=_job(),
        evidence_items=[ev],
        timeline=[{"stage": "completed", "at": "2026-05-27T00:01:00+00:00"}],
    )

    assert proof["schema_version"] == JOB_PROOF_SCHEMA_VERSION
    assert proof["proof_type"] == "job_proof_hash"
    assert proof["job_id"] == "job_001"
    assert proof["evidence_count"] == 1
    assert ev["evidence_hash"] in proof["evidence_hashes"]
    assert proof["job_proof_hash"]


def test_changed_evidence_changes_final_job_proof_hash():
    ev1 = build_evidence_item(
        evidence_id="ev_001",
        evidence_type="photo",
        source="provider_upload",
        captured_at="2026-05-27T00:00:00+00:00",
        payload_ref={"uri": "file://completion-a.jpg"},
        confidence=0.9,
        freshness="fresh",
    )
    ev2 = dict(ev1)
    ev2["payload_ref"] = {"uri": "file://completion-b.jpg"}

    first = build_job_proof_hash(job=_job(), evidence_items=[ev1])
    second = build_job_proof_hash(job=_job(), evidence_items=[ev2])

    assert first["job_proof_hash"] != second["job_proof_hash"]


def test_changed_timeline_changes_final_job_proof_hash():
    ev = build_evidence_item(
        evidence_id="ev_001",
        evidence_type="message",
        source="agent_protocol",
        captured_at="2026-05-27T00:00:00+00:00",
        payload_ref={"message_id": "msg_001"},
    )

    first = build_job_proof_hash(
        job=_job(),
        evidence_items=[ev],
        timeline=[{"stage": "scheduled"}],
    )
    second = build_job_proof_hash(
        job=_job(),
        evidence_items=[ev],
        timeline=[{"stage": "completed"}],
    )

    assert first["job_proof_hash"] != second["job_proof_hash"]


def test_proof_layer_is_not_payment_or_glyphchain_commit():
    proof = build_job_proof_hash(job=_job(), evidence_items=[])

    assert proof["dry_run_only"] is True
    assert proof["would_commit_to_glyphchain"] is False
    assert proof["would_create_payment"] is False
    assert proof["would_grant_permission"] is False
