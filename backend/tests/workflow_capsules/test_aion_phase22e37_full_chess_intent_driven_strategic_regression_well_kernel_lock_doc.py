from pathlib import Path


def test_phase22e37_lock_doc_exists_and_names_intent_integration():
    path = Path("docs/rfc/aion_phase22e37_full_chess_intent_driven_strategic_regression_well_kernel_lock.tex")
    assert path.exists()

    text = path.read_text(encoding="utf-8")
    assert "Phase 22E.37" in text
    assert "Intent Driver" in text
    assert "Strategic Regression Well" in text
    assert "opening drift" in text
    assert "h2h4" in text
    assert "Stockfish" in text
    assert "LLM" in text
