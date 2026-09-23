from pathlib import Path


def test_phase22e16_lock_doc_exists_and_names_authorized_sender():
    path = Path("docs/rfc/aion_phase22e16_full_chess_live_level2_one_move_authorized_sender_kernel_lock.tex")
    assert path.exists()

    text = path.read_text(encoding="utf-8")
    assert "Phase 22E.16" in text
    assert "Live Level-2 One-Move Authorized Sender" in text
    assert "one move" in text
    assert "authorized sender" in text
    assert "real POST" in text
    assert "Stockfish" in text
    assert "LLM" in text
