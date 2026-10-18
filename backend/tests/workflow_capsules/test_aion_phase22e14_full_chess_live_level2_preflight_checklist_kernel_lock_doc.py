from pathlib import Path


def test_phase22e14_lock_doc_exists_and_names_preflight():
    path = Path("docs/rfc/aion_phase22e14_full_chess_live_level2_preflight_checklist_kernel_lock.tex")
    assert path.exists()

    text = path.read_text(encoding="utf-8")
    assert "Phase 22E.14" in text
    assert "Live Level-2 Preflight Checklist" in text
    assert "Level 2" in text
    assert "no live game" in text
    assert "no move POST" in text
    assert "Stockfish" in text
    assert "LLM" in text
