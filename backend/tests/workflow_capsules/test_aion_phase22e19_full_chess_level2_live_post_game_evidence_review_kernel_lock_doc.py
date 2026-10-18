from pathlib import Path


def test_phase22e19_lock_doc_exists_and_names_failure_review():
    path = Path("docs/rfc/aion_phase22e19_full_chess_level2_live_post_game_evidence_review_kernel_lock.tex")
    assert path.exists()

    text = path.read_text(encoding="utf-8")
    assert "Phase 22E.19" in text
    assert "Live Level-2 Post-Game Evidence Lock" in text
    assert "outoftime" in text
    assert "61/61" in text
    assert "d7d8q" in text
    assert "queen endgame" in text
    assert "clock pressure" in text
    assert "Stockfish" in text
    assert "LLM" in text
