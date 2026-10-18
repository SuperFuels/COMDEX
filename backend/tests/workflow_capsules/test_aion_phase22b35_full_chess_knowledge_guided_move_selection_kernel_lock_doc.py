from pathlib import Path


def test_phase22b35_full_chess_knowledge_guided_move_selection_doc_lock_exists():
    path = Path("docs/rfc/aion_phase22b35_full_chess_knowledge_guided_move_selection_kernel_lock.tex")
    text = path.read_text(encoding="utf-8")

    assert "AION Phase 22B.35: Full Chess Knowledge-Guided Move Selection Kernel Lock" in text
    assert "position\\_family" in text
    assert "side\\_to\\_move" in text
    assert "legal\\_candidate\\_count" in text
    assert "knowledge\\_prior\\_count" in text
    assert "avoidance\\_rule\\_count" in text
    assert "selected\\_bestmove" in text
    assert "selected\\_policy" in text
    assert "selected\\_score" in text
    assert "highest\\_penalised\\_move" in text
    assert "candidate\\_scores" in text
    assert "knowledge\\_guided\\_trace\\_hash" in text
    assert "uses\\_llm\\_shortcut = false" in text
    assert "Lock ID: AION-PHASE22B35-FULL-CHESS-KNOWLEDGE-GUIDED-MOVE-SELECTION-KERNEL-LOCK" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
