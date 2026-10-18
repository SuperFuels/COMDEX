from pathlib import Path


def test_phase22e9_lock_doc_exists_and_names_concept_guided_bias():
    path = Path("docs/rfc/aion_phase22e9_full_chess_concept_guided_search_plan_bias_kernel_lock.tex")
    assert path.exists()

    text = path.read_text(encoding="utf-8")
    assert "Phase 22E.9" in text
    assert "Concept-Guided Search" in text
    assert "Plan Bias" in text
    assert "concept policy weights" in text
    assert "live Lichess" in text
    assert "Stockfish" in text
    assert "LLM" in text
