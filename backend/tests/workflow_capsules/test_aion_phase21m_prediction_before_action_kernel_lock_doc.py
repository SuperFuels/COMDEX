from pathlib import Path


def test_phase21m_prediction_before_action_kernel_doc_lock_exists():
    path = Path("docs/rfc/aion_phase21m_prediction_before_action_kernel_lock.tex")
    text = path.read_text(encoding="utf-8")

    assert "AION Phase 21M: Prediction Before Action Kernel Lock" in text
    assert "prediction \\rightarrow action \\rightarrow outcome" in text
    assert "predicted\\_reward" in text
    assert "actual\\_reward" in text
    assert "prediction\\_error\\_delta" in text
    assert "final\\_prediction\\_model" in text
    assert "uses\\_llm\\_shortcut = false" in text
    assert "Lock ID: AION-PHASE21M-PREDICTION-BEFORE-ACTION-KERNEL-LOCK" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
