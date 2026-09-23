from pathlib import Path


DOC = Path("docs/rfc/aion_phase20f_human_review_decision_envelope_lock.tex")


def test_phase20f_lock_doc_exists():
    assert DOC.exists()


def test_phase20f_lock_doc_contains_core_terms():
    text = DOC.read_text()

    for term in [
        "Phase 20F",
        "Human Review Decision Envelope",
        "approve_preview",
        "reject",
        "request_more_evidence",
        "recommendation card",
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
