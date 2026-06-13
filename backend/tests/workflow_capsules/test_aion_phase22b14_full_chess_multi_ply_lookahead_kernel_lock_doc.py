from pathlib import Path


def test_phase22b14_full_chess_multi_ply_doc_lock_exists():
    path = Path("docs/rfc/aion_phase22b14_full_chess_multi_ply_lookahead_kernel_lock.tex")
    text = path.read_text(encoding="utf-8")

    assert "AION Phase 22B.14: Full Chess Multi-Ply Lookahead Kernel Lock" in text
    assert "lookahead\\_depth" in text
    assert "candidate\\_line\\_count" in text
    assert "surviving\\_line\\_count" in text
    assert "greedy\\_trap\\_rejection\\_count" in text
    assert "king\\_safety\\_rejection\\_count" in text
    assert "material\\_loss\\_rejection\\_count" in text
    assert "selected\\_line" in text
    assert "selected\\_line\\_survives\\_depth" in text
    assert "multi\\_ply\\_trace\\_hash" in text
    assert "uses\\_llm\\_shortcut = false" in text
    assert "Lock ID: AION-PHASE22B14-FULL-CHESS-MULTI-PLY-LOOKAHEAD-KERNEL-LOCK" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
