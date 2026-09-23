from pathlib import Path


def test_phase22e48_lock_doc_exists_and_names_promotion_safety():
    path = Path("docs/rfc/aion_phase22e48_full_chess_promotion_safety_queen_survival_guard_kernel_lock.tex")
    assert path.exists()

    text = path.read_text(encoding="utf-8")
    assert "Phase 22E.48" in text
    assert "Promotion Safety" in text
    assert "Queen Survival" in text
    assert "g7g8q" in text
    assert "Stockfish" in text
    assert "LLM" in text
