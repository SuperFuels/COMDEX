from pathlib import Path


def test_phase22e28_lock_doc_exists_and_names_one_ply_blunder_guard():
    path = Path("docs/rfc/aion_phase22e28_full_chess_one_ply_blunder_guard_kernel_lock.tex")
    assert path.exists()

    text = path.read_text(encoding="utf-8")
    assert "Phase 22E.28" in text
    assert "One-Ply Blunder Guard" in text
    assert "catastrophic opponent reply" in text
    assert "safe_to_send" in text
    assert "Stockfish" in text
    assert "LLM" in text
