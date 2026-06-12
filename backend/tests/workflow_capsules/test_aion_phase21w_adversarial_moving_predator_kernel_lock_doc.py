from pathlib import Path


def test_phase21w_adversarial_moving_predator_doc_lock_exists():
    path = Path("docs/rfc/aion_phase21w_adversarial_moving_predator_kernel_lock.tex")
    text = path.read_text(encoding="utf-8")

    assert "AION Phase 21W: Adversarial Moving Hazard / Predator Kernel Lock" in text
    assert "agent\\_state + predator\\_state" in text
    assert "predicted\\_intercept" in text
    assert "before\\_impact\\_avoidance" in text
    assert "predator\\_avoided\\_before\\_impact" in text
    assert "uses\\_adversarial\\_moving\\_hazard" in text
    assert "uses\\_llm\\_shortcut = false" in text
    assert "Lock ID: AION-PHASE21W-ADVERSARIAL-MOVING-PREDATOR-KERNEL-LOCK" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
