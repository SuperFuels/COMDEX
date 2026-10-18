from pathlib import Path

DOC = Path("docs/rfc/aion_gateway_fulfilment_job_core_preview_lock.tex")
SUITE = Path("scripts/run_goal_engine_focused_lock_suite.sh")


def _text() -> str:
    return DOC.read_text()


def test_fulfilment_job_preview_lock_doc_exists():
    text = _text()
    assert "AION Gateway FulfilmentJob Core Preview Lock" in text
    assert "AION-GATEWAY-FULFILMENT-JOB-CORE-PREVIEW-v1" in text
    assert "Status: LOCKED" in text


def test_fulfilment_job_preview_lock_doc_names_implementation_files():
    text = _text()
    assert "backend/modules/aion_gateway/contracts.py" in text
    assert "backend/modules/aion_gateway/inbound_gateway.py" in text
    assert "backend/modules/aion_gateway/fulfilment_job.py" in text
    assert "backend/modules/aion_gateway/safety.py" in text


def test_fulfilment_job_preview_lock_doc_names_core_fields():
    text = _text()
    assert "job\\_preview\\_id" in text
    assert "intent\\_id" in text
    assert "business\\_id" in text
    assert "workflow\\_hint" in text
    assert "suggested\\_goal\\_hint" in text
    assert "requested\\_outcome" in text
    assert "evidence\\_requirements" in text
    assert "risk\\_flags" in text
    assert "safety\\_flags" in text


def test_fulfilment_job_preview_lock_doc_keeps_preview_only_boundary():
    text = _text()
    assert "MUST NOT" in text
    assert "Create a real \\texttt{FulfilmentJob}" in text
    assert "Instantiate database records" in text
    assert "Execute Goal Engine" in text
    assert "Call providers" in text
    assert "Grant permissions" in text


def test_fulfilment_job_preview_lock_doc_locks_false_runtime_flags():
    text = _text()
    assert "would_create_fulfilment_job = false" in text
    assert "would_execute_goal_engine = false" in text
    assert "would_write_externally = false" in text
    assert "would_mutate_business_state = false" in text
    assert "would_grant_permission = false" in text


def test_fulfilment_job_preview_lock_doc_states_gateway_does_not_replace_goal_engine():
    text = _text()
    assert "MUST NOT replace the Goal Engine" in text
    assert "NormalizedInboundIntent" in text
    assert "FulfilmentJobPreview" in text
    assert "Goal Engine later" in text


def test_fulfilment_job_preview_lock_doc_uses_tessaris_footer():
    text = _text()
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text


def test_fulfilment_job_preview_lock_doc_mentions_focused_suite_next_boundary():
    text = _text()
    assert "focused lock suite" in text
    assert "No public API" in text
    assert "website embed" in text
    assert "Boardroom panel" in text
