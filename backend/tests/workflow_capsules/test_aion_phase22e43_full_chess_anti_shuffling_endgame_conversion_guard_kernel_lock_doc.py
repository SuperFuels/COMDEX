from pathlib import Path


def test_phase22e43_lock_doc_exists_and_names_anti_shuffling_guard():
    path = Path("docs/rfc/aion_phase22e43_full_chess_anti_shuffling_endgame_conversion_guard_kernel_lock.tex")
    assert path.exists()

    text = path.read_text(encoding="utf-8")
    assert "Phase 22E.43" in text
    assert "Anti-Shuffling" in text
    assert "b8b7" in text
    assert "endgame conversion" in text
    assert "Stockfish" in text
    assert "LLM" in text
