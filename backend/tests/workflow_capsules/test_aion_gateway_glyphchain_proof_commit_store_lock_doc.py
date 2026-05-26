from pathlib import Path

DOC = Path("docs/rfc/aion_gateway_glyphchain_proof_commit_store_lock.tex")


def _text() -> str:
    return DOC.read_text()


def test_glyphchain_proof_commit_store_lock_doc_exists():
    assert DOC.exists()
    assert "AION Gateway GlyphChain Proof Commit Store v0.1 Lock" in _text()


def test_glyphchain_proof_commit_store_lock_doc_lists_supported_types():
    text = _text()
    for term in [
        "AION\\_JOB\\_PROOF\\_V1",
        "AION\\_EVIDENCE\\_PROOF\\_V1",
        "AION\\_SETTLEMENT\\_READINESS\\_PROOF\\_V1",
    ]:
        assert term in text


def test_glyphchain_proof_commit_store_lock_doc_lists_record_fields():
    text = _text()
    for term in [
        "proof\\_commitment\\_id",
        "store\\_version",
        "proof\\_type",
        "business\\_id",
        "job\\_id",
        "proof\\_payload\\_hash",
        "proof\\_commitment\\_hash",
        "committed\\_at\\_ms",
        "dry\\_run\\_chain\\_tx",
    ]:
        assert term in text


def test_glyphchain_proof_commit_store_lock_doc_states_idempotency():
    text = _text()
    assert "already_committed" in text
    assert "same \\texttt{proof\\_commitment\\_id}" in text


def test_glyphchain_proof_commit_store_lock_doc_states_no_bank_or_staking_tx():
    text = _text()
    assert "MUST NOT" in text
    assert "BANK\\_*" in text
    assert "staking transaction types" in text
    assert "tx\\_id = None" in text
    assert "tx\\_hash = None" in text
    assert "block\\_height = None" in text


def test_glyphchain_proof_commit_store_lock_doc_states_no_payment_wallet_token():
    text = _text()
    assert "move PHO" in text
    assert "require PHO" in text
    assert "require a token" in text
    assert "require a wallet" in text
    assert "create a payment" in text
    assert "create escrow" in text


def test_glyphchain_proof_commit_store_lock_doc_uses_tessaris_footer():
    text = _text()
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
