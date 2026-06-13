from pathlib import Path


def test_phase22e7_lock_doc_exists_and_names_risk_forecasting():
    path = Path("docs/rfc/aion_phase22e7_full_chess_consequence_simulation_risk_forecasting_kernel_lock.tex")
    assert path.exists()

    text = path.read_text(encoding="utf-8")
    assert "Phase 22E.7" in text
    assert "Consequence Simulation" in text
    assert "Risk Forecasting" in text
    assert "failure probability" in text
    assert "fallback" in text
    assert "Stockfish" in text
    assert "LLM" in text
