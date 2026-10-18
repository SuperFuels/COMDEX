from pathlib import Path


def test_phase22e30_lock_doc_exists_and_names_passed_pawn_policy():
    path = Path("docs/rfc/aion_phase22e30_full_chess_passed_pawn_conversion_policy_kernel_lock.tex")
    assert path.exists()

    text = path.read_text(encoding="utf-8")
    assert "Phase 22E.30" in text
    assert "Passed Pawn Conversion Policy" in text
    assert "promote_now" in text
    assert "push_passed_pawn" in text
    assert "Stockfish" in text
    assert "LLM" in text
