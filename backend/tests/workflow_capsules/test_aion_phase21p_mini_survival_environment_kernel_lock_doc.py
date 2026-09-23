from pathlib import Path


def test_phase21p_mini_survival_environment_doc_lock_exists():
    path = Path("docs/rfc/aion_phase21p_mini_survival_environment_kernel_lock.tex")
    text = path.read_text(encoding="utf-8")

    assert "AION Phase 21P: Mini Survival Environment Kernel Lock" in text
    assert "state \\rightarrow predict \\rightarrow act" in text
    assert "energy\\_change" in text
    assert "survival\\_score" in text
    assert "final\\_energy" in text
    assert "hazards\\_hit" in text
    assert "uses\\_llm\\_shortcut = false" in text
    assert "Lock ID: AION-PHASE21P-MINI-SURVIVAL-ENVIRONMENT-KERNEL-LOCK" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
