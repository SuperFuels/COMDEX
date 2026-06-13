from pathlib import Path


def test_phase22e2_lock_doc_exists_and_names_goal_bias():
    path = Path("docs/rfc/aion_phase22e2_full_chess_goal_biased_strategic_search_kernel_lock.tex")
    assert path.exists()

    text = path.read_text(encoding="utf-8")
    assert "Phase 22E.2" in text
    assert "Multi-Ply Strategic Search with Goal Bias" in text
    assert "positional features" in text
    assert "goal bias" in text
    assert "promotion" in text
    assert "invasion" in text
    assert "Stockfish" in text
    assert "LLM" in text
