from pathlib import Path


def test_phase22c1_real_evaluation_function_doc_lock_exists():
    path = Path("docs/rfc/aion_phase22c1_full_chess_real_evaluation_function_kernel_lock.tex")
    text = path.read_text(encoding="utf-8")

    assert "AION Phase 22C.1: Full Chess Real Evaluation Function Kernel Lock" in text
    assert "material balance" in text
    assert "king safety" in text
    assert "piece activity" in text
    assert "centre control" in text
    assert "pawn structure" in text
    assert "repetition-risk penalty" in text
    assert "terminal mate or draw awareness" in text
    assert "full_chess_real_evaluation_function_kernel.py" in text
    assert "full_chess_real_evaluation_function_memory.json" in text
    assert "22C.2 -- Evaluation-Guided Move Selection" in text
    assert "Lock ID: AION-PHASE22C1-FULL-CHESS-REAL-EVALUATION-FUNCTION-KERNEL-LOCK" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
