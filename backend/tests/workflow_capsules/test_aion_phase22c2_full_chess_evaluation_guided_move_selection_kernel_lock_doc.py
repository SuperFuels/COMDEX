from pathlib import Path


def test_phase22c2_evaluation_guided_move_selection_doc_lock_exists():
    path = Path("docs/rfc/aion_phase22c2_full_chess_evaluation_guided_move_selection_kernel_lock.tex")
    text = path.read_text(encoding="utf-8")

    assert "AION Phase 22C.2: Full Chess Evaluation-Guided Move Selection Kernel Lock" in text
    assert "evaluation-guided legal move selection implemented and tested" in text
    assert "full_chess_evaluation_guided_move_selection_kernel.py" in text
    assert "generate legal chess moves" in text
    assert "score each candidate using the Phase 22C.1 evaluator" in text
    assert "prioritise terminal mate moves" in text
    assert "avoid emitting moves from terminal positions" in text
    assert "22C.3 -- Depth-Limited Lookahead Search" in text
    assert "Lock ID: AION-PHASE22C2-FULL-CHESS-EVALUATION-GUIDED-MOVE-SELECTION-KERNEL-LOCK" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
