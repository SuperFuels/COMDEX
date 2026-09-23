from pathlib import Path


def test_phase22e34_lock_doc_exists_and_names_regression_well():
    path = Path("docs/rfc/aion_phase22e34_full_chess_strategic_regression_well_optimiser_kernel_lock.tex")
    assert path.exists()

    text = path.read_text(encoding="utf-8")
    assert "Phase 22E.34" in text
    assert "Strategic Regression Well Optimiser" in text
    assert "safe_to_send" in text
    assert "winning basin" in text
    assert "Stockfish" in text
    assert "LLM" in text
