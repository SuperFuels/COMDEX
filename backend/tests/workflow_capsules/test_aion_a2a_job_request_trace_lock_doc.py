from pathlib import Path

DOC = Path("docs/rfc/aion_a2a_job_request_trace_lock.tex")


def _text() -> str:
    assert DOC.exists(), "Phase 11D lock doc must exist"
    return DOC.read_text()


def test_a2a_job_trace_doc_exists_and_identifies_lock():
    text = _text()
    assert "\\section{Phase 11D --- A2A Job Request and Trace Preview v0}" in text
    assert "AION-A2A-JOB-REQUEST-TRACE-v0.1" in text


def test_a2a_job_trace_doc_lists_module_and_exports():
    text = _text()
    assert "backend/modules/aion_gateway/a2a_job_trace.py" in text
    for term in [
        "A2A\\_JOB\\_TRACE\\_VERSION",
        "validate\\_a2a\\_job\\_request\\_preview",
        "build\\_a2a\\_job\\_request\\_preview",
        "build\\_a2a\\_job\\_trace\\_preview",
        "build\\_a2a\\_job\\_request\\_trace\\_bundle",
    ]:
        assert term in text


def test_a2a_job_trace_doc_lists_universal_boundary():
    text = _text()
    assert "universal Gateway infrastructure" in text
    assert "Home Fixed" in text
    assert "legal" in text
    assert "ecommerce" in text
    assert "vertical adapters" in text


def test_a2a_job_trace_doc_lists_required_fields_and_routes():
    text = _text()
    assert "POST /api/aion/a2a/{business_id}/job_request_preview" in text
    assert "GET /api/aion/a2a/{business_id}/job_trace" in text
    for term in [
        "business\\_id",
        "vertical\\_key",
        "requested\\_outcome",
    ]:
        assert term in text


def test_a2a_job_trace_doc_lists_non_live_boundary():
    text = _text()
    for term in [
        "final_job_created = false",
        "workflow_run_created = false",
        "booking_created = false",
        "human_review_required = true",
        "next_step = future_guarded_approval_path",
        "current_stage = waiting_human_review",
        "live_status_polling_enabled = false",
    ]:
        assert term in text


def test_a2a_job_trace_doc_lists_hashes():
    text = _text()
    assert "job_request_hash" in text
    assert "trace_hash" in text
    assert "bundle_hash" in text


def test_a2a_job_trace_doc_states_safety():
    text = _text()
    for term in [
        "expose a public route",
        "create a booking",
        "create a live job",
        "execute the Goal Engine",
        "bypass human review",
        "move money",
        "move PHO",
        "require a wallet",
        "create a payment",
        "create escrow",
        "send external messages",
        "enable live status polling",
    ]:
        assert term in text


def test_a2a_job_trace_doc_uses_tessaris_footer():
    text = _text()
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
