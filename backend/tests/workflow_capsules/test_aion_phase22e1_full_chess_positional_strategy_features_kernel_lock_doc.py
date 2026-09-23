from pathlib import Path


def test_phase22e1_lock_doc_exists_and_names_features():
    path = Path("docs/rfc/aion_phase22e1_full_chess_positional_strategy_features_kernel_lock.tex")
    assert path.exists()

    text = path.read_text(encoding="utf-8")
    assert "Phase 22E.1" in text
    assert "Positional Strategy Features" in text
    assert "king safety" in text
    assert "centre control" in text
    assert "passed pawn" in text
    assert "invasion risk" in text
    assert "promotion danger" in text
    assert "Stockfish" in text
    assert "LLM" in text
