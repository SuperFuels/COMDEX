from pathlib import Path


def test_phase22e23_lock_doc_exists_and_names_post_400_recovery():
    path = Path("docs/rfc/aion_phase22e23_full_chess_live_post_400_recovery_kernel_lock.tex")
    assert path.exists()

    text = path.read_text(encoding="utf-8")
    assert "Phase 22E.23" in text
    assert "Live POST 400 Recovery" in text
    assert "stale-state" in text
    assert "HTTP 400" in text
    assert "Stockfish" in text
    assert "LLM" in text
