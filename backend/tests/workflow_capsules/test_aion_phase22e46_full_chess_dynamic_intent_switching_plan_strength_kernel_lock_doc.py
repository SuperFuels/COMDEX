from pathlib import Path


def test_phase22e46_lock_doc_exists_and_names_dynamic_intent_switching():
    path = Path("docs/rfc/aion_phase22e46_full_chess_dynamic_intent_switching_plan_strength_kernel_lock.tex")
    assert path.exists()

    text = path.read_text(encoding="utf-8")
    assert "Phase 22E.46" in text
    assert "Dynamic Intent Switching" in text
    assert "plan strength" in text
    assert "22E.46" in text
    assert "Stockfish" in text
    assert "LLM" in text
