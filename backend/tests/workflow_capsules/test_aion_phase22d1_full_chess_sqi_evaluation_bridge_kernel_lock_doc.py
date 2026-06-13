from pathlib import Path


def test_phase22d1_sqi_bridge_doc_lock_exists():
    path = Path("docs/rfc/aion_phase22d1_full_chess_sqi_evaluation_bridge_kernel_lock.tex")
    text = path.read_text(encoding="utf-8")

    assert "AION Phase 22D.1: Full Chess SQI Evaluation Bridge Kernel Lock" in text
    assert "chess SQI evaluation bridge implemented and tested" in text
    assert "full_chess_sqi_evaluation_bridge_kernel.py" in text
    assert "coherence score" in text
    assert "resonance score" in text
    assert "decoherence penalty" in text
    assert "collapse weight" in text
    assert "does not yet invoke physical wave hardware" in text
    assert "22D.2 -- SQI-Guided Chess Move Selection" in text
    assert "Lock ID: AION-PHASE22D1-FULL-CHESS-SQI-EVALUATION-BRIDGE-KERNEL-LOCK" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
