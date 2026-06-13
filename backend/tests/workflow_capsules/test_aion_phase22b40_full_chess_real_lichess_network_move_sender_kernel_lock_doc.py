from pathlib import Path


def test_phase22b40_real_lichess_network_move_sender_doc_lock_exists():
    path = Path("docs/rfc/aion_phase22b40_full_chess_real_lichess_network_move_sender_kernel_lock.tex")
    text = path.read_text(encoding="utf-8")

    assert "AION Phase 22B.40: Full Chess Real Lichess Network Move Sender Kernel Lock" in text
    assert "sender\\_mode" in text
    assert "selected\\_bestmove" in text
    assert "selected\\_policy" in text
    assert "send\\_allowed" in text
    assert "send\\_attempted" in text
    assert "send\\_success" in text
    assert "block\\_reason" in text
    assert "http\\_status" in text
    assert "network\\_call\\_performed" in text
    assert "real\\_send\\_trace\\_hash" in text
    assert "uses\\_llm\\_shortcut = false" in text
    assert "LICHESS_BOT_TOKEN" in text
    assert "Lock ID: AION-PHASE22B40-FULL-CHESS-REAL-LICHESS-NETWORK-MOVE-SENDER-KERNEL-LOCK" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
