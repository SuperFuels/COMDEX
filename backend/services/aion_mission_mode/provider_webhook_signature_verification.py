"""
AION Phase 20H.7 — Provider Webhook Signature Handshakes + Cryptographic Vault Key Verification

Purpose:
- Prove inbound webhook/callback payloads are genuinely signed by the expected provider.
- Bind signature verification to vault-scoped public/secret references.
- Prevent unsigned, stale, replayed, provider-mismatched, algorithm-mismatched or tampered payloads.
- Keep raw webhook signing secrets out of model-visible and runtime-visible payloads.
"""

from __future__ import annotations

from hashlib import sha256, sha512
import hmac
import json
from typing import Any


VALID_SIGNATURE_ALGORITHMS = {
    "hmac_sha256",
    "hmac_sha512",
    "static_test_signature",
}

VALID_SIGNATURE_HEADER_TYPES = {
    "stripe_signature",
    "github_signature_256",
    "generic_hmac_signature",
    "jws_detached",
    "provider_test_signature",
}

FORBIDDEN_VISIBLE_SECRET_KEYS = {
    "webhook_secret",
    "signing_secret",
    "private_key",
    "api_key",
    "access_token",
    "refresh_token",
    "session_token",
}


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _hash(value: Any) -> str:
    return "sha256:" + sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _raw_hash(raw: str) -> str:
    return "sha256:" + sha256(raw.encode("utf-8")).hexdigest()


def canonical_payload_bytes(payload: dict[str, Any]) -> bytes:
    return _canonical_json(payload).encode("utf-8")


def create_vault_signature_key_reference(
    *,
    business_id: str,
    provider: str,
    credential_scope: str,
    vault_key_id: str,
    algorithm: str,
    signature_header_type: str,
    key_version: str,
    secret_material_visible: bool = False,
) -> dict[str, Any]:
    if algorithm not in VALID_SIGNATURE_ALGORITHMS:
        raise ValueError(f"Unknown signature algorithm: {algorithm}")
    if signature_header_type not in VALID_SIGNATURE_HEADER_TYPES:
        raise ValueError(f"Unknown signature header type: {signature_header_type}")
    if secret_material_visible:
        raise ValueError("Webhook signature secret material cannot be model/runtime visible")

    ref = {
        "schema_version": "aion.provider_signature_key_reference.v0",
        "business_id": business_id,
        "provider": provider,
        "credential_scope": credential_scope,
        "vault_key_id": vault_key_id,
        "algorithm": algorithm,
        "signature_header_type": signature_header_type,
        "key_version": key_version,
        "secret_material_visible": False,
        "vault_signature_key_ref_hash": "",
    }
    ref["vault_signature_key_ref_hash"] = _hash(
        {k: v for k, v in ref.items() if k != "vault_signature_key_ref_hash"}
    )
    return ref


def sign_test_payload(
    *,
    payload: dict[str, Any],
    secret: str,
    algorithm: str = "hmac_sha256",
) -> str:
    body = canonical_payload_bytes(payload)
    if algorithm == "hmac_sha256":
        return "sha256=" + hmac.new(secret.encode("utf-8"), body, sha256).hexdigest()
    if algorithm == "hmac_sha512":
        return "sha512=" + hmac.new(secret.encode("utf-8"), body, sha512).hexdigest()
    if algorithm == "static_test_signature":
        return "testsig:" + sha256(body + secret.encode("utf-8")).hexdigest()
    raise ValueError(f"Unsupported test signing algorithm: {algorithm}")


def _verify_signature(
    *,
    payload: dict[str, Any],
    signature_header: str,
    secret_lookup_value: str,
    algorithm: str,
) -> bool:
    expected = sign_test_payload(
        payload=payload,
        secret=secret_lookup_value,
        algorithm=algorithm,
    )
    return hmac.compare_digest(expected, signature_header)


def assert_no_visible_secret_material(record: dict[str, Any]) -> None:
    for key, value in record.items():
        if key in FORBIDDEN_VISIBLE_SECRET_KEYS and value not in (None, "", "[REDACTED]"):
            raise ValueError(f"Visible secret material rejected: {key}")
        if isinstance(value, dict):
            assert_no_visible_secret_material(value)


