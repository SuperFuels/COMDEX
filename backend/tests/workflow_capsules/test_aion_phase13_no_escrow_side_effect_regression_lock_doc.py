from pathlib import Path


DOC = Path("docs/rfc/aion_phase13_no_escrow_side_effect_regression_lock.tex")


def _text() -> str:
    return DOC.read_text(encoding="utf-8")


def test_phase13_no_escrow_doc_exists():
    assert DOC.exists()


def test_phase13_no_escrow_doc_names_phase():
    text = _text()
    assert "Phase 13D --- No-Escrow Side-Effect Regression v0" in text
    assert "no-escrow and no-fund-release regression boundary" in text


def test_phase13_no_escrow_doc_lists_locked_flags():
    text = _text()
    for term in [
        "would\\_create\\_escrow = false",
        "would\\_release\\_funds = false",
        "would\\_move\\_money = false",
        "would\\_create\\_payment = false",
        "would\\_require\\_wallet = false",
        "preview\\_only = true",
        "human\\_review\\_required = true",
    ]:
        assert term in text


def test_phase13_no_escrow_doc_lists_forbidden_couplings():
    text = _text()
    for term in [
        "stripe",
        "revolut",
        "paypal",
        "escrow\\_provider",
        "PaymentIntent",
        "checkout.session",
        "create\\_payment",
        "release\\_payment",
        "release\\_escrow",
        "capture\\_payment",
        "transfer\\_funds",
    ]:
        assert term in text


def test_phase13_no_escrow_doc_states_no_frontend_smoke_test():
    text = _text()
    assert "does not create a new frontend visual surface" in text
    assert "No new manual frontend smoke test is required" in text


def test_phase13_no_escrow_doc_mentions_dna_switch_boundary():
    text = _text()
    assert "backend/modules/dna_chain/dna_switch_index.json" in text
    assert "remain unstaged" in text


def test_phase13_no_escrow_doc_uses_tessaris_footer():
    text = _text()
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
