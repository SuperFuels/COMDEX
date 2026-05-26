from pathlib import Path

DOC = Path("docs/rfc/aion_gateway_glyphchain_proof_commit_lock.tex")


def _text() -> str:
    return DOC.read_text()


def test_glyphchain_proof_commit_lock_doc_exists():
    assert DOC.exists()
    assert "AION Gateway GlyphChain Proof Commit Adapter v0.1 Lock" in _text()


def test_glyphchain_proof_commit_lock_doc_lists_proof_types():
    text = _text()
    for term in [
        "AION\\_JOB\\_PROOF\\_V1",
        "AION\\_EVIDENCE\\_PROOF\\_V1",
        "AION\\_SETTLEMENT\\_READINESS\\_PROOF\\_V1",
    ]:
        assert term in text


def test_glyphchain_proof_commit_lock_doc_mentions_chainsim_canonical_codec():
    text = _text()
    assert "backend.modules.chain_sim.canonical_codec.canonical_hash_hex" in text
    assert "created\\_at\\_ms" in text
    assert "MUST NOT use floating-point timestamps" in text


def test_glyphchain_proof_commit_lock_doc_states_dry_run_safety():
    text = _text()
    for term in [
        "would\\_submit\\_chain\\_tx = false",
        "would\\_move\\_money = false",
        "would\\_require\\_pho = false",
        "would\\_require\\_token = false",
        "would\\_require\\_wallet = false",
        "would\\_create\\_payment = false",
        "would\\_create\\_escrow = false",
    ]:
        assert term in text


def test_glyphchain_proof_commit_lock_doc_states_no_live_chain_submit():
    text = _text()
    assert "MUST NOT" in text
    assert "submit a live ChainSim transaction" in text
    assert "mutate chain state" in text
    assert "move PHO" in text
    assert "expose a public route" in text


def test_glyphchain_proof_commit_lock_doc_mentions_verification():
    text = _text()
    assert "proof\\_payload\\_hash" in text
    assert "proof\\_commitment\\_hash" in text
    assert "Verification passes only when" in text


def test_glyphchain_proof_commit_lock_doc_uses_tessaris_footer():
    text = _text()
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
