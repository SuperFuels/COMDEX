from pathlib import Path


DOC = Path("docs/rfc/aion_phase20h_evidence_satisfaction_envelope_lock.tex")


def test_phase20h_lock_doc_exists():
    assert DOC.exists()


def test_phase20h_lock_doc_contains_core_terms():
    text = DOC.read_text()

    for term in [
        "Phase 20H",
        "Evidence Intake",
        "Evidence Satisfaction Envelope",
        "evidence gap",
        "missing evidence",
        "return_to_human_review",
        "recommendation card",
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
