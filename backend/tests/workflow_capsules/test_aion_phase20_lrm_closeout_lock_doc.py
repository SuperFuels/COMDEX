from pathlib import Path


DOC = Path("docs/rfc/aion_phase20_lrm_closeout_lock.tex")
SUITE = Path("scripts/run_aion_lrm_phase20_lock_suite.sh")


def test_phase20_closeout_doc_exists():
    assert DOC.exists()


def test_phase20_closeout_script_exists():
    assert SUITE.exists()


def test_phase20_closeout_doc_contains_core_terms():
    text = DOC.read_text()

    for term in [
        "Phase 20",
        "AION-LRM",
        "Governed Reasoning Packet",
        "Reasoning Memory Snapshot",
        "Reasoning Replay Trace",
        "Boardroom Replay Visibility",
        "Reasoning Recommendation Card",
        "Human Review Decision Envelope",
        "Evidence Gap Envelope",
        "Evidence Satisfaction Envelope",
        "End-to-End Decision Loop",
        "preview-only",
        "human review",
        "private chain-of-thought",
        "no booking",
        "no payment",
        "no escrow",
        "no external messages",
        "no live chain",
        "Tessaris AI",
        "Kevin Robinson",
    ]:
        assert term in text


def test_phase20_closeout_script_runs_phase20_tests_only():
    text = SUITE.read_text()

    assert "test_aion_phase20a" in text
    assert "test_aion_phase20b" in text
    assert "test_aion_phase20c" in text
    assert "test_aion_phase20d" in text
    assert "test_aion_phase20e" in text
    assert "test_aion_phase20f" in text
    assert "test_aion_phase20g" in text
    assert "test_aion_phase20h" in text
    assert "test_aion_phase20i" in text
    assert "compileall backend/modules/aion_lrm" in text
    assert "run_goal_engine_focused_lock_suite" not in text
