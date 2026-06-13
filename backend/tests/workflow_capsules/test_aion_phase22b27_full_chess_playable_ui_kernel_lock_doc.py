from pathlib import Path


def test_phase22b27_full_chess_playable_ui_doc_lock_exists():
    path = Path("docs/rfc/aion_phase22b27_full_chess_playable_ui_kernel_lock.tex")
    text = path.read_text(encoding="utf-8")

    assert "AION Phase 22B.27: Full Chess Playable UI Kernel Lock" in text
    assert "initial\\_fen" in text
    assert "user\\_uci\\_move" in text
    assert "selected\\_aion\\_uci\\_move" in text
    assert "final\\_fen" in text
    assert "final\\_pgn" in text
    assert "ui\\_status" in text
    assert "user\\_move\\_accepted" in text
    assert "aion\\_response\\_ready" in text
    assert "board\\_updated\\_after\\_user\\_move" in text
    assert "board\\_updated\\_after\\_aion\\_move" in text
    assert "move\\_log\\_count" in text
    assert "playable\\_ui\\_state" in text
    assert "playable\\_ui\\_trace\\_hash" in text
    assert "uses\\_llm\\_shortcut = false" in text
    assert "Lock ID: AION-PHASE22B27-FULL-CHESS-PLAYABLE-UI-KERNEL-LOCK" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
