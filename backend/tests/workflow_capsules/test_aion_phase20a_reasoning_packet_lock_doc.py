from pathlib import Path

DOC = Path("docs/rfc/aion_phase20a_reasoning_packet_lock.tex")


def test_phase20a_lock_doc_exists():
    assert DOC.exists()


def test_phase20a_lock_doc_contains_core_terms():
    text = DOC.read_text()

    for term in [
        "AION Reasoning Packet",
        "website_intake",
        "commercial_ticket",
        "workflow_context",
        "agentmap_context",
        "boardroom_context",
        "proof_context",
        "ets_context",
        "reasoning_packet_hash",
        "summary_hash",
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
