from pathlib import Path

DOC = Path("docs/rfc/aion_a2a_proof_receipt_lock.tex")


def _text() -> str:
    assert DOC.exists(), "docs/rfc/aion_a2a_proof_receipt_lock.tex must exist"
    return DOC.read_text()


def test_a2a_proof_receipt_doc_exists_and_has_lock_id():
    text = _text()
    assert "\\section{Phase 11F --- A2A Proof Commitment and Proof Receipt Preview v0}" in text
    assert "AION-A2A-PROOF-COMMITMENT-PROOF-RECEIPT-v0.1" in text


def test_a2a_proof_receipt_doc_lists_module_and_exports():
    text = _text()
    for term in [
        "backend/modules/aion_gateway/a2a_proof_receipt.py",
        "A2A\\_PROOF\\_RECEIPT\\_VERSION",
        "build\\_a2a\\_proof\\_commitment\\_preview",
        "build\\_a2a\\_proof\\_receipt\\_preview",
        "build\\_a2a\\_proof\\_bundle\\_preview",
        "build\\_a2a\\_proof\\_bundle\\_summary",
    ]:
        assert term in text


def test_a2a_proof_receipt_doc_lists_endpoint_alignment():
    text = _text()
    assert "GET proof\\_commitment" in text
    assert "GET proof\\_receipt" in text
    assert "/api/aion/a2a/*" in text


def test_a2a_proof_receipt_doc_lists_business_context():
    text = _text()
    assert "business_id = home_fixed" in text
    assert "business_name = Home Fixed" in text
    assert "vertical_key = home_repair" in text
    assert "industry_key = trades" in text
    assert "MUST NOT become hardcoded to trades only" in text


def test_a2a_proof_receipt_doc_lists_commitment_boundary():
    text = _text()
    for term in [
        "status = proof_commitment_preview_only",
        "endpoint_key = proof_commitment",
        "proof_commitment_created = false",
        "proof_commitment_status = preview_not_committed",
        "glyphchain_commit_enabled = false",
        "glyphchain_commit_executed = false",
        "glyphchain_is_payment_rail = false",
        "proof_only_not_payment = true",
        "human_review_required = true",
        "next_step = future_guarded_approval_path",
    ]:
        assert term in text


def test_a2a_proof_receipt_doc_lists_receipt_boundary():
    text = _text()
    for term in [
        "status = proof_receipt_preview_only",
        "endpoint_key = proof_receipt",
        "proof_receipt_created = false",
        "proof_receipt_status = preview_not_issued",
        "proof_verified = false",
        "verification_status = not_verified_preview_only",
        "glyphchain_receipt_lookup_enabled = false",
        "glyphchain_receipt_lookup_executed = false",
    ]:
        assert term in text


def test_a2a_proof_receipt_doc_lists_hashes():
    text = _text()
    assert "proof_commitment_hash" in text
    assert "proof_receipt_hash" in text
    assert "bundle_hash" in text
    assert "summary_hash" in text


def test_a2a_proof_receipt_doc_states_glyphchain_boundary():
    text = _text()
    assert "GlyphChain remains a proof and receipt rail only" in text
    assert "glyphchain_is_payment_rail = false" in text
    assert "proof_only_not_payment = true" in text


def test_a2a_proof_receipt_doc_states_safety():
    text = _text()
    for term in [
        "expose a public route",
        "create a booking",
        "create a live job",
        "execute the Goal Engine",
        "bypass human review",
        "confirm final completion",
        "execute a GlyphChain commit",
        "issue a live proof receipt",
        "verify a live proof receipt",
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


def test_a2a_proof_receipt_doc_uses_tessaris_footer():
    text = _text()
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
