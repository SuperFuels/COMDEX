from __future__ import annotations

from pathlib import Path

DOC = Path("docs/rfc/aion_home_fixed_vertical_testbed_lock.tex")


def _text() -> str:
    return DOC.read_text()


def test_home_fixed_vertical_lock_doc_exists():
    assert DOC.exists()
    assert "Phase 8 --- Home Fixed Vertical Testbed v0" in _text()


def test_home_fixed_vertical_lock_doc_names_home_fixed_not_costaconnect():
    text = _text()
    assert "Home Fixed" in text
    assert "not CostaConnect or CostaConexion" in text


def test_home_fixed_vertical_lock_doc_lists_full_flow():
    text = _text()
    for term in [
        "Parallel business profile",
        "Machine-readable service catalog",
        "Customer repair request intake",
        "Machine cart request",
        "Quote preview",
        "Fulfilment job preview",
        "Provider assignment preview",
        "Job timeline preview",
        "Evidence upload",
        "Settlement readiness preview",
        "Job proof hash",
        "GlyphChain proof receipt preview",
        "Machine trace preview",
    ]:
        assert term in text


def test_home_fixed_vertical_lock_doc_states_fiat_first_boundary():
    text = _text()
    assert "fiat-first" in text
    assert "would\\_move\\_money = false" in text
    assert "would\\_require\\_wallet = false" in text


def test_home_fixed_vertical_lock_doc_states_no_live_side_effects():
    text = _text()
    for term in [
        "expose a public route",
        "execute the Goal Engine",
        "create a live workflow run",
        "create a booking",
        "notify a provider",
        "send external messages",
        "create a payment",
        "create escrow",
        "move PHO",
    ]:
        assert term in text


def test_home_fixed_vertical_lock_doc_mentions_glyphchain_proof_receipt():
    text = _text()
    assert "GlyphChain Proof Receipt Preview" in text
    assert "job\\_proof\\_hash" in text
    assert "documentation/proof-only" in text


def test_home_fixed_vertical_lock_doc_uses_tessaris_footer():
    text = _text()
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
