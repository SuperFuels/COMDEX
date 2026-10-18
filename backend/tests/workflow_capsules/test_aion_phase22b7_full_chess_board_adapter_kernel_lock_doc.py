from pathlib import Path


def test_phase22b7_full_chess_board_adapter_doc_lock_exists():
    path = Path("docs/rfc/aion_phase22b7_full_chess_board_adapter_kernel_lock.tex")
    text = path.read_text(encoding="utf-8")

    assert "AION Phase 22B.7: Full Chess Board Adapter Kernel Lock" in text
    assert "board\\_size = 8" in text
    assert "initial\\_piece\\_count = 32" in text
    assert "white\\_piece\\_count = 16" in text
    assert "black\\_piece\\_count = 16" in text
    assert "standard\\_start\\_position" in text
    assert "legal\\_opening\\_move\\_count" in text
    assert "blocked\\_piece\\_rejection\\_count" in text
    assert "uses\\_llm\\_shortcut = false" in text
    assert "Lock ID: AION-PHASE22B7-FULL-CHESS-BOARD-ADAPTER-KERNEL-LOCK" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
