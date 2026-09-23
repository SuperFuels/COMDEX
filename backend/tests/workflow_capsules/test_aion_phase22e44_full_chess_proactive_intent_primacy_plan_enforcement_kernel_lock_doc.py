from pathlib import Path


def test_phase22e44_lock_doc_exists_and_names_proactive_primacy():
    path = Path("docs/rfc/aion_phase22e44_full_chess_proactive_intent_primacy_plan_enforcement_kernel_lock.tex")
    assert path.exists()

    text = path.read_text(encoding="utf-8")
    assert "Phase 22E.44" in text
    assert "Proactive Intent Primacy" in text
    assert "passive drift" in text
    assert "22E.44" in text
    assert "Stockfish" in text
    assert "LLM" in text
