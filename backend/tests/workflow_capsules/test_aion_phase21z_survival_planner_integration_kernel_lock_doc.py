from pathlib import Path


def test_phase21z_survival_planner_integration_doc_lock_exists():
    path = Path("docs/rfc/aion_phase21z_survival_planner_integration_kernel_lock.tex")
    text = path.read_text(encoding="utf-8")

    assert "AION Phase 21Z: Survival Planner Integration Kernel Lock" in text
    assert "classify\\_danger" in text
    assert "simulate\\_future" in text
    assert "predict\\_moving\\_threat" in text
    assert "handle\\_uncertainty" in text
    assert "generate\\_plan" in text
    assert "proof\\_hash" in text
    assert "planner\\_receipt\\_hash" in text
    assert "uses\\_llm\\_shortcut = false" in text
    assert "Lock ID: AION-PHASE21Z-SURVIVAL-PLANNER-INTEGRATION-KERNEL-LOCK" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
