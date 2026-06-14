from pathlib import Path


def test_phase22e55_documentation_lock_exists_and_names_boundaries():
    doc = Path("docs/rfc/aion_phase22e55_full_chess_monte_carlo_policy_value_seed_kernel_lock.tex")
    assert doc.exists()
    text = doc.read_text(encoding="utf-8")

    assert "Phase 22E.55" in text
    assert "Monte Carlo Search Skeleton" in text
    assert "Self-Play Policy-Value Seed" in text
    assert "does not call Stockfish" in text
    assert "does not use LLM move judgement" in text
    assert "does not use Lichess analysis" in text
    assert "Lock ID: AION-PHASE22E55-MONTE-CARLO-POLICY-VALUE-SEED" in text
