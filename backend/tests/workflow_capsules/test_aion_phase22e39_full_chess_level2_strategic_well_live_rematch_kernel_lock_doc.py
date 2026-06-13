from pathlib import Path


def test_phase22e39_lock_doc_exists_and_names_full_live_rematch():
    path = Path("docs/rfc/aion_phase22e39_full_chess_level2_strategic_well_live_rematch_kernel_lock.tex")
    assert path.exists()

    text = path.read_text(encoding="utf-8")
    assert "Phase 22E.39" in text
    assert "Full Live Level-2 Strategic Well Rematch" in text
    assert "Phase 22E.38" in text
    assert "Phase 22E.25" in text
    assert "g1f3" in text
    assert "h2h4" in text
    assert "Stockfish" in text
    assert "LLM" in text
