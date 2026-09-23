from pathlib import Path


def test_phase21j_telemetry_grounded_voice_bridge_doc_lock_exists():
    path = Path("docs/rfc/aion_phase21j_telemetry_grounded_voice_bridge_lock.tex")
    text = path.read_text(encoding="utf-8")

    assert "AION Phase 21J: Telemetry-Grounded Voice Bridge Lock" in text
    assert "HexCore + M(t) + TrialEvidence" in text
    assert "uses\\_hexcore\\_telemetry" in text
    assert "uses\\_llm\\_shortcut = false" in text
    assert "operational self-measurement" in text
    assert "Lock ID: AION-PHASE21J-TELEMETRY-GROUNDED-VOICE-BRIDGE-LOCK" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
