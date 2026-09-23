from pathlib import Path

DOC = Path("docs/rfc/aion_gateway_fulfilment_job_core_lock.tex")


def _text() -> str:
    return DOC.read_text()


def test_fulfilment_job_core_lock_doc_exists():
    assert DOC.exists()


def test_fulfilment_job_core_lock_doc_has_lock_id_and_status():
    text = _text()
    assert "AION-GATEWAY-FULFILMENT-JOB-CORE-v1" in text
    assert "Status: LOCKED" in text


def test_fulfilment_job_core_lock_doc_names_schema_version():
    text = _text()
    assert "aion.fulfilment_job.v0.1" in text


def test_fulfilment_job_core_lock_doc_lists_required_fields():
    text = _text()
    for term in [
        "job\\_id",
        "business\\_id",
        "service\\_type",
        "location",
        "requested\\_outcome",
        "workflow\\_run\\_id",
        "goal\\_id",
        "job\\_timeline",
        "current\\_stage",
        "next\\_expected\\_event",
        "blocked\\_reason",
    ]:
        assert term in text


def test_fulfilment_job_core_lock_doc_lists_lifecycle_states():
    text = _text()
    for state in [
        "requested",
        "quoted",
        "accepted",
        "scheduled",
        "in_progress",
        "completed",
        "disputed",
        "failed",
    ]:
        assert state in text


def test_fulfilment_job_core_lock_doc_preserves_gateway_v0_boundary():
    text = _text()
    assert "Gateway v0 still MUST NOT create real" in text
    assert "would_create_fulfilment_job = false" in text


def test_fulfilment_job_core_lock_doc_mentions_append_only_timeline():
    text = _text()
    assert "append-only" in text
    assert "Timeline events include" in text


def test_fulfilment_job_core_lock_doc_uses_tessaris_footer():
    text = _text()
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
