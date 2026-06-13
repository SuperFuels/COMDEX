from pathlib import Path


def test_phase22e6_lock_doc_exists_and_names_long_term_plan_generation():
    path = Path("docs/rfc/aion_phase22e6_full_chess_long_term_plan_generation_kernel_lock.tex")
    assert path.exists()

    text = path.read_text(encoding="utf-8")
    assert "Phase 22E.6" in text
    assert "Long-Term Plan Generation" in text
    assert "multi-stage" in text
    assert "stabilise king" in text
    assert "safer endgame" in text
    assert "Stockfish" in text
    assert "LLM" in text
