from pathlib import Path


def test_phase22e59_doc_lock_exists_and_names_integration():
    doc = Path("docs/rfc/aion_phase22e59_live_sender_rolling_plan_integration_lock.tex")
    assert doc.exists()
    text = doc.read_text(encoding="utf-8")

    assert "Phase 22E.59" in text
    assert "Rolling Plan Live Sender Integration" in text
    assert "22E.58" in text
    assert "before Monte Carlo" in text
    assert "Lock ID: AION-PHASE22E59-LIVE-SENDER-ROLLING-PLAN-INTEGRATION" in text
