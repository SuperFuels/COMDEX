from pathlib import Path


DOC = Path("docs/rfc/aion_phase13_public_gateway_regression_lock.tex")


def _text() -> str:
    return DOC.read_text(encoding="utf-8")


def test_phase13_public_gateway_regression_doc_exists():
    assert DOC.exists()


def test_phase13_public_gateway_regression_doc_names_phase():
    text = _text()
    assert "Phase 13A" in text
    assert "Public Gateway Regression and Lock Integrity v0" in text


def test_phase13_public_gateway_regression_doc_lists_phase12_chain():
    text = _text()
    for term in [
        "Phase 12A",
        "Phase 12B",
        "Phase 12C",
        "Phase 12D",
        "Phase 12E",
        "Phase 12F",
    ]:
        assert term in text


def test_phase13_public_gateway_regression_doc_states_safety():
    text = _text()
    for term in [
        "create a booking",
        "create a live job",
        "execute the Goal Engine",
        "bypass human review",
        "move money",
        "move PHO",
        "require a wallet",
        "create a payment",
        "create escrow",
        "release funds",
        "send external messages",
        "expose an unauthenticated public write route",
    ]:
        assert term in text


def test_phase13_public_gateway_regression_doc_says_no_frontend_smoke_test():
    text = _text()
    assert "does not create a new frontend visual surface" in text
    assert "No new manual frontend smoke test is required" in text


def test_phase13_public_gateway_regression_doc_mentions_dna_hygiene():
    text = _text()
    assert "backend/modules/dna_chain/dna_switch_index.json" in text
    assert "must remain outside this phase unless intentionally changed" in text


def test_phase13_public_gateway_regression_doc_uses_tessaris_footer():
    text = _text()
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
