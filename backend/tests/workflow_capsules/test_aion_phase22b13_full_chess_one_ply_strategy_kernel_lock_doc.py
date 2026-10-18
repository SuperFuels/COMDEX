from pathlib import Path


def test_phase22b13_full_chess_one_ply_strategy_doc_lock_exists():
    path = Path("docs/rfc/aion_phase22b13_full_chess_one_ply_strategy_kernel_lock.tex")
    text = path.read_text(encoding="utf-8")

    assert "AION Phase 22B.13: Full Chess One-Ply Strategy Kernel Lock" in text
    assert "candidate\\_strategy\\_count" in text
    assert "generated\\_legal\\_count" in text
    assert "safety\\_preserving\\_count" in text
    assert "safe\\_profitable\\_capture\\_count" in text
    assert "threat\\_improving\\_count" in text
    assert "survives\\_opponent\\_reply\\_count" in text
    assert "rejected\\_by\\_safety\\_count" in text
    assert "rejected\\_by\\_bad\\_reply\\_count" in text
    assert "rejected\\_by\\_bad\\_capture\\_count" in text
    assert "selected\\_strategy" in text
    assert "one\\_ply\\_strategy\\_trace\\_hash" in text
    assert "uses\\_llm\\_shortcut = false" in text
    assert "Lock ID: AION-PHASE22B13-FULL-CHESS-ONE-PLY-STRATEGY-KERNEL-LOCK" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
