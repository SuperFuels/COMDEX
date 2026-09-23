from pathlib import Path


def test_phase22b8_full_chess_move_generator_doc_lock_exists():
    path = Path("docs/rfc/aion_phase22b8_full_chess_move_generator_kernel_lock.tex")
    text = path.read_text(encoding="utf-8")

    assert "AION Phase 22B.8: Full Chess Move Generator Kernel Lock" in text
    assert "pawn\\_forward\\_move\\_count" in text
    assert "pawn\\_capture\\_move\\_count" in text
    assert "knight\\_move\\_count" in text
    assert "sliding\\_move\\_count" in text
    assert "king\\_move\\_count" in text
    assert "blocked\\_path\\_rejection\\_count" in text
    assert "king\\_safety\\_rejection\\_count" in text
    assert "selected\\_move\\_legal" in text
    assert "uses\\_llm\\_shortcut = false" in text
    assert "Lock ID: AION-PHASE22B8-FULL-CHESS-MOVE-GENERATOR-KERNEL-LOCK" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
