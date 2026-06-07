"""
AION Phase 20H.3 — Browser Worker Sandbox Isolation

Locks:
- Browser workers are mission-scoped and provider-context scoped.
- Browser worker v0 may read, search, extract metadata, stage forms, and capture evidence.
- Browser worker v0 must stop before final submit/payment/publish/deploy/send/booking/legal/identity actions.
- Browser worker never receives raw credentials.
- Browser sessions are isolated by mission/run/provider.
- Kill switch blocks browser worker execution.
"""

from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Literal


BrowserActionMode = Literal[
    "read_page",
    "search",
    "extract_metadata",
    "fill_form_staged",
    "prepare_checkout",
    "prepare_deploy",
    "prepare_publish",
    "capture_screenshot",
    "final_submit",
]

ALLOWED_V0_ACTIONS = {
    "read_page",
    "search",
    "extract_metadata",
    "fill_form_staged",
    "prepare_checkout",
    "prepare_deploy",
    "prepare_publish",
    "capture_screenshot",
}

FINAL_SIDE_EFFECT_ACTIONS = {
    "final_submit",
    "final_payment_submit",
    "publish_public_content",
    "production_deploy",
    "send_external_message",
    "create_booking",
    "submit_legal_document",
    "submit_identity_document",
}

VALID_SESSION_STATES = {
    "created",
    "running",
    "waiting_approval",
    "blocked",
    "killed",
    "completed",
}

SECRET_MARKERS = {
    "password",
    "api_key",
    "access_token",
    "refresh_token",
    "session_token",
    "cookie",
    "authorization",
    "payment_token",
    "card_number",
    "cvv",
}


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _hash(value: Any) -> str:
    return "sha256:" + sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _contains_secret_key(value: Any) -> bool:
    if isinstance(value, dict):
        for key, nested in value.items():
            if str(key).lower() in SECRET_MARKERS:
                return True
            if _contains_secret_key(nested):
                return True
    if isinstance(value, list):
        return any(_contains_secret_key(item) for item in value)
    return False


def create_browser_session(
    *,
    mission_id: str,
    mission_run_id: str,
    business_id: str,
    provider: str,
    browser_worker_id: str,
    provider_context_hash: str,
    allowed_domains: list[str],
    kill_switch_active: bool = False,
) -> dict[str, Any]:
    result = {
        "schema_version": "aion.browser_worker_session.v0",
        "mission_id": mission_id,
        "mission_run_id": mission_run_id,
        "business_id": business_id,
        "provider": provider,
        "browser_worker_id": browser_worker_id,
        "provider_context_hash": provider_context_hash,
        "allowed_domains": sorted(set(allowed_domains)),
        "session_state": "killed" if kill_switch_active else "created",
        "kill_switch_active": kill_switch_active,
        "raw_credentials_exposed": False,
        "session_hash": "",
    }
    result["session_hash"] = _hash({k: v for k, v in result.items() if k != "session_hash"})
    return result


def assert_browser_session_scope(
    *,
    session: dict[str, Any],
    mission_id: str,
    mission_run_id: str,
    provider: str,
) -> dict[str, Any]:
    reasons: list[str] = []

    if session["mission_id"] != mission_id:
        reasons.append("browser_session_mission_mismatch")
    if session["mission_run_id"] != mission_run_id:
        reasons.append("browser_session_run_mismatch")
    if session["provider"] != provider:
        reasons.append("browser_session_provider_mismatch")
    if session.get("kill_switch_active") is True or session.get("session_state") == "killed":
        reasons.append("browser_worker_kill_switch_active")
    if session.get("raw_credentials_exposed") is True:
        reasons.append("raw_credentials_exposed")

    allowed = not reasons

    result = {
        "schema_version": "aion.browser_session_scope_assertion.v0",
        "mission_id": mission_id,
        "mission_run_id": mission_run_id,
        "provider": provider,
        "browser_worker_id": session["browser_worker_id"],
        "session_hash": session["session_hash"],
        "scope_allowed": allowed,
        "reasons": reasons,
        "scope_assertion_hash": "",
    }
    result["scope_assertion_hash"] = _hash(
        {k: v for k, v in result.items() if k != "scope_assertion_hash"}
    )
    return result


