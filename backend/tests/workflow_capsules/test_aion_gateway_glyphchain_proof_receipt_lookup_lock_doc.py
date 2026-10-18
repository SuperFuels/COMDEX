from pathlib import Path

DOC = Path("docs/rfc/aion_gateway_glyphchain_proof_receipt_lookup_lock.tex")


def _text() -> str:
    return DOC.read_text()


def test_proof_receipt_lookup_lock_doc_exists():
    assert DOC.exists()
    assert "AION Gateway GlyphChain Proof Receipt Lookup v0.1 Lock" in _text()


def test_proof_receipt_lookup_lock_doc_lists_functions():
    text = _text()
    for term in [
        "build_aion_proof_commit_receipt",
        "internal_commit_aion_proof_and_build_receipt",
        "internal_lookup_aion_proof_receipt",
        "internal_verify_aion_proof_receipt",
    ]:
        assert term in text


def test_proof_receipt_lookup_lock_doc_lists_receipt_fields():
    text = _text()
    for term in [
        "receipt\\_version",
        "proof\\_commitment\\_id",
        "proof\\_commitment\\_hash",
        "proof\\_type",
        "business\\_id",
        "job\\_id",
        "verified",
        "receipt\\_status",
        "created\\_at\\_ms",
    ]:
        assert term in text


def test_proof_receipt_lookup_lock_doc_states_lookup_and_verify_behaviour():
    text = _text()
    assert "status = found" in text
    assert "status = not_found" in text
    assert "status = verified" in text
    assert "status = failed" in text


def test_proof_receipt_lookup_lock_doc_states_no_public_route_or_tx():
    text = _text()
    assert "public\\_route\\_exposed = false" in text
    assert "block\\_height = None" in text
    assert "tx\\_id = None" in text
    assert "tx\\_hash = None" in text


def test_proof_receipt_lookup_lock_doc_states_no_payment_wallet_token():
    text = _text()
    assert "move PHO" in text
    assert "require PHO" in text
    assert "require a token" in text
    assert "require a wallet" in text
    assert "create payment" in text
    assert "create escrow" in text


def test_proof_receipt_lookup_lock_doc_uses_tessaris_footer():
    text = _text()
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
