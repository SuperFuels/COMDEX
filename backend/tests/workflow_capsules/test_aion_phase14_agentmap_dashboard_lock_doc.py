from pathlib import Path

DOC = Path("docs/rfc/aion_phase14_agentmap_dashboard_lock.tex")


def test_phase14g_doc_exists():
    assert DOC.exists()


def test_phase14g_doc_mentions_required_contract_terms():
    text = DOC.read_text().lower()

    required = [
        "agentmap dashboard",
        "generate agentmap",
        "machine discovery",
        "agentmap_hash",
        "dashboard_hash",
        "summary_hash",
        "copy agentmap url",
        "download agentmap.json",
        "copy website install tag",
        "regenerate agentmap",
        "preview-only",
        "read-only",
        "human review",
        "no booking",
        "no payment",
        "no escrow",
        "no dispatch",
        "no external message",
        "no live chain",
    ]

    for term in required:
        assert term in text


def test_phase14g_doc_has_lock_footer():
    text = DOC.read_text().lower()

    assert "lock id:" in text
    assert "status:" in text
    assert "maintainer: tessaris ai" in text
    assert "author: kevin robinson" in text


def test_phase14g_doc_mentions_focused_suite():
    text = DOC.read_text()

    assert "test_aion_phase14_agentmap_dashboard_lock.py" in text
    assert "test_aion_phase14_agentmap_dashboard_lock_doc.py" in text
