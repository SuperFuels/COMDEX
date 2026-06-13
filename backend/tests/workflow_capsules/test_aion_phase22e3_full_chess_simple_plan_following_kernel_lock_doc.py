from pathlib import Path


def test_phase22e3_lock_doc_exists_and_names_plan_following():
    path = Path("docs/rfc/aion_phase22e3_full_chess_simple_plan_following_kernel_lock.tex")
    assert path.exists()

    text = path.read_text(encoding="utf-8")
    assert "Phase 22E.3" in text
    assert "Simple Plan Formation" in text
    assert "Plan Following" in text
    assert "stop promotion" in text
    assert "develop pieces" in text
    assert "Stockfish" in text
    assert "LLM" in text
