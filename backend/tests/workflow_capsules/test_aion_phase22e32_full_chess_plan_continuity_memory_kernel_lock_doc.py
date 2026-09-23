from pathlib import Path


def test_phase22e32_lock_doc_exists_and_names_plan_continuity():
    path = Path("docs/rfc/aion_phase22e32_full_chess_plan_continuity_memory_kernel_lock.tex")
    assert path.exists()

    text = path.read_text(encoding="utf-8")
    assert "Phase 22E.32" in text
    assert "Plan Continuity Memory" in text
    assert "previous strategic plan" in text
    assert "plan_changed" in text
    assert "Stockfish" in text
    assert "LLM" in text
