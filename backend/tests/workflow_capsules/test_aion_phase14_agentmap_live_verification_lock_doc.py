from pathlib import Path

DOC = Path("docs/rfc/aion_phase14_agentmap_live_verification_lock.tex")


def test_phase14d_doc_exists():
    assert DOC.exists()


def test_phase14d_doc_mentions_required_contract_terms():
    text = DOC.read_text().lower()

    required_terms = [
        "agentmap live verification",
        "verification_hash",
        "agentmap_hash",
        "summary_hash",
        "canonical path",
        "well-known path",
        "preview-only",
        "read-only",
        "human review",
        "no live booking",
        "no payment",
        "no escrow",
        "no dispatch",
        "no external message",
        "no live chain",
    ]

    for term in required_terms:
        assert term in text


def test_phase14d_doc_has_lock_footer():
    text = DOC.read_text().lower()

    assert "lock id:" in text
    assert "status:" in text
    assert "maintainer: tessaris ai" in text
    assert "author: kevin robinson" in text


def test_phase14d_doc_references_validation_commands():
    text = DOC.read_text()

    assert "test_aion_phase14_agentmap_live_verification_lock.py" in text
    assert "test_aion_phase14_agentmap_live_verification_lock_doc.py" in text
