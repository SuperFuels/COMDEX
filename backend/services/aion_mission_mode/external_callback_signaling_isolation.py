"""
AION Phase 20H.6 — External Webhook Callbacks + WebRTC Signaling Isolation

Locks:
- External callbacks are not trusted just because they reach AION.
- Webhook/provider callback ingress must bind provider, mission, run, action, nonce and staged state.
- Unknown callbacks are quarantined.
- Replay callbacks are rejected.
- Callback payload hash must match expected payload hash when expected.
- WebRTC/socket/signaling channels must be scoped to mission/run/provider/session.
- Signaling messages cannot mutate mission memory or commit external actions directly.
"""

from __future__ import annotations

from hashlib import sha256
import json
from typing import Any


VALID_CALLBACK_TYPES = {
    "domain_purchase_callback",
    "deployment_callback",
    "payment_intent_callback",
    "oauth_callback",
    "ad_campaign_callback",
    "email_delivery_callback",
    "booking_callback",
    "provider_status_callback",
}

VALID_SIGNAL_TYPES = {
    "browser_worker_heartbeat",
    "browser_worker_screenshot_ready",
    "provider_socket_status",
    "webrtc_connection_state",
    "staged_state_update",
    "non_mutating_progress_update",
}

FORBIDDEN_CALLBACK_MUTATIONS = {
    "commit_external_action",
    "mutate_business_memory",
    "publish_content",
    "send_customer_message",
    "capture_payment",
    "deploy_to_production",
    "create_booking",
    "connect_dns",
}

FORBIDDEN_SIGNAL_MUTATIONS = {
    "commit_external_action",
    "approve_payload",
    "mutate_memory",
    "write_business_container",
    "send_message",
    "make_payment",
    "deploy",
}


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _hash(value: Any) -> str:
    return "sha256:" + sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def payload_hash(payload: dict[str, Any]) -> str:
    return _hash(payload)


def create_callback_contract(
    *,
    mission_id: str,
    mission_run_id: str,
    business_id: str,
    provider: str,
    action_type: str,
    callback_type: str,
    callback_url_id: str,
    expected_payload_hash: str | None,
    staged_state_hash: str | None,
    provider_context_hash: str,
    nonce: str,
    expires_at: float,
) -> dict[str, Any]:
    if callback_type not in VALID_CALLBACK_TYPES:
        raise ValueError(f"Unknown callback type: {callback_type}")

    contract = {
        "schema_version": "aion.external_callback_contract.v0",
        "mission_id": mission_id,
        "mission_run_id": mission_run_id,
        "business_id": business_id,
        "provider": provider,
        "action_type": action_type,
        "callback_type": callback_type,
        "callback_url_id": callback_url_id,
        "expected_payload_hash": expected_payload_hash,
        "staged_state_hash": staged_state_hash,
        "provider_context_hash": provider_context_hash,
        "nonce": nonce,
        "expires_at": expires_at,
        "consumed": False,
        "callback_contract_hash": "",
    }
    contract["callback_contract_hash"] = _hash(
        {k: v for k, v in contract.items() if k != "callback_contract_hash"}
    )
    return contract


def evaluate_callback_ingress(
    *,
    contract: dict[str, Any],
    callback_event: dict[str, Any],
    now: float,
    seen_callback_hashes: list[str] | None = None,
) -> dict[str, Any]:
    seen_callback_hashes = seen_callback_hashes or []
    reasons: list[str] = []

    incoming_payload = callback_event.get("payload", {})
    incoming_payload_hash = payload_hash(incoming_payload)

    callback_event_hash = _hash(
        {
            "contract_hash": contract["callback_contract_hash"],
            "provider": callback_event.get("provider"),
            "callback_type": callback_event.get("callback_type"),
            "callback_url_id": callback_event.get("callback_url_id"),
            "nonce": callback_event.get("nonce"),
            "payload_hash": incoming_payload_hash,
        }
    )

    if callback_event_hash in seen_callback_hashes:
        reasons.append("callback_replay_detected")

    if contract.get("consumed") is True:
        reasons.append("callback_contract_already_consumed")

    if now > float(contract["expires_at"]):
        reasons.append("callback_contract_expired")

    if callback_event.get("provider") != contract["provider"]:
        reasons.append("provider_mismatch")

    if callback_event.get("mission_id") != contract["mission_id"]:
        reasons.append("mission_mismatch")

    if callback_event.get("mission_run_id") != contract["mission_run_id"]:
        reasons.append("mission_run_mismatch")

    if callback_event.get("callback_type") != contract["callback_type"]:
        reasons.append("callback_type_mismatch")

    if callback_event.get("callback_url_id") != contract["callback_url_id"]:
        reasons.append("callback_url_id_mismatch")

    if callback_event.get("nonce") != contract["nonce"]:
        reasons.append("nonce_mismatch")

    expected_payload_hash = contract.get("expected_payload_hash")
    if expected_payload_hash and incoming_payload_hash != expected_payload_hash:
        reasons.append("callback_payload_hash_mismatch")

    requested_mutation = callback_event.get("requested_mutation")
    if requested_mutation in FORBIDDEN_CALLBACK_MUTATIONS:
        reasons.append("forbidden_callback_mutation_blocked")

    allowed = not reasons

    result = {
        "schema_version": "aion.external_callback_ingress_assertion.v0",
        "mission_id": contract["mission_id"],
        "mission_run_id": contract["mission_run_id"],
        "business_id": contract["business_id"],
        "provider": contract["provider"],
        "action_type": contract["action_type"],
        "callback_type": contract["callback_type"],
        "callback_contract_hash": contract["callback_contract_hash"],
        "callback_event_hash": callback_event_hash,
        "incoming_payload_hash": incoming_payload_hash,
        "expected_payload_hash": expected_payload_hash,
        "allowed": allowed,
        "ingress_state": "callback_ingress_allowed" if allowed else "callback_ingress_quarantined",
        "reasons": reasons,
        "ingress_assertion_hash": "",
    }
    result["ingress_assertion_hash"] = _hash(
        {k: v for k, v in result.items() if k != "ingress_assertion_hash"}
    )
    return result


