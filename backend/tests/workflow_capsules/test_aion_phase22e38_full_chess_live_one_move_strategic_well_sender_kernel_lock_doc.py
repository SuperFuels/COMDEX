from pathlib import Path


def test_phase22e38_lock_doc_exists_and_names_one_move_sender():
    path = Path("docs/rfc/aion_phase22e38_full_chess_live_one_move_strategic_well_sender_kernel_lock.tex")
    assert path.exists()

    text = path.read_text(encoding="utf-8")
    assert "Phase 22E.38" in text
    assert "Live One-Move Strategic Well Sender" in text
    assert "Phase 22E.37" in text
    assert "g1f3" in text
    assert "h2h4" in text
    assert "one move" in text
    assert "Stockfish" in text
    assert "LLM" in text
