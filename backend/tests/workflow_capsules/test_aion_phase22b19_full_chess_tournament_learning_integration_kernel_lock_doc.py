from pathlib import Path


def test_phase22b19_full_chess_tournament_learning_doc_lock_exists():
    path = Path("docs/rfc/aion_phase22b19_full_chess_tournament_learning_integration_kernel_lock.tex")
    text = path.read_text(encoding="utf-8")

    assert "AION Phase 22B.19: Full Chess Tournament Learning Integration Kernel Lock" in text
    assert "tournament\\_winner\\_policy\\_id" in text
    assert "tournament\\_winner\\_strategy" in text
    assert "tournament\\_learning\\_update\\_count" in text
    assert "positive\\_update\\_count" in text
    assert "penalty\\_update\\_count" in text
    assert "learned\\_policy\\_reinforced" in text
    assert "greedy\\_policy\\_penalised" in text
    assert "king\\_exposure\\_policy\\_penalised" in text
    assert "material\\_loss\\_policy\\_penalised" in text
    assert "previous\\_learned\\_weight" in text
    assert "updated\\_learned\\_weight" in text
    assert "previous\\_greedy\\_penalty" in text
    assert "updated\\_greedy\\_penalty" in text
    assert "next\\_tournament\\_ready" in text
    assert "tournament\\_learning\\_trace\\_hash" in text
    assert "uses\\_llm\\_shortcut = false" in text
    assert "Lock ID: AION-PHASE22B19-FULL-CHESS-TOURNAMENT-LEARNING-INTEGRATION-KERNEL-LOCK" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
