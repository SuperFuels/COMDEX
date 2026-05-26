from pathlib import Path

DOC = Path("docs/rfc/aion_gateway_evidence_proof_hash_lock.tex")


def _text():
    return DOC.read_text()


def test_evidence_proof_hash_lock_doc_exists():
    assert DOC.exists()
    assert "AION Gateway Evidence and Job Proof Hash Lock" in _text()


def test_evidence_proof_hash_lock_doc_lists_core_fields():
    text = _text()
    for term in [
        "evidence\\_id",
        "evidence\\_type",
        "source",
        "captured\\_at",
        "provenance",
        "payload\\_ref",
        "confidence",
        "freshness",
        "evidence\\_hash",
        "job\\_proof\\_hash",
    ]:
        assert term in text


def test_evidence_proof_hash_lock_doc_states_hashing_rules():
    text = _text()
    assert "json.dumps" in text
    assert "sort_keys=True" in text
    assert "hashlib.sha256" in text
    assert "stable across dictionary ordering" in text


def test_evidence_proof_hash_lock_doc_states_mutation_rule():
    text = _text()
    assert "Changing evidence" in text
    assert "MUST change the evidence hash" in text
    assert "MUST change the final \\texttt{job\\_proof\\_hash}" in text


def test_evidence_proof_hash_lock_doc_keeps_safety_boundary():
    text = _text()
    assert "MUST NOT" in text
    assert "commit to GlyphChain" in text
    assert "create payments" in text
    assert "grant permissions" in text
    assert "execute workflows" in text
    assert "expose public routes" in text


def test_evidence_proof_hash_lock_doc_uses_tessaris_footer():
    text = _text()
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
