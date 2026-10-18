from pathlib import Path


def test_phase22e5_lock_doc_exists_and_names_curriculum():
    path = Path("docs/rfc/aion_phase22e5_full_chess_self_play_curriculum_kernel_lock.tex")
    assert path.exists()

    text = path.read_text(encoding="utf-8")
    assert "Phase 22E.5" in text
    assert "Self-Play Curriculum" in text
    assert "Increasing Difficulty" in text
    assert "post-game strategic policy updates" in text
    assert "Stockfish" in text
    assert "LLM" in text