def evaluate_browser_action(
    *,
    session: dict[str, Any],
    action_type: str,
    target_url: str,
    staged_payload: dict[str, Any] | None = None,
    approval_hash: str | None = None,
    approved_payload_hash: str | None = None,
) -> dict[str, Any]:
    staged_payload = staged_payload or {}
    reasons: list[str] = []

    if session.get("kill_switch_active") is True or session.get("session_state") == "killed":
        reasons.append("browser_worker_kill_switch_active")

    if _contains_secret_key(staged_payload):
        reasons.append("staged_payload_contains_secret_key")

    domain_allowed = any(target_url.startswith(domain) for domain in session.get("allowed_domains", []))
    if not domain_allowed:
        reasons.append("target_url_outside_allowed_domains")

    is_final_side_effect = action_type in FINAL_SIDE_EFFECT_ACTIONS or action_type == "final_submit"
    staged_payload_hash = _hash(staged_payload)

    if is_final_side_effect:
        reasons.append("browser_worker_v0_final_submit_blocked")
        if not approval_hash:
            reasons.append("missing_approval_hash")
        if approved_payload_hash != staged_payload_hash:
            reasons.append("payload_hash_mismatch")

    if action_type not in ALLOWED_V0_ACTIONS and not is_final_side_effect:
        reasons.append("unsupported_browser_action")

    allowed = not reasons

    result = {
        "schema_version": "aion.browser_worker_action_evaluation.v0",
        "mission_id": session["mission_id"],
        "mission_run_id": session["mission_run_id"],
        "provider": session["provider"],
        "browser_worker_id": session["browser_worker_id"],
        "session_hash": session["session_hash"],
        "action_type": action_type,
        "target_url": target_url,
        "staged_payload_hash": staged_payload_hash,
        "approval_hash": approval_hash,
        "approved_payload_hash": approved_payload_hash,
        "allowed": allowed,
        "browser_state": "allowed" if allowed else "blocked",
        "reasons": reasons,
        "browser_action_hash": "",
    }
    result["browser_action_hash"] = _hash(
        {k: v for k, v in result.items() if k != "browser_action_hash"}
    )
    return result


def create_browser_evidence(
    *,
    action_evaluation: dict[str, Any],
    screenshot_hash: str | None = None,
    page_state_hash: str | None = None,
    dom_summary_hash: str | None = None,
) -> dict[str, Any]:
    if not action_evaluation["allowed"]:
        raise ValueError("Cannot create browser evidence for blocked browser action")

    result = {
        "schema_version": "aion.browser_worker_evidence.v0",
        "mission_id": action_evaluation["mission_id"],
        "mission_run_id": action_evaluation["mission_run_id"],
        "provider": action_evaluation["provider"],
        "browser_worker_id": action_evaluation["browser_worker_id"],
        "action_type": action_evaluation["action_type"],
        "target_url": action_evaluation["target_url"],
        "browser_action_hash": action_evaluation["browser_action_hash"],
        "screenshot_hash": screenshot_hash,
        "page_state_hash": page_state_hash,
        "dom_summary_hash": dom_summary_hash,
        "evidence_hash": "",
    }
    result["evidence_hash"] = _hash({k: v for k, v in result.items() if k != "evidence_hash"})
    return result


def transition_browser_session(
    *,
    session: dict[str, Any],
    next_state: str,
    reason: str,
) -> dict[str, Any]:
    if next_state not in VALID_SESSION_STATES:
        raise ValueError(f"Unknown browser session state: {next_state}")

    transitioned = dict(session)
    transitioned["session_state"] = next_state
    transitioned["transition_reason"] = reason
    transitioned.pop("session_hash", None)
    transitioned["session_hash"] = _hash(
        {k: v for k, v in transitioned.items() if k != "session_hash"}
    )
    return transitioned


def kill_browser_session(
    *,
    session: dict[str, Any],
    reason: str,
) -> dict[str, Any]:
    killed = dict(session)
    killed["kill_switch_active"] = True
    killed["session_state"] = "killed"
    killed["kill_reason"] = reason
    killed.pop("session_hash", None)
    killed["session_hash"] = _hash({k: v for k, v in killed.items() if k != "session_hash"})
    return killed
