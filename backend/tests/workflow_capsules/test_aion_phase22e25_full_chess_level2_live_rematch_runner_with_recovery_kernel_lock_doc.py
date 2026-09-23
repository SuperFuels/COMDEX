from pathlib import Path


def test_phase22e25_lock_doc_exists_and_names_runner():
    path = Path("docs/rfc/aion_phase22e25_full_chess_level2_live_rematch_runner_with_recovery_kernel_lock.tex")
    assert path.exists()

    text = path.read_text(encoding="utf-8")
    assert "Phase 22E.25" in text
    assert "Full Level-2 Live Rematch Runner With 400 Recovery" in text
    assert "22E.21" in text
    assert "22E.24" in text
    assert "queen override" in text
    assert "POST 400" in text
    assert "Stockfish" in text
    assert "LLM" in text
