from pathlib import Path


def test_phase22e42_lock_doc_exists_and_names_scope_guard():
    path = Path("docs/rfc/aion_phase22e42_full_chess_passed_pawn_intent_scope_guard_kernel_lock.tex")
    assert path.exists()

    text = path.read_text(encoding="utf-8")
    assert "Phase 22E.42" in text
    assert "Passed Pawn Intent Scope Guard" in text
    assert "h1h4" in text
    assert "convert_passed_pawn" in text
    assert "Stockfish" in text
    assert "LLM" in text
