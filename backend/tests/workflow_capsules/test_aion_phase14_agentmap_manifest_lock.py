from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

TARGET_FILES = [
    "backend/modules/aion_gateway/agentmap_manifest.py",
]


def _text(path: str) -> str:
    return (ROOT / path).read_text().lower()


def test_phase14_agentmap_manifest_file_exists():
    for path in TARGET_FILES:
        assert (ROOT / path).exists(), path


def test_phase14_agentmap_manifest_defines_machine_metadata_contract():
    text = _text("backend/modules/aion_gateway/agentmap_manifest.py")

    for term in [
        "agentmap",
        "agentmap_version",
        "business_id",
        "business_name",
        "vertical_key",
        "human_seo_metadata",
        "machine_a2a_metadata",
        "capabilities",
        "availability",
        "accepted_protocols",
        "authentication",
        "metadata_hash",
    ]:
        assert term in text


def test_phase14_agentmap_manifest_keeps_human_and_machine_metadata_separate():
    text = _text("backend/modules/aion_gateway/agentmap_manifest.py")

    assert "meta_description" in text
    assert "machine_description" in text
    assert "human_seo_metadata" in text
    assert "machine_a2a_metadata" in text


def test_phase14_agentmap_manifest_is_deterministic():
    from backend.modules.aion_gateway.agentmap_manifest import build_agentmap_manifest

    first = build_agentmap_manifest(
        business_id="home_fixed",
        business_name="Home Fixed",
        vertical_key="home_repair",
    )
    second = build_agentmap_manifest(
        business_id="home_fixed",
        business_name="Home Fixed",
        vertical_key="home_repair",
    )

    assert first["metadata_hash"] == second["metadata_hash"]
    assert first["agentmap_hash"] == second["agentmap_hash"]


def test_phase14_agentmap_manifest_exposes_preview_only_safety_boundary():
    manifest = __import__(
        "backend.modules.aion_gateway.agentmap_manifest",
        fromlist=["build_agentmap_manifest"],
    ).build_agentmap_manifest(
        business_id="home_fixed",
        business_name="Home Fixed",
        vertical_key="home_repair",
    )

    safety = manifest["safety_profile"]

    assert safety["preview_only"] is True
    assert safety["human_review_required"] is True
    assert safety["would_create_booking"] is False
    assert safety["would_create_payment"] is False
    assert safety["would_create_escrow"] is False
    assert safety["would_send_external_message"] is False
    assert safety["live_chain_write"] is False


def test_phase14_agentmap_manifest_has_no_live_side_effects():
    text = _text("backend/modules/aion_gateway/agentmap_manifest.py")

    for forbidden in [
        "capture_payment(",
        "release_escrow(",
        "create_booking(",
        "send_email(",
        "send_sms(",
        "post_social(",
        "dispatch_job(",
        '"would_create_booking": true',
        '"would_create_payment": true',
        '"would_create_escrow": true',
        '"would_send_external_message": true',
        '"live_chain_write": true',
    ]:
        assert forbidden not in text
