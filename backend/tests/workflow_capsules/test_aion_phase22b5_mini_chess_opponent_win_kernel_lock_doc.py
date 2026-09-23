from pathlib import Path


def test_phase22b5_mini_chess_opponent_win_doc_lock_exists():
    path = Path("docs/rfc/aion_phase22b5_mini_chess_opponent_win_kernel_lock.tex")
    text = path.read_text(encoding="utf-8")

    assert "AION Phase 22B.5: Mini Chess Opponent Win Kernel Lock" in text
    assert "opponent\\_type" in text
    assert "aion\\_legal\\_moves" in text
    assert "aion\\_illegal\\_moves" in text
    assert "learned\\_policy\\_applied" in text
    assert "avoided\\_known\\_bad\\_capture" in text
    assert "preserved\\_king\\_safety" in text
    assert "win\\_condition" in text
    assert "aion\\_won" in text
    assert "uses\\_llm\\_shortcut = false" in text
    assert "Lock ID: AION-PHASE22B5-MINI-CHESS-OPPONENT-WIN-KERNEL-LOCK" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
