from pathlib import Path


def test_phase22b11_full_chess_capture_evaluation_doc_lock_exists():
    path = Path("docs/rfc/aion_phase22b11_full_chess_capture_evaluation_kernel_lock.tex")
    text = path.read_text(encoding="utf-8")

    assert "AION Phase 22B.11: Full Chess Capture Evaluation Kernel Lock" in text
    assert "capture\\_candidate\\_count" in text
    assert "safe\\_capture\\_count" in text
    assert "bad\\_exchange\\_rejection\\_count" in text
    assert "hanging\\_piece\\_trap\\_rejection\\_count" in text
    assert "king\\_exposure\\_rejection\\_count" in text
    assert "blocked\\_capture\\_rejection\\_count" in text
    assert "defended\\_target\\_count" in text
    assert "selected\\_capture" in text
    assert "selected\\_capture\\_safe" in text
    assert "selected\\_capture\\_profitable" in text
    assert "preserved\\_king\\_safety" in text
    assert "uses\\_llm\\_shortcut = false" in text
    assert "Lock ID: AION-PHASE22B11-FULL-CHESS-CAPTURE-EVALUATION-KERNEL-LOCK" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
