from pathlib import Path


def test_phase21r_survival_transfer_generalisation_doc_lock_exists():
    path = Path("docs/rfc/aion_phase21r_survival_transfer_generalisation_kernel_lock.tex")
    text = path.read_text(encoding="utf-8")

    assert "AION Phase 21R: Survival Transfer and New World Generalisation Kernel Lock" in text
    assert "old\\_hazard\\_memory \\rightarrow hazard\\_concept" in text
    assert "new\\_hazard\\_positions" in text
    assert "concept\\_generalised" in text
    assert "uses\\_hazard\\_concept\\_transfer" in text
    assert "uses\\_llm\\_shortcut = false" in text
    assert "Lock ID: AION-PHASE21R-SURVIVAL-TRANSFER-GENERALISATION-KERNEL-LOCK" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
