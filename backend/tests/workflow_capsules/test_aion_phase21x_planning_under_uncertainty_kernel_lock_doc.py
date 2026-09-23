from pathlib import Path


def test_phase21x_planning_under_uncertainty_doc_lock_exists():
    path = Path("docs/rfc/aion_phase21x_planning_under_uncertainty_kernel_lock.tex")
    text = path.read_text(encoding="utf-8")

    assert "AION Phase 21X: Planning Under Uncertainty Kernel Lock" in text
    assert "unknown\\_entity" in text
    assert "uncertainty\\_score" in text
    assert "cautious\\_observation" in text
    assert "risk\\_update" in text
    assert "avoided\\_overconfident\\_action" in text
    assert "gathered\\_information\\_safely" in text
    assert "uses\\_llm\\_shortcut = false" in text
    assert "Lock ID: AION-PHASE21X-PLANNING-UNDER-UNCERTAINTY-KERNEL-LOCK" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
