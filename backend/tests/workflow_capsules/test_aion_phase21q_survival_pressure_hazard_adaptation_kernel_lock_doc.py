from pathlib import Path


def test_phase21q_survival_pressure_hazard_adaptation_doc_lock_exists():
    path = Path("docs/rfc/aion_phase21q_survival_pressure_hazard_adaptation_kernel_lock.tex")
    text = path.read_text(encoding="utf-8")

    assert "AION Phase 21Q: Survival Pressure and Hazard Adaptation Kernel Lock" in text
    assert "hazard \\rightarrow damage \\rightarrow memory" in text
    assert "avoidance\\_increase" in text
    assert "hazards\\_hit" in text
    assert "hazard\\_adaptation\\_delta" in text
    assert "known\\_hazards" in text
    assert "uses\\_llm\\_shortcut = false" in text
    assert "Lock ID: AION-PHASE21Q-SURVIVAL-PRESSURE-HAZARD-ADAPTATION-KERNEL-LOCK" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