def verify_provider_webhook_signature(
    *,
    mission_id: str,
    mission_run_id: str,
    business_id: str,
    provider: str,
    callback_url_id: str,
    payload: dict[str, Any],
    signature_header: str | None,
    vault_key_reference: dict[str, Any],
    vault_secret_lookup_value: str,
    timestamp: float,
    expected_provider: str,
    expected_business_id: str,
    max_age_seconds: float,
    now: float,
    seen_signature_hashes: list[str] | None = None,
) -> dict[str, Any]:
    seen_signature_hashes = seen_signature_hashes or []
    reasons: list[str] = []

    assert_no_visible_secret_material(vault_key_reference)

    payload_body_hash = _raw_hash(_canonical_json(payload))
    signature_header_hash = _raw_hash(signature_header or "")

    if not signature_header:
        reasons.append("missing_signature_header")

    if provider != expected_provider:
        reasons.append("provider_mismatch")

    if business_id != expected_business_id:
        reasons.append("business_mismatch")

    if vault_key_reference.get("provider") != expected_provider:
        reasons.append("vault_provider_mismatch")

    if vault_key_reference.get("business_id") != expected_business_id:
        reasons.append("vault_business_mismatch")

    algorithm = vault_key_reference.get("algorithm")
    if algorithm not in VALID_SIGNATURE_ALGORITHMS:
        reasons.append("unsupported_signature_algorithm")

    if now - timestamp > max_age_seconds:
        reasons.append("signature_timestamp_expired")

    if timestamp > now + 5:
        reasons.append("signature_timestamp_from_future")

    replay_preimage = {
        "provider": provider,
        "callback_url_id": callback_url_id,
        "payload_body_hash": payload_body_hash,
        "signature_header_hash": signature_header_hash,
        "timestamp": timestamp,
        "vault_signature_key_ref_hash": vault_key_reference.get("vault_signature_key_ref_hash"),
    }
    signature_event_hash = _hash(replay_preimage)

    if signature_event_hash in seen_signature_hashes:
        reasons.append("signature_replay_detected")

    signature_valid = False
    if signature_header and algorithm in VALID_SIGNATURE_ALGORITHMS and not any(
        reason in reasons
        for reason in [
            "provider_mismatch",
            "business_mismatch",
            "vault_provider_mismatch",
            "vault_business_mismatch",
            "unsupported_signature_algorithm",
        ]
    ):
        signature_valid = _verify_signature(
            payload=payload,
            signature_header=signature_header,
            secret_lookup_value=vault_secret_lookup_value,
            algorithm=algorithm,
        )
        if not signature_valid:
            reasons.append("signature_verification_failed")

    allowed = not reasons

    result = {
        "schema_version": "aion.provider_webhook_signature_assertion.v0",
        "mission_id": mission_id,
        "mission_run_id": mission_run_id,
        "business_id": business_id,
        "provider": provider,
        "callback_url_id": callback_url_id,
        "payload_body_hash": payload_body_hash,
        "signature_header_hash": signature_header_hash,
        "vault_signature_key_ref_hash": vault_key_reference.get("vault_signature_key_ref_hash"),
        "algorithm": algorithm,
        "timestamp": timestamp,
        "max_age_seconds": max_age_seconds,
        "signature_event_hash": signature_event_hash,
        "signature_valid": signature_valid,
        "allowed": allowed,
        "signature_state": "signature_verified" if allowed else "signature_quarantined",
        "reasons": reasons,
        "signature_assertion_hash": "",
    }
    result["signature_assertion_hash"] = _hash(
        {k: v for k, v in result.items() if k != "signature_assertion_hash"}
    )
    return result


def bind_signature_to_callback_ingress(
    *,
    signature_assertion: dict[str, Any],
    callback_ingress_assertion: dict[str, Any],
) -> dict[str, Any]:
    reasons: list[str] = []

    if not signature_assertion.get("allowed"):
        reasons.append("signature_assertion_not_allowed")

    if not callback_ingress_assertion.get("allowed"):
        reasons.append("callback_ingress_not_allowed")

    if signature_assertion.get("mission_id") != callback_ingress_assertion.get("mission_id"):
        reasons.append("mission_mismatch")

    if signature_assertion.get("mission_run_id") != callback_ingress_assertion.get("mission_run_id"):
        reasons.append("mission_run_mismatch")

    if signature_assertion.get("provider") != callback_ingress_assertion.get("provider"):
        reasons.append("provider_mismatch")

    allowed = not reasons

    result = {
        "schema_version": "aion.provider_signature_callback_binding.v0",
        "mission_id": signature_assertion.get("mission_id"),
        "mission_run_id": signature_assertion.get("mission_run_id"),
        "provider": signature_assertion.get("provider"),
        "signature_assertion_hash": signature_assertion.get("signature_assertion_hash"),
        "callback_ingress_assertion_hash": callback_ingress_assertion.get("ingress_assertion_hash"),
        "allowed": allowed,
        "binding_state": "signature_callback_binding_verified" if allowed else "signature_callback_binding_blocked",
        "reasons": reasons,
        "binding_hash": "",
    }
    result["binding_hash"] = _hash({k: v for k, v in result.items() if k != "binding_hash"})
    return result


def summarize_signature_assertions(
    *,
    mission_id: str,
    mission_run_id: str,
    assertions: list[dict[str, Any]],
) -> dict[str, Any]:
    blocked = [item for item in assertions if not item["allowed"]]
    allowed = [item for item in assertions if item["allowed"]]

    result = {
        "schema_version": "aion.provider_signature_summary.v0",
        "mission_id": mission_id,
        "mission_run_id": mission_run_id,
        "allowed_count": len(allowed),
        "blocked_count": len(blocked),
        "blocked_reasons": sorted({reason for item in blocked for reason in item["reasons"]}),
        "assertion_hashes": sorted(item["signature_assertion_hash"] for item in assertions),
        "runtime_state": "provider_signature_clear" if not blocked else "provider_signature_quarantine",
        "summary_hash": "",
    }
    result["summary_hash"] = _hash({k: v for k, v in result.items() if k != "summary_hash"})
    return result
