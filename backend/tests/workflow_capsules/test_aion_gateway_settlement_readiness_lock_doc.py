from pathlib import Path

DOC = Path("docs/rfc/aion_gateway_settlement_readiness_lock.tex")


def _text() -> str:
    return DOC.read_text()


def test_settlement_readiness_lock_doc_exists():
    assert DOC.exists()
    assert "AION Gateway Settlement Readiness v0.1 Lock" in _text()


def test_settlement_readiness_lock_doc_lists_core_fields():
    text = _text()
    for term in [
        "payment\\_requested",
        "deposit\\_paid",
        "payment\\_ready",
        "disputed",
        "refund\\_recommended",
        "fiat\\_payment\\_reference\\_hash",
        "settlement\\_readiness\\_hash",
    ]:
        assert term in text


def test_settlement_readiness_lock_doc_states_fiat_first_boundary():
    text = _text()
    assert "fiat-first" in text
    assert "MUST NOT require PHO, token, wallet, blockchain settlement, or escrow" in text
    assert "GlyphChain remains a proof/documentation rail, not a payment rail" in text


def test_settlement_readiness_lock_doc_states_hashing_rules():
    text = _text()
    assert "json.dumps" in text
    assert "sort_keys=True" in text
    assert "hashlib.sha256" in text
    assert "Changing the fiat payment reference MUST change" in text


def test_settlement_readiness_lock_doc_keeps_safety_boundary():
    text = _text()
    assert "would_move_money = false" in text
    assert "would_create_payment = false" in text
    assert "would_create_escrow = false" in text
    assert "would_commit_glyphchain = false" in text


def test_settlement_readiness_lock_doc_uses_tessaris_footer():
    text = _text()
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
