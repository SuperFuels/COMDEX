from pathlib import Path


def test_phase22b16_full_chess_learning_doc_lock_exists():
    path = Path("docs/rfc/aion_phase22b16_full_chess_learning_loop_kernel_lock.tex")
    text = path.read_text(encoding="utf-8")

    assert "AION Phase 22B.16: Full Chess Learning Loop Kernel Lock" in text
    assert "learning\\_signal\\_count" in text
    assert "positive\\_learning\\_count" in text
    assert "negative\\_learning\\_count" in text
    assert "reinforced\\_safe\\_capture\\_count" in text
    assert "reinforced\\_surviving\\_strategy\\_count" in text
    assert "reinforced\\_multi\\_ply\\_line\\_count" in text
    assert "weakened\\_greedy\\_capture\\_count" in text
    assert "weakened\\_king\\_exposure\\_count" in text
    assert "weakened\\_material\\_loss\\_count" in text
    assert "learned\\_policy" in text
    assert "preferred\\_strategy\\_after\\_learning" in text
    assert "learning\\_loop\\_trace\\_hash" in text
    assert "uses\\_llm\\_shortcut = false" in text
    assert "Lock ID: AION-PHASE22B16-FULL-CHESS-LEARNING-LOOP-KERNEL-LOCK" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
