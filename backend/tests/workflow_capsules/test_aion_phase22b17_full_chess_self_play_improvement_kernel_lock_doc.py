from pathlib import Path


def test_phase22b17_full_chess_self_play_doc_lock_exists():
    path = Path("docs/rfc/aion_phase22b17_full_chess_self_play_improvement_kernel_lock.tex")
    text = path.read_text(encoding="utf-8")

    assert "AION Phase 22B.17: Full Chess Self-Play Improvement Kernel Lock" in text
    assert "self\\_play\\_episode\\_count" in text
    assert "completed\\_episode\\_count" in text
    assert "stable\\_or\\_winning\\_episode\\_count" in text
    assert "improved\\_episode\\_count" in text
    assert "preferred\\_strategy\\_retention\\_count" in text
    assert "avoided\\_bad\\_line\\_count" in text
    assert "initial\\_safe\\_capture\\_weight" in text
    assert "final\\_safe\\_capture\\_weight" in text
    assert "initial\\_multi\\_ply\\_survival\\_weight" in text
    assert "final\\_multi\\_ply\\_survival\\_weight" in text
    assert "initial\\_greedy\\_capture\\_penalty" in text
    assert "final\\_greedy\\_capture\\_penalty" in text
    assert "preferred\\_strategy\\_after\\_self\\_play" in text
    assert "self\\_play\\_trace\\_hash" in text
    assert "uses\\_llm\\_shortcut = false" in text
    assert "Lock ID: AION-PHASE22B17-FULL-CHESS-SELF-PLAY-IMPROVEMENT-KERNEL-LOCK" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
