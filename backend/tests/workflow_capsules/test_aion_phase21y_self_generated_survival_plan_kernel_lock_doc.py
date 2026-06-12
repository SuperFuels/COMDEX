from pathlib import Path


def test_phase21y_self_generated_survival_plan_doc_lock_exists():
    path = Path("docs/rfc/aion_phase21y_self_generated_survival_plan_kernel_lock.tex")
    text = path.read_text(encoding="utf-8")

    assert "AION Phase 21Y: Self-Generated Survival Plan Kernel Lock" in text
    assert "plan\\_steps" in text
    assert "hazard\\_labels" in text
    assert "uncertainty\\_labels" in text
    assert "fallback\\_route" in text
    assert "plan\\_revision\\_count" in text
    assert "uses\\_llm\\_shortcut = false" in text
    assert "Lock ID: AION-PHASE21Y-SELF-GENERATED-SURVIVAL-PLAN-KERNEL-LOCK" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
