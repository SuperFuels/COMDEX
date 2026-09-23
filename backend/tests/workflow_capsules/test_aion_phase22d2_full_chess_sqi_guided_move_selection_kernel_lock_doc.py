from pathlib import Path


def test_phase22d2_sqi_guided_move_selection_doc_lock_exists():
    path = Path("docs/rfc/aion_phase22d2_full_chess_sqi_guided_move_selection_kernel_lock.tex")
    text = path.read_text(encoding="utf-8")

    assert "AION Phase 22D.2: Full Chess SQI-Guided Move Selection Kernel Lock" in text
    assert "SQI-guided chess move selection implemented and tested" in text
    assert "full_chess_sqi_guided_move_selection_kernel.py" in text
    assert "use SQI-adjusted score as the active ranking value" in text
    assert "coherence, resonance, decoherence and collapse-weight" in text
    assert "remain live-loop compatible" in text
    assert "22D.3 -- Live Loop Uses SQI-Guided Move Selection" in text
    assert "Lock ID: AION-PHASE22D2-FULL-CHESS-SQI-GUIDED-MOVE-SELECTION-KERNEL-LOCK" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
