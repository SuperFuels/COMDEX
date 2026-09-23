from pathlib import Path


DOC = Path("docs/rfc/aion_phase14_agentmap_human_review_simulation_bridge_lock.tex")


def _doc_text() -> str:
    assert DOC.exists()
    return DOC.read_text().lower()


def test_phase14f_doc_exists():
    assert DOC.exists()


def test_phase14f_doc_mentions_required_contract_terms():
    text = _doc_text()

    for term in [
        "human review",
        "synthetic",
        "bridge_hash",
        "simulation_hash",
        "verification_hash",
        "agentmap_hash",
        "waiting_human_review",
        "preview-only",
        "no booking",
        "no payment",
        "no escrow",
        "no dispatch",
        "no external message",
        "no live chain",
    ]:
        assert term in text


def test_phase14f_doc_has_lock_footer():
    text = _doc_text()

    assert "lock id:" in text
    assert "status:" in text
    assert "maintainer:" in text
    assert "author:" in text
    assert "tessaris ai" in text
    assert "kevin robinson" in text


def test_phase14f_doc_mentions_tests():
    text = _doc_text()

    assert "test_aion_phase14_agentmap_human_review_simulation_bridge_lock.py" in text
    assert "test_aion_phase14_agentmap_human_review_simulation_bridge_lock_doc.py" in text
