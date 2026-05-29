from pathlib import Path


DOC = Path("docs/rfc/aion_phase14_agentmap_synthetic_agent_simulation_lock.tex")


def test_phase14e_doc_exists():
    assert DOC.exists()


def test_phase14e_doc_mentions_required_contract_terms():
    text = DOC.read_text().lower()

    required_terms = [
        "synthetic inbound agent simulation",
        "simulation_hash",
        "summary_hash",
        "agentmap_hash",
        "endpoint_hash",
        "verification_hash",
        "human review",
        "preview-only",
        "read-only",
        "synthetic",
        "no live booking",
        "no payment",
        "no escrow",
        "no dispatch",
        "no external message",
        "no live chain",
    ]

    for term in required_terms:
        assert term in text


def test_phase14e_doc_has_lock_footer():
    text = DOC.read_text().lower()

    assert "lock id:" in text
    assert "status:" in text
    assert "maintainer: tessaris ai" in text
    assert "author: kevin robinson" in text


def test_phase14e_doc_references_tests_and_suite():
    text = DOC.read_text()

    assert (
        "backend/tests/workflow_capsules/"
        "test_aion_phase14_agentmap_synthetic_agent_simulation_lock.py"
    ) in text
    assert "scripts/run_goal_engine_focused_lock_suite.sh" in text
