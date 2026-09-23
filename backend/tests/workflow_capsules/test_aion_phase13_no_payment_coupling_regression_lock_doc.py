from pathlib import Path


DOC = Path("docs/rfc/aion_phase13_no_payment_coupling_regression_lock.tex")


def _text() -> str:
    return DOC.read_text(encoding="utf-8")


def test_phase13_no_payment_doc_exists():
    assert DOC.exists()


def test_phase13_no_payment_doc_names_phase():
    text = _text()
    assert "Phase 13B" in text
    assert "No-Payment Coupling Regression v0" in text


def test_phase13_no_payment_doc_states_boundary():
    text = _text()
    for term in [
        "move money",
        "move PHO",
        "require a wallet",
        "create a payment",
        "create escrow",
        "release funds",
    ]:
        assert term in text


def test_phase13_no_payment_doc_states_glyphchain_boundary():
    text = _text()
    assert "GlyphChain remains a proof and receipt rail only" in text
    assert "glyphchain_is_payment_rail = false" in text
    assert "proof_only_not_payment = true" in text
    assert "settlement_mode = fiat_first" in text


def test_phase13_no_payment_doc_says_no_frontend_smoke_test():
    text = _text()
    assert "does not create a new frontend visual surface" in text
    assert "No new manual frontend smoke test is required" in text


def test_phase13_no_payment_doc_mentions_dna_hygiene():
    text = _text()
    assert "backend/modules/dna_chain/dna_switch_index.json" in text
    assert "remains outside this phase unless intentionally changed" in text


def test_phase13_no_payment_doc_uses_tessaris_footer():
    text = _text()
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
