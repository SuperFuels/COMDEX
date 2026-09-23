from pathlib import Path


def test_phase22e49_lock_doc_exists_and_names_initiative_hygiene():
    path = Path("docs/rfc/aion_phase22e49_full_chess_initiative_hygiene_guard_kernel_lock.tex")
    assert path.exists()

    text = path.read_text(encoding="utf-8")
    assert "Phase 22E.49" in text
    assert "Initiative Hygiene" in text
    assert "h2h4" in text
    assert "g2g4" in text
    assert "Stockfish" in text
    assert "LLM" in text
