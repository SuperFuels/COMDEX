from pathlib import Path


def test_phase22e10_lock_doc_exists_and_names_move_reranking():
    path = Path("docs/rfc/aion_phase22e10_full_chess_concept_guided_move_reranking_kernel_lock.tex")
    assert path.exists()

    text = path.read_text(encoding="utf-8")
    assert "Phase 22E.10" in text
    assert "Concept-Guided Move Re-Ranking" in text
    assert "legal candidate moves" in text
    assert "no live Lichess" in text
    assert "Stockfish" in text
    assert "LLM" in text
