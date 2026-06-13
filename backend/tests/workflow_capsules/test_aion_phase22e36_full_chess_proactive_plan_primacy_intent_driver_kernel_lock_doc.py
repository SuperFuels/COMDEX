from pathlib import Path


def test_phase22e36_lock_doc_exists_and_names_intent_driver():
    path = Path("docs/rfc/aion_phase22e36_full_chess_proactive_plan_primacy_intent_driver_kernel_lock.tex")
    assert path.exists()

    text = path.read_text(encoding="utf-8")
    assert "Phase 22E.36" in text
    assert "Proactive Plan Primacy" in text
    assert "Intent Driver" in text
    assert "active intent" in text
    assert "emergency override" in text
    assert "Strategic Regression Well" in text
    assert "Stockfish" in text
    assert "LLM" in text
