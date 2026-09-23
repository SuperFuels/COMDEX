from pathlib import Path


def test_phase22e33_lock_doc_exists_and_names_repetition_breaker():
    path = Path("docs/rfc/aion_phase22e33_full_chess_rook_bishop_repetition_breaker_kernel_lock.tex")
    assert path.exists()

    text = path.read_text(encoding="utf-8")
    assert "Phase 22E.33" in text
    assert "Rook/Bishop Repetition Breaker" in text
    assert "repeated destination" in text
    assert "irreversible progress" in text
    assert "Stockfish" in text
    assert "LLM" in text
