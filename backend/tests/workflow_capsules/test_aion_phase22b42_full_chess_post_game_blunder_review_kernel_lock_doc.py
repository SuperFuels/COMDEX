from pathlib import Path


def test_phase22b42_post_game_blunder_review_doc_lock_exists():
    path = Path("docs/rfc/aion_phase22b42_full_chess_post_game_blunder_review_kernel_lock.tex")
    text = path.read_text(encoding="utf-8")

    assert "AION Phase 22B.42: Full Chess Post-Game Blunder Review Kernel Lock" in text
    assert "game_id: cPv6iyKb" in text
    assert "opponent: Stockfish level 1" in text
    assert "final_status: mate" in text
    assert "winner: white" in text
    assert "aion_result: win" in text
    assert "review\\_mode" in text
    assert "analyzed\\_ply\\_count" in text
    assert "analyzed\\_aion\\_move\\_count" in text
    assert "repeated\\_cycle\\_detected" in text
    assert "suboptimal\\_pattern\\_count" in text
    assert "policy\\_memory\\_mutated" in text
    assert "post\\_game\\_review\\_trace\\_hash" in text
    assert "uses\\_llm\\_shortcut = false" in text
    assert "strongest_negative_signal: repetitive_piece_shuffling" in text
    assert "Lock ID: AION-PHASE22B42-FULL-CHESS-POST-GAME-BLUNDER-REVIEW-KERNEL-LOCK" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