def consume_callback_contract(
    *,
    contract: dict[str, Any],
    ingress_assertion: dict[str, Any],
    provider_response_hash: str,
    now: float,
) -> dict[str, Any]:
    if not ingress_assertion["allowed"]:
        raise ValueError("Cannot consume callback contract for quarantined callback")

    consumed = dict(contract)
    consumed["consumed"] = True
    consumed["consumed_at"] = now
    consumed["ingress_assertion_hash"] = ingress_assertion["ingress_assertion_hash"]
    consumed["provider_response_hash"] = provider_response_hash
    consumed.pop("callback_contract_hash", None)
    consumed["callback_contract_hash"] = _hash(
        {k: v for k, v in consumed.items() if k != "callback_contract_hash"}
    )
    return consumed


def create_signaling_contract(
    *,
    mission_id: str,
    mission_run_id: str,
    business_id: str,
    provider: str,
    browser_worker_id: str,
    browser_session_hash: str,
    signaling_channel_id: str,
    allowed_signal_types: list[str],
    expires_at: float,
) -> dict[str, Any]:
    unknown = sorted(set(allowed_signal_types) - VALID_SIGNAL_TYPES)
    if unknown:
        raise ValueError(f"Unknown signal types: {unknown}")

    contract = {
        "schema_version": "aion.signaling_contract.v0",
        "mission_id": mission_id,
        "mission_run_id": mission_run_id,
        "business_id": business_id,
        "provider": provider,
        "browser_worker_id": browser_worker_id,
        "browser_session_hash": browser_session_hash,
        "signaling_channel_id": signaling_channel_id,
        "allowed_signal_types": sorted(set(allowed_signal_types)),
        "expires_at": expires_at,
        "signaling_contract_hash": "",
    }
    contract["signaling_contract_hash"] = _hash(
        {k: v for k, v in contract.items() if k != "signaling_contract_hash"}
    )
    return contract


def evaluate_signaling_message(
    *,
    contract: dict[str, Any],
    signal_message: dict[str, Any],
    now: float,
) -> dict[str, Any]:
    reasons: list[str] = []

    signal_payload = signal_message.get("payload", {})
    signal_payload_hash = payload_hash(signal_payload)

    if now > float(contract["expires_at"]):
        reasons.append("signaling_contract_expired")

    if signal_message.get("mission_id") != contract["mission_id"]:
        reasons.append("mission_mismatch")

    if signal_message.get("mission_run_id") != contract["mission_run_id"]:
        reasons.append("mission_run_mismatch")

    if signal_message.get("provider") != contract["provider"]:
        reasons.append("provider_mismatch")

    if signal_message.get("browser_worker_id") != contract["browser_worker_id"]:
        reasons.append("browser_worker_mismatch")

    if signal_message.get("browser_session_hash") != contract["browser_session_hash"]:
        reasons.append("browser_session_mismatch")

    if signal_message.get("signaling_channel_id") != contract["signaling_channel_id"]:
        reasons.append("signaling_channel_mismatch")

    signal_type = signal_message.get("signal_type")
    if signal_type not in contract["allowed_signal_types"]:
        reasons.append("signal_type_not_allowed")

    requested_mutation = signal_message.get("requested_mutation")
    if requested_mutation in FORBIDDEN_SIGNAL_MUTATIONS:
        reasons.append("forbidden_signal_mutation_blocked")

    allowed = not reasons

    result = {
        "schema_version": "aion.signaling_message_assertion.v0",
        "mission_id": contract["mission_id"],
        "mission_run_id": contract["mission_run_id"],
        "provider": contract["provider"],
        "browser_worker_id": contract["browser_worker_id"],
        "browser_session_hash": contract["browser_session_hash"],
        "signaling_channel_id": contract["signaling_channel_id"],
        "signaling_contract_hash": contract["signaling_contract_hash"],
        "signal_type": signal_type,
        "signal_payload_hash": signal_payload_hash,
        "allowed": allowed,
        "signaling_state": "signal_allowed" if allowed else "signal_quarantined",
        "reasons": reasons,
        "signal_assertion_hash": "",
    }
    result["signal_assertion_hash"] = _hash(
        {k: v for k, v in result.items() if k != "signal_assertion_hash"}
    )
    return result


def summarize_callback_and_signal_assertions(
    *,
    mission_id: str,
    mission_run_id: str,
    assertions: list[dict[str, Any]],
) -> dict[str, Any]:
    blocked = [item for item in assertions if not item["allowed"]]
    allowed = [item for item in assertions if item["allowed"]]

    result = {
        "schema_version": "aion.callback_signal_summary.v0",
        "mission_id": mission_id,
        "mission_run_id": mission_run_id,
        "allowed_count": len(allowed),
        "blocked_count": len(blocked),
        "blocked_reasons": sorted({reason for item in blocked for reason in item["reasons"]}),
        "assertion_hashes": sorted(
            item.get("ingress_assertion_hash") or item.get("signal_assertion_hash")
            for item in assertions
        ),
        "runtime_state": "callback_signal_quarantine" if blocked else "callback_signal_clear",
        "summary_hash": "",
    }
    result["summary_hash"] = _hash({k: v for k, v in result.items() if k != "summary_hash"})
    return result
