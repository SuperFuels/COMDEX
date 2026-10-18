from pathlib import Path


def test_phase21v_hazard_semantics_threat_model_doc_lock_exists():
    path = Path("docs/rfc/aion_phase21v_hazard_semantics_threat_model_kernel_lock.tex")
    text = path.read_text(encoding="utf-8")

    assert "AION Phase 21V: Hazard Semantics and Threat Model Kernel Lock" in text
    assert "threat\\_type" in text
    assert "danger\\_target" in text
    assert "danger\\_horizon" in text
    assert "semantic\\_avoidance" in text
    assert "uses\\_hazard\\_semantics" in text
    assert "uses\\_llm\\_shortcut = false" in text
    assert "Lock ID: AION-PHASE21V-HAZARD-SEMANTICS-THREAT-MODEL-KERNEL-LOCK" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
