from pathlib import Path


def test_phase22e62_lock_doc_exists_and_states_no_live_post():
    p = Path("docs/rfc/aion_phase22e62_live_sender_parallel_beam_router_integration_lock.tex")
    assert p.exists()
    text = p.read_text(encoding="utf-8")
    assert "Phase 22E.62" in text
    assert "22E.61" in text
    assert "dry-run" in text.lower()
    assert "MUST NOT create a live Lichess move" in text
