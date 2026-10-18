from pathlib import Path


def test_phase22b12_full_chess_opponent_reply_doc_lock_exists():
    path = Path("docs/rfc/aion_phase22b12_full_chess_opponent_reply_kernel_lock.tex")
    text = path.read_text(encoding="utf-8")

    assert "AION Phase 22B.12: Full Chess Opponent Reply Kernel Lock" in text
    assert "candidate\\_move\\_count" in text
    assert "opponent\\_reply\\_count" in text
    assert "safe\\_after\\_reply\\_count" in text
    assert "bad\\_reply\\_rejection\\_count" in text
    assert "king\\_exposure\\_reply\\_rejection\\_count" in text
    assert "material\\_loss\\_reply\\_rejection\\_count" in text
    assert "selected\\_move" in text
    assert "selected\\_move\\_survives\\_reply" in text
    assert "avoided\\_bad\\_opponent\\_reply" in text
    assert "opponent\\_reply\\_trace\\_hash" in text
    assert "uses\\_llm\\_shortcut = false" in text
    assert "Lock ID: AION-PHASE22B12-FULL-CHESS-OPPONENT-REPLY-KERNEL-LOCK" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
