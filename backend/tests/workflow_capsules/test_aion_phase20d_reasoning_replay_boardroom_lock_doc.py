from pathlib import Path

DOC = Path("docs/rfc/aion_phase20d_reasoning_replay_boardroom_lock.tex")


def test_phase20d_lock_doc_exists():
    assert DOC.exists()


def test_phase20d_lock_doc_contains_core_terms():
    text = DOC.read_text()

    for term in [
        "Phase 20D",
        "Reasoning Replay Boardroom Visibility",
        "reasoning packet",
        "memory snapshot",
        "replay trace",
        "evidence",
        "proof",
        "context hashes",
        "private chain-of-thought",
        "preview-only",
        "human review",
        "no booking",
        "no payment",
        "no escrow",
        "no external message",
        "no live chain",
        "Tessaris AI",
        "Kevin Robinson",
    ]:
        assert term in text
