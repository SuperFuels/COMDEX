from pathlib import Path


def test_phase22e20_lock_doc_exists_and_names_queen_endgame_patch():
    path = Path("docs/rfc/aion_phase22e20_full_chess_queen_endgame_mate_conversion_kernel_lock.tex")
    assert path.exists()

    text = path.read_text(encoding="utf-8")
    assert "Phase 22E.20" in text
    assert "Queen Endgame Mate Conversion Kernel" in text
    assert "queen endgame" in text
    assert "repetition" in text
    assert "clock pressure" in text
    assert "Stockfish" in text
    assert "LLM" in text
