from pathlib import Path


def test_phase22b36_full_chess_local_engine_match_harness_doc_lock_exists():
    path = Path("docs/rfc/aion_phase22b36_full_chess_local_engine_match_harness_kernel_lock.tex")
    text = path.read_text(encoding="utf-8")

    assert "AION Phase 22B.36: Full Chess Local Engine Match Harness Kernel Lock" in text
    assert "harness\\_mode" in text
    assert "network\\_call\\_performed" in text
    assert "human\\_approval\\_required" in text
    assert "opponent\\_profile\\_count" in text
    assert "match\\_count" in text
    assert "completed\\_match\\_count" in text
    assert "win\\_count" in text
    assert "draw\\_count" in text
    assert "loss\\_count" in text
    assert "score\\_total" in text
    assert "score\\_percentage" in text
    assert "local\\_match\\_passed" in text
    assert "opponent\\_profiles" in text
    assert "local\\_matches" in text
    assert "local\\_match\\_trace\\_hash" in text
    assert "uses\\_llm\\_shortcut = false" in text
    assert "Lock ID: AION-PHASE22B36-FULL-CHESS-LOCAL-ENGINE-MATCH-HARNESS-KERNEL-LOCK" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
