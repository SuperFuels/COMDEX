from pathlib import Path


def test_phase22e24_lock_doc_exists_and_names_live_loop_integration():
    path = Path("docs/rfc/aion_phase22e24_full_chess_level2_live_rematch_recovery_loop_kernel_lock.tex")
    assert path.exists()

    text = path.read_text(encoding="utf-8")
    assert "Phase 22E.24" in text
    assert "POST 400 Recovery Into Live Rematch Loop" in text
    assert "22E.22" in text
    assert "22E.23" in text
    assert "HTTP 400" in text
    assert "stale-state" in text
    assert "Stockfish" in text
    assert "LLM" in text
