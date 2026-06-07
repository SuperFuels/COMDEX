import pytest

from backend.services.aion_mission_mode.provider_webhook_signature_verification import (
    bind_signature_to_callback_ingress,
    create_vault_signature_key_reference,
    sign_test_payload,
    summarize_signature_assertions,
    verify_provider_webhook_signature,
)


SECRET = "whsec_test_secret"


def _payload():
    return {"id": "evt_123", "type": "deployment.ready", "status": "ok"}


def _vault_ref(**kwargs):
    base = dict(
        business_id="business_001",
        provider="vercel",
        credential_scope="webhook:deployment",
        vault_key_id="vault_key_001",
        algorithm="hmac_sha256",
        signature_header_type="generic_hmac_signature",
        key_version="v1",
    )
    base.update(kwargs)
    return create_vault_signature_key_reference(**base)


def _signature(payload=None, secret=SECRET, algorithm="hmac_sha256"):
    return sign_test_payload(payload=payload or _payload(), secret=secret, algorithm=algorithm)


def _verify(**kwargs):
    base = dict(
        mission_id="mission_001",
        mission_run_id="run_001",
        business_id="business_001",
        provider="vercel",
        callback_url_id="callback_001",
        payload=_payload(),
        signature_header=_signature(),
        vault_key_reference=_vault_ref(),
        vault_secret_lookup_value=SECRET,
        timestamp=100.0,
        expected_provider="vercel",
        expected_business_id="business_001",
        max_age_seconds=300.0,
        now=120.0,
    )
    base.update(kwargs)
    return verify_provider_webhook_signature(**base)


def test_phase20h7_vault_key_reference_hash_deterministic() -> None:
    assert _vault_ref()["vault_signature_key_ref_hash"] == _vault_ref()["vault_signature_key_ref_hash"]


def test_phase20h7_unknown_algorithm_rejected() -> None:
    with pytest.raises(ValueError):
        _vault_ref(algorithm="md5")


def test_phase20h7_unknown_signature_header_type_rejected() -> None:
    with pytest.raises(ValueError):
        _vault_ref(signature_header_type="unknown_header")


def test_phase20h7_visible_secret_material_rejected_in_ref_creation() -> None:
    with pytest.raises(ValueError):
        _vault_ref(secret_material_visible=True)


def test_phase20h7_valid_signature_allowed() -> None:
    result = _verify()
    assert result["allowed"] is True
    assert result["signature_valid"] is True
    assert result["signature_state"] == "signature_verified"


def test_phase20h7_missing_signature_header_quarantined() -> None:
    result = _verify(signature_header=None)
    assert result["allowed"] is False
    assert "missing_signature_header" in result["reasons"]


def test_phase20h7_tampered_payload_quarantined() -> None:
    result = _verify(payload={"id": "evt_123", "type": "deployment.ready", "status": "tampered"})
    assert result["allowed"] is False
    assert "signature_verification_failed" in result["reasons"]


def test_phase20h7_wrong_secret_quarantined() -> None:
    result = _verify(vault_secret_lookup_value="wrong_secret")
    assert result["allowed"] is False
    assert "signature_verification_failed" in result["reasons"]


def test_phase20h7_provider_mismatch_quarantined() -> None:
    result = _verify(provider="stripe")
    assert result["allowed"] is False
    assert "provider_mismatch" in result["reasons"]


def test_phase20h7_business_mismatch_quarantined() -> None:
    result = _verify(business_id="business_999")
    assert result["allowed"] is False
    assert "business_mismatch" in result["reasons"]


def test_phase20h7_vault_provider_mismatch_quarantined() -> None:
    result = _verify(vault_key_reference=_vault_ref(provider="stripe"))
    assert result["allowed"] is False
    assert "vault_provider_mismatch" in result["reasons"]


def test_phase20h7_vault_business_mismatch_quarantined() -> None:
    result = _verify(vault_key_reference=_vault_ref(business_id="business_999"))
    assert result["allowed"] is False
    assert "vault_business_mismatch" in result["reasons"]


