from pathlib import Path


def test_phase22e40_lock_doc_exists_and_names_failure_map():
    path = Path("docs/rfc/aion_phase22e40_full_chess_level2_strategic_well_live_post_game_review_kernel_lock.tex")
    assert path.exists()

    text = path.read_text(encoding="utf-8")
    assert "Phase 22E.40" in text
    assert "Strategic Well Live Post-Game Review" in text
    assert "h2h4" in text
    assert "d7c8r" in text
    assert "Queen First" in text
    assert "Stockfish" in text
    assert "LLM" in text
