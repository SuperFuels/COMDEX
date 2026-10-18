from pathlib import Path


def test_phase22b23_full_chess_real_opponent_loop_doc_lock_exists():
    path = Path("docs/rfc/aion_phase22b23_full_chess_real_opponent_game_loop_kernel_lock.tex")
    text = path.read_text(encoding="utf-8")

    assert "AION Phase 22B.23: Full Chess Real Opponent Game Loop Kernel Lock" in text
    assert "opponent\\_source" in text
    assert "initial\\_fen" in text
    assert "final\\_fen" in text
    assert "turn\\_count" in text
    assert "aion\\_turn\\_count" in text
    assert "opponent\\_turn\\_count" in text
    assert "accepted\\_opponent\\_move\\_count" in text
    assert "mutation\\_applied\\_count" in text
    assert "active\\_color\\_after\\_loop" in text
    assert "pgn\\_export" in text
    assert "pgn\\_export\\_ok" in text
    assert "turns" in text
    assert "final\\_board\\_hash" in text
    assert "real\\_opponent\\_loop\\_trace\\_hash" in text
    assert "uses\\_llm\\_shortcut = false" in text
    assert "Lock ID: AION-PHASE22B23-FULL-CHESS-REAL-OPPONENT-GAME-LOOP-KERNEL-LOCK" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
