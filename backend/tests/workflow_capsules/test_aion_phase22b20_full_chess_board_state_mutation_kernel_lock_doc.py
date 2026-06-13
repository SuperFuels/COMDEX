from pathlib import Path


def test_phase22b20_full_chess_board_state_mutation_doc_lock_exists():
    path = Path("docs/rfc/aion_phase22b20_full_chess_board_state_mutation_kernel_lock.tex")
    text = path.read_text(encoding="utf-8")

    assert "AION Phase 22B.20: Full Chess Board State Mutation Kernel Lock" in text
    assert "board\\_before" in text
    assert "board\\_after" in text
    assert "origin\\_cleared" in text
    assert "target\\_occupied\\_by\\_moved\\_piece" in text
    assert "captured\\_piece\\_removed" in text
    assert "piece\\_count\\_before" in text
    assert "piece\\_count\\_after" in text
    assert "board\\_hash\\_before" in text
    assert "board\\_hash\\_after" in text
    assert "board\\_hash\\_changed" in text
    assert "king\\_safe\\_after\\_move" in text
    assert "mutation\\_trace\\_hash" in text
    assert "uses\\_llm\\_shortcut = false" in text
    assert "Lock ID: AION-PHASE22B20-FULL-CHESS-BOARD-STATE-MUTATION-KERNEL-LOCK" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
