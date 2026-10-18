from pathlib import Path


def test_phase22e4_lock_doc_exists_and_names_policy_update():
    path = Path("docs/rfc/aion_phase22e4_full_chess_post_game_strategic_review_policy_kernel_lock.tex")
    assert path.exists()

    text = path.read_text(encoding="utf-8")
    assert "Phase 22E.4" in text
    assert "Post-Game Strategic Review" in text
    assert "Policy Update" in text
    assert "mate loss" in text
    assert "positional decline" in text
    assert "Stockfish" in text
    assert "LLM" in text
