from pathlib import Path


DOC = Path("docs/rfc/aion_phase20c_reasoning_replay_trace_lock.tex")


def test_phase20c_lock_doc_exists():
    assert DOC.exists()


def test_phase20c_lock_doc_contains_core_terms():
    text = DOC.read_text()

    required_terms = [
        "AION Reasoning Replay Trace",
        "governed reasoning packet",
        "reasoning memory snapshot",
        "evidence_context",
        "proof_context",
        "agentmap_hash",
        "proof_hash",
        "replay_trace_hash",
        "summary_hash",
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
    ]

    for term in required_terms:
        assert term in text
