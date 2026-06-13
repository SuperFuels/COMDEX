from pathlib import Path


def test_phase22b31_full_chess_guarded_live_move_execution_doc_lock_exists():
    path = Path("docs/rfc/aion_phase22b31_full_chess_guarded_live_move_execution_kernel_lock.tex")
    text = path.read_text(encoding="utf-8")

    assert "AION Phase 22B.31: Full Chess Guarded Live Move Execution Kernel Lock" in text
    assert "execution\\_mode" in text
    assert "request" in text
    assert "guard\\_decision" in text
    assert "prepared\\_request" in text
    assert "would\\_post\\_move" in text
    assert "network\\_call\\_performed" in text
    assert "live\\_write\\_blocked" in text
    assert "dry\\_run\\_preview\\_emitted" in text
    assert "selected\\_bestmove" in text
    assert "game\\_id" in text
    assert "guarded\\_execution\\_trace\\_hash" in text
    assert "uses\\_llm\\_shortcut = false" in text
    assert "human approval" in text
    assert "Lock ID: AION-PHASE22B31-FULL-CHESS-GUARDED-LIVE-MOVE-EXECUTION-KERNEL-LOCK" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
