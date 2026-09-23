from pathlib import Path


def test_phase22e21_lock_doc_exists_and_names_override_live_sender():
    path = Path("docs/rfc/aion_phase22e21_full_chess_queen_endgame_override_live_sender_kernel_lock.tex")
    assert path.exists()

    text = path.read_text(encoding="utf-8")
    assert "Phase 22E.21" in text
    assert "Queen Endgame Override Live Sender" in text
    assert "22E.20" in text
    assert "22E.16" in text
    assert "queen endgame" in text
    assert "live sender" in text
    assert "Stockfish" in text
    assert "LLM" in text
