from pathlib import Path


def test_phase22b25_full_chess_self_play_training_doc_lock_exists():
    path = Path("docs/rfc/aion_phase22b25_full_chess_self_play_training_kernel_lock.tex")
    text = path.read_text(encoding="utf-8")

    assert "AION Phase 22B.25: Full Chess Self-Play Training Kernel Lock" in text
    assert "training\\_game\\_count" in text
    assert "completed\\_training\\_game\\_count" in text
    assert "stable\\_or\\_winning\\_game\\_count" in text
    assert "losing\\_or\\_penalised\\_game\\_count" in text
    assert "reinforcement\\_update\\_count" in text
    assert "penalty\\_update\\_count" in text
    assert "initial\\_policy\\_strength" in text
    assert "final\\_policy\\_strength" in text
    assert "policy\\_improvement\\_delta" in text
    assert "selected\\_policy\\_after\\_training" in text
    assert "rejected\\_policy\\_after\\_training" in text
    assert "training\\_games" in text
    assert "training\\_trace\\_hash" in text
    assert "uses\\_llm\\_shortcut = false" in text
    assert "Lock ID: AION-PHASE22B25-FULL-CHESS-SELF-PLAY-TRAINING-KERNEL-LOCK" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
