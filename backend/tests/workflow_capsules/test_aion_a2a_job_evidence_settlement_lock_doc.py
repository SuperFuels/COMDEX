from pathlib import Path

DOC = Path("docs/rfc/aion_a2a_job_evidence_settlement_lock.tex")


def _text() -> str:
    assert DOC.exists(), "Phase 11E lock doc must exist"
    return DOC.read_text()


def test_a2a_job_evidence_settlement_doc_exists_and_identifies_lock():
    text = _text()
    assert "\\section{Phase 11E --- A2A Job Evidence and Settlement Readiness Preview v0}" in text
    assert "AION-A2A-JOB-EVIDENCE-SETTLEMENT-v0.1" in text


def test_a2a_job_evidence_settlement_doc_lists_module_and_exports():
    text = _text()
    assert "backend/modules/aion_gateway/a2a_job_evidence_settlement.py" in text
    for term in [
        "A2A\\_JOB\\_EVIDENCE\\_SETTLEMENT\\_VERSION",
        "build\\_a2a\\_job\\_evidence\\_preview",
        "build\\_a2a\\_settlement\\_readiness\\_preview",
        "build\\_a2a\\_job\\_evidence\\_settlement\\_bundle",
    ]:
        assert term in text


def test_a2a_job_evidence_settlement_doc_lists_universal_boundary():
    text = _text()
    assert "universal Gateway infrastructure" in text
    assert "Home Fixed" in text
    assert "legal" in text
    assert "ecommerce" in text
    assert "vertical adapters" in text


def test_a2a_job_evidence_settlement_doc_lists_routes():
    text = _text()
    assert "GET /api/aion/a2a/{business_id}/job_evidence" in text
    assert "GET /api/aion/a2a/{business_id}/settlement_readiness" in text


def test_a2a_job_evidence_settlement_doc_lists_evidence_fields():
    text = _text()
    for term in [
        "required evidence",
        "submitted evidence",
        "missing evidence",
        "evidence-backed completion state",
        "proof commit readiness",
        "human_review_required = true",
        "evidence_review_status = requires_human_review",
        "final_completion_confirmed = false",
    ]:
        assert term in text


def test_a2a_job_evidence_settlement_doc_lists_settlement_boundary():
    text = _text()
    for term in [
        "settlement_status = not_ready_human_review_required",
        "settlement_ready = false",
        "payment_ready = false",
        "escrow_ready = false",
        "fiat_first = true",
        "glyphchain_is_payment_rail = false",
        "proof_required_before_settlement = true",
        "would_move_money = false",
        "would_create_payment = false",
        "would_create_escrow = false",
        "would_release_funds = false",
        "next_step = future_guarded_approval_path",
    ]:
        assert term in text


def test_a2a_job_evidence_settlement_doc_lists_hashes():
    text = _text()
    assert "evidence_hash" in text
    assert "settlement_readiness_hash" in text
    assert "bundle_hash" in text


def test_a2a_job_evidence_settlement_doc_states_safety():
    text = _text()
    for term in [
        "expose a public route",
        "create a booking",
        "create a live job",
        "execute the Goal Engine",
        "bypass human review",
        "confirm final completion",
        "move money",
        "move PHO",
        "require a wallet",
        "create a payment",
        "create escrow",
        "release funds",
        "send external messages",
        "enable live status polling",
    ]:
        assert term in text


def test_a2a_job_evidence_settlement_doc_uses_tessaris_footer():
    text = _text()
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
