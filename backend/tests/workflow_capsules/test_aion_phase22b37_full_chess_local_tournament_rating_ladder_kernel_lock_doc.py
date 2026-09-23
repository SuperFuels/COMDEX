from pathlib import Path


def test_phase22b37_full_chess_local_tournament_rating_ladder_doc_lock_exists():
    path = Path("docs/rfc/aion_phase22b37_full_chess_local_tournament_rating_ladder_kernel_lock.tex")
    text = path.read_text(encoding="utf-8")

    assert "AION Phase 22B.37: Full Chess Local Tournament / Rating Ladder Kernel Lock" in text
    assert "ladder\\_mode" in text
    assert "network\\_call\\_performed" in text
    assert "human\\_approval\\_required" in text
    assert "tier\\_count" in text
    assert "total\\_games\\_played" in text
    assert "total\\_score\\_percentage" in text
    assert "passed\\_tier\\_count" in text
    assert "failed\\_tier\\_count" in text
    assert "highest\\_passed\\_tier" in text
    assert "lowest\\_failed\\_tier" in text
    assert "estimated\\_rating\\_floor" in text
    assert "estimated\\_rating\\_ceiling" in text
    assert "estimated\\_rating\\_band\\_label" in text
    assert "ladder\\_trace\\_hash" in text
    assert "uses\\_llm\\_shortcut = false" in text
    assert "Lock ID: AION-PHASE22B37-FULL-CHESS-LOCAL-TOURNAMENT-RATING-LADDER-KERNEL-LOCK" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
