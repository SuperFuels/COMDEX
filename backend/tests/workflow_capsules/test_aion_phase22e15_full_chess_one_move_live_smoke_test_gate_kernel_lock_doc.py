from pathlib import Path


def test_phase22e15_lock_doc_exists_and_names_one_move_smoke_gate():
    path = Path("docs/rfc/aion_phase22e15_full_chess_one_move_live_smoke_test_gate_kernel_lock.tex")
    assert path.exists()

    text = path.read_text(encoding="utf-8")
    assert "Phase 22E.15" in text
    assert "One-Move Live Smoke Test Gate" in text
    assert "one move" in text
    assert "no move POST" in text
    assert "no live send" in text
    assert "Stockfish" in text
    assert "LLM" in text
