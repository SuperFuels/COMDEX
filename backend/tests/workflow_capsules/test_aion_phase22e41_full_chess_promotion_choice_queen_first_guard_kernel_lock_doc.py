from pathlib import Path


def test_phase22e41_lock_doc_exists_and_names_queen_first_guard():
    path = Path("docs/rfc/aion_phase22e41_full_chess_promotion_choice_queen_first_guard_kernel_lock.tex")
    assert path.exists()

    text = path.read_text(encoding="utf-8")
    assert "Phase 22E.41" in text
    assert "Queen First" in text
    assert "d7c8r" in text
    assert "d7c8q" in text
    assert "Stockfish" in text
    assert "LLM" in text
