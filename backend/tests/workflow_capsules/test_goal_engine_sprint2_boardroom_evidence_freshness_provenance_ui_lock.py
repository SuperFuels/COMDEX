from pathlib import Path


APP = Path("desktop/mac/src/app.js")


def test_boardroom_outcome_evidence_summary_shows_freshness_and_provenance_fields():
    text = APP.read_text()

    assert "Evidence Freshness" in text
    assert "Evidence Provenance" in text
    assert "source_connector" in text
    assert "source_ref" in text
    assert "confidence" in text
    assert "verified" in text


def test_boardroom_outcome_evidence_summary_reads_validator_validations():
    text = APP.read_text()

    assert "validations" in text
    assert "validation.evidence" in text
    assert "evidence_source_summary" in text


def test_boardroom_outcome_evidence_summary_explains_supporting_source():
    text = APP.read_text()

    assert "Supporting evidence" in text
    assert "Blocked evidence" in text
    assert "Manual confirmation" in text


def test_boardroom_outcome_evidence_summary_keeps_missing_evidence_warning():
    text = APP.read_text()

    assert "Missing evidence" in text
    assert "outcome_success_requires_evidence" in text
