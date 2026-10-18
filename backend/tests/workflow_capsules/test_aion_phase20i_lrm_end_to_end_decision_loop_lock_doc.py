from pathlib import Path


DOC = Path("docs/rfc/aion_phase20i_lrm_end_to_end_decision_loop_lock.tex")


def test_phase20i_lock_doc_exists():
    assert DOC.exists()


def test_phase20i_lock_doc_contains_core_terms():
    text = DOC.read_text()

    for term in [
        "Phase 20I",
        "LRM Closeout",
        "End-to-End Decision Loop",
        "governed reasoning packet",
        "reasoning memory snapshot",
        "reasoning replay trace",
        "boardroom visibility",
        "recommendation card",
        "human review decision",
        "evidence gap",
        "evidence satisfaction",
        "return_to_human_review",
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
