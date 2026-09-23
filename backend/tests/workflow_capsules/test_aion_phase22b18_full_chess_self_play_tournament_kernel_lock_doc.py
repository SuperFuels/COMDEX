from pathlib import Path


def test_phase22b18_full_chess_self_play_tournament_doc_lock_exists():
    path = Path("docs/rfc/aion_phase22b18_full_chess_self_play_tournament_kernel_lock.tex")
    text = path.read_text(encoding="utf-8")

    assert "AION Phase 22B.18: Full Chess Self-Play Tournament Kernel Lock" in text
    assert "policy\\_count" in text
    assert "match\\_count" in text
    assert "completed\\_match\\_count" in text
    assert "learned\\_policy\\_win\\_count" in text
    assert "safe\\_policy\\_win\\_count" in text
    assert "greedy\\_policy\\_loss\\_count" in text
    assert "king\\_exposure\\_policy\\_loss\\_count" in text
    assert "material\\_loss\\_policy\\_loss\\_count" in text
    assert "tournament\\_winner\\_policy\\_id" in text
    assert "tournament\\_winner\\_strategy" in text
    assert "tournament\\_standings" in text
    assert "tournament\\_trace\\_hash" in text
    assert "uses\\_llm\\_shortcut = false" in text
    assert "Lock ID: AION-PHASE22B18-FULL-CHESS-SELF-PLAY-TOURNAMENT-KERNEL-LOCK" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
