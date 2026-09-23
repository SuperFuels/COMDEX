from pathlib import Path


def test_phase22b1_mini_chess_legal_move_doc_lock_exists():
    path = Path("docs/rfc/aion_phase22b1_mini_chess_legal_move_kernel_lock.tex")
    text = path.read_text(encoding="utf-8")

    assert "AION Phase 22B.1: Mini Chess Legal Move Kernel Lock" in text
    assert "board\\_size" in text
    assert "legal\\_moves" in text
    assert "illegal\\_moves" in text
    assert "capture\\_moves" in text
    assert "threat\\_map" in text
    assert "selected\\_safe\\_capture" in text
    assert "uses\\_llm\\_shortcut = false" in text
    assert "Lock ID: AION-PHASE22B1-MINI-CHESS-LEGAL-MOVE-KERNEL-LOCK" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
