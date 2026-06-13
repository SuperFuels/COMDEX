from pathlib import Path


def test_phase22b10_full_chess_legal_move_safety_doc_lock_exists():
    path = Path("docs/rfc/aion_phase22b10_full_chess_legal_move_safety_kernel_lock.tex")
    text = path.read_text(encoding="utf-8")

    assert "AION Phase 22B.10: Full Chess Legal Move Safety Kernel Lock" in text
    assert "pseudo\\_legal\\_move\\_count" in text
    assert "safe\\_legal\\_move\\_count" in text
    assert "unsafe\\_king\\_exposure\\_count" in text
    assert "own\\_piece\\_rejection\\_count" in text
    assert "illegal\\_geometry\\_count" in text
    assert "selected\\_safe\\_move" in text
    assert "king\\_safe\\_after\\_selected\\_move" in text
    assert "selected\\_move\\_preserves\\_king\\_safety" in text
    assert "uses\\_llm\\_shortcut = false" in text
    assert "Lock ID: AION-PHASE22B10-FULL-CHESS-LEGAL-MOVE-SAFETY-KERNEL-LOCK" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
