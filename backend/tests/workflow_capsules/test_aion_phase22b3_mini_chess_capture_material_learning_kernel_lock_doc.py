from pathlib import Path


def test_phase22b3_mini_chess_capture_material_learning_doc_lock_exists():
    path = Path("docs/rfc/aion_phase22b3_mini_chess_capture_material_learning_kernel_lock.tex")
    text = path.read_text(encoding="utf-8")

    assert "AION Phase 22B.3: Mini Chess Capture Material Learning Kernel Lock" in text
    assert "piece\\_values" in text
    assert "capture\\_candidates" in text
    assert "selected\\_capture" in text
    assert "rejected\\_captures" in text
    assert "learned\\_safe\\_capture" in text
    assert "avoided\\_bad\\_capture" in text
    assert "protected\\_high\\_value\\_piece" in text
    assert "uses\\_llm\\_shortcut = false" in text
    assert "Lock ID: AION-PHASE22B3-MINI-CHESS-CAPTURE-MATERIAL-LEARNING-KERNEL-LOCK" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
