from pathlib import Path


def test_phase21i_self_improvement_trial_loop_doc_lock_exists():
    path = Path("docs/rfc/aion_phase21i_self_improvement_trial_loop_lock.tex")
    text = path.read_text(encoding="utf-8")

    assert "AION Phase 21I: Self-Improvement Trial Loop Lock" in text
    assert "attempt \\rightarrow score" in text
    assert "improvement\\_delta" in text
    assert "equilibrium\\_reached" in text
    assert "operational self-improvement" in text
    assert "Lock ID: AION-PHASE21I-SELF-IMPROVEMENT-TRIAL-LOOP-LOCK" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
