from pathlib import Path


def test_phase22b15_full_chess_game_loop_doc_lock_exists():
    path = Path("docs/rfc/aion_phase22b15_full_chess_game_loop_kernel_lock.tex")
    text = path.read_text(encoding="utf-8")

    assert "AION Phase 22B.15: Full Chess Game Loop Kernel Lock" in text
    assert "planned\\_turn\\_count" in text
    assert "completed\\_turn\\_count" in text
    assert "aion\\_turn\\_count" in text
    assert "opponent\\_turn\\_count" in text
    assert "legal\\_turn\\_count" in text
    assert "king\\_safe\\_turn\\_count" in text
    assert "opponent\\_reply\\_evaluated\\_count" in text
    assert "multi\\_ply\\_checked\\_count" in text
    assert "material\\_gain\\_total" in text
    assert "final\\_state\\_score" in text
    assert "game\\_loop\\_completed" in text
    assert "game\\_loop\\_trace\\_hash" in text
    assert "uses\\_llm\\_shortcut = false" in text
    assert "Lock ID: AION-PHASE22B15-FULL-CHESS-GAME-LOOP-KERNEL-LOCK" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
