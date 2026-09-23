from pathlib import Path


DOC = Path("docs/rfc/aion_phase20g_evidence_gap_envelope_lock.tex")


def test_phase20g_lock_doc_exists():
    assert DOC.exists()


def test_phase20g_lock_doc_contains_core_terms():
    text = DOC.read_text()

    for term in [
        "Phase 20G",
        "Evidence Request",
        "Evidence Gap Envelope",
        "request_more_evidence",
        "missing evidence",
        "recommendation card",
        "human review decision envelope",
        "proof hashes",
        "context hashes",
        "preview-only",
        "human review",
        "private chain-of-thought",
        "no booking",
        "no payment",
        "no escrow",
        "no external message",
        "no live chain",
        "Tessaris AI",
        "Kevin Robinson",
    ]:
        assert term in text