def test_phase20h7_expired_signature_quarantined() -> None:
    result = _verify(timestamp=1.0, now=500.0, max_age_seconds=300.0)
    assert result["allowed"] is False
    assert "signature_timestamp_expired" in result["reasons"]


def test_phase20h7_future_timestamp_quarantined() -> None:
    result = _verify(timestamp=200.0, now=100.0)
    assert result["allowed"] is False
    assert "signature_timestamp_from_future" in result["reasons"]


def test_phase20h7_replay_signature_quarantined() -> None:
    first = _verify()
    second = _verify(seen_signature_hashes=[first["signature_event_hash"]])
    assert second["allowed"] is False
    assert "signature_replay_detected" in second["reasons"]


def test_phase20h7_signature_assertion_hash_deterministic() -> None:
    assert _verify()["signature_assertion_hash"] == _verify()["signature_assertion_hash"]


def test_phase20h7_hmac_sha512_supported() -> None:
    ref = _vault_ref(algorithm="hmac_sha512")
    sig = _signature(algorithm="hmac_sha512")
    result = _verify(vault_key_reference=ref, signature_header=sig)
    assert result["allowed"] is True


def test_phase20h7_static_test_signature_supported() -> None:
    ref = _vault_ref(algorithm="static_test_signature")
    sig = _signature(algorithm="static_test_signature")
    result = _verify(vault_key_reference=ref, signature_header=sig)
    assert result["allowed"] is True


def test_phase20h7_visible_secret_material_in_reference_rejected() -> None:
    ref = _vault_ref()
    ref["webhook_secret"] = "plaintext_secret"
    with pytest.raises(ValueError):
        _verify(vault_key_reference=ref)


def test_phase20h7_signature_binds_to_callback_ingress() -> None:
    sig = _verify()
    ingress = {
        "allowed": True,
        "mission_id": "mission_001",
        "mission_run_id": "run_001",
        "provider": "vercel",
        "ingress_assertion_hash": "sha256:ingress",
    }
    binding = bind_signature_to_callback_ingress(
        signature_assertion=sig,
        callback_ingress_assertion=ingress,
    )
    assert binding["allowed"] is True


def test_phase20h7_signature_binding_blocks_failed_signature() -> None:
    sig = _verify(signature_header="bad")
    ingress = {
        "allowed": True,
        "mission_id": "mission_001",
        "mission_run_id": "run_001",
        "provider": "vercel",
        "ingress_assertion_hash": "sha256:ingress",
    }
    binding = bind_signature_to_callback_ingress(
        signature_assertion=sig,
        callback_ingress_assertion=ingress,
    )
    assert binding["allowed"] is False
    assert "signature_assertion_not_allowed" in binding["reasons"]


def test_phase20h7_signature_binding_blocks_failed_ingress() -> None:
    sig = _verify()
    ingress = {
        "allowed": False,
        "mission_id": "mission_001",
        "mission_run_id": "run_001",
        "provider": "vercel",
        "ingress_assertion_hash": "sha256:ingress",
    }
    binding = bind_signature_to_callback_ingress(
        signature_assertion=sig,
        callback_ingress_assertion=ingress,
    )
    assert binding["allowed"] is False
    assert "callback_ingress_not_allowed" in binding["reasons"]


def test_phase20h7_summary_quarantines_if_any_blocked() -> None:
    ok = _verify()
    bad = _verify(signature_header="bad")
    summary = summarize_signature_assertions(
        mission_id="mission_001",
        mission_run_id="run_001",
        assertions=[ok, bad],
    )
    assert summary["allowed_count"] == 1
    assert summary["blocked_count"] == 1
    assert summary["runtime_state"] == "provider_signature_quarantine"


def test_phase20h7_summary_hash_deterministic() -> None:
    ok = _verify()
    first = summarize_signature_assertions(
        mission_id="mission_001",
        mission_run_id="run_001",
        assertions=[ok],
    )
    second = summarize_signature_assertions(
        mission_id="mission_001",
        mission_run_id="run_001",
        assertions=[ok],
    )
    assert first["summary_hash"] == second["summary_hash"]
