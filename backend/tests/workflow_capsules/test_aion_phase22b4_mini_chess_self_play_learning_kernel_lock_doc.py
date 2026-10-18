from pathlib import Path


def test_phase22b4_mini_chess_self_play_learning_doc_lock_exists():
    path = Path("docs/rfc/aion_phase22b4_mini_chess_self_play_learning_kernel_lock.tex")
    text = path.read_text(encoding="utf-8")

    assert "AION Phase 22B.4: Mini Chess Self-Play Learning Kernel Lock" in text
    assert "episodes\\_run" in text
    assert "baseline\\_result" in text
    assert "final\\_result" in text
    assert "reward\\_delta" in text
    assert "policy\\_improved" in text
    assert "learned\\_from\\_loss" in text
    assert "win\\_condition\\_reached" in text
    assert "uses\\_llm\\_shortcut = false" in text
    assert "Lock ID: AION-PHASE22B4-MINI-CHESS-SELF-PLAY-LEARNING-KERNEL-LOCK" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
