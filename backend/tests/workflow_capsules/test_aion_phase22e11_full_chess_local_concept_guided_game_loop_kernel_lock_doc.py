from pathlib import Path


def test_phase22e11_lock_doc_exists_and_names_local_loop_preview():
    path = Path("docs/rfc/aion_phase22e11_full_chess_local_concept_guided_game_loop_kernel_lock.tex")
    assert path.exists()

    text = path.read_text(encoding="utf-8")
    assert "Phase 22E.11" in text
    assert "Local Concept-Guided Game Loop Preview" in text
    assert "multi-ply" in text
    assert "no live Lichess" in text
    assert "Stockfish" in text
    assert "LLM" in text
