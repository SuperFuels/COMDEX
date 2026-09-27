from __future__ import annotations

from backend.scripts.run_glyphchain_legal_disaster_recovery_exercise import run_exercise


def test_disaster_recovery_exercise_is_content_free_and_passes_all_checks():
    report = run_exercise()

    assert report["result"] == "PASS"
    assert report["report_sha256"]
    assert all(report["checks"].values())
    assert report["backup"]["raw_private_keys_exposed"] is False
    assert report["validator_exercise"]["result"] == "PASS"
    assert report["password_exported"] is False
    assert report["private_keys_exported"] is False
    assert report["legal_document_content_present"] is False
    assert "not application-account recovery" in report["claim_boundary"]
