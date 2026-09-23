from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DOC = ROOT / "docs/rfc/aion_phase14_agentmap_manifest_lock.tex"


def test_phase14_agentmap_manifest_lock_doc_exists():
    assert DOC.exists()


def test_phase14_agentmap_manifest_lock_doc_status_locked():
    text = DOC.read_text().lower()
    assert "status: locked" in text
    assert "agentmap machine metadata manifest" in text


def test_phase14_agentmap_manifest_lock_doc_mentions_required_contract_terms():
    text = DOC.read_text().lower()

    for term in [
        "agentmap",
        "metadata_hash",
        "agentmap_hash",
        "human_seo_metadata",
        "machine_a2a_metadata",
        "capabilities",
        "availability",
        "accepted_protocols",
        "authentication",
    ]:
        assert term in text


def test_phase14_agentmap_manifest_lock_doc_mentions_safety_boundary():
    text = DOC.read_text().lower()

    for term in [
        "discovery-only",
        "create bookings",
        "capture payments",
        "release escrow",
        "live chain writes",
    ]:
        assert term in text


def test_phase14_agentmap_manifest_lock_doc_footer():
    text = DOC.read_text()
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text


def test_phase14_agentmap_manifest_lock_doc_validation_command():
    text = DOC.read_text()
    assert "test_aion_phase14_agentmap_manifest_lock.py" in text
