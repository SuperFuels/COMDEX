from pathlib import Path


def test_phase22a_general_game_adapter_doc_lock_exists():
    path = Path("docs/rfc/aion_phase22a_general_game_adapter_lock.tex")
    text = path.read_text(encoding="utf-8")

    assert "AION Phase 22A: General Game Adapter Lock" in text
    assert "game\\_id" in text
    assert "game\\_type" in text
    assert "legal\\_actions" in text
    assert "threats" in text
    assert "uncertainty" in text
    assert "adapter\\_trace\\_hash" in text
    assert "uses\\_llm\\_shortcut = false" in text
    assert "Lock ID: AION-PHASE22A-GENERAL-GAME-ADAPTER-LOCK" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
