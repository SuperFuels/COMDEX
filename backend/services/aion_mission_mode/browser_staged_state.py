"""
AION Phase 20H.4 — Browser Staged State Contract

Locks:
- Browser staged states are hash-bound.
- Staged states expire.
- Staged payload mutation invalidates commit.
- Staged states commit once only.
- Expired/abandoned/committed states cannot execute.
- Approval must bind exact staged payload hash.
"""

from __future__ import annotations

from hashlib import sha256
import json
from typing import Any


VALID_STAGED_STATES = {
    "none",
    "preparing",
    "staged",
    "waiting_approval",
    "expired",
    "committed",
    "abandoned",
}

COMMITTABLE_STATES = {
    "staged",
    "waiting_approval",
}


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _hash(value: Any) -> str:
    return "sha256:" + sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def canonical_payload_hash(payload: dict[str, Any]) -> str:
    return _hash(payload)


def create_staged_browser_state(
    *,
    mission_id: str,
    mission_run_id: str,
    business_id: str,
    provider: str,
    browser_worker_id: str,
    provider_context_hash: str,
    browser_session_hash: str,
    action_type: str,
    target_url: str,
    staged_payload: dict[str, Any],
    staged_state_expires_at: float,
    now: float,
    approval_required: bool = True,
) -> dict[str, Any]:
    staged_payload_hash = canonical_payload_hash(staged_payload)

    state = {
        "schema_version": "aion.browser_staged_state.v0",
        "mission_id": mission_id,
        "mission_run_id": mission_run_id,
        "business_id": business_id,
        "provider": provider,
        "browser_worker_id": browser_worker_id,
        "provider_context_hash": provider_context_hash,
        "browser_session_hash": browser_session_hash,
        "action_type": action_type,
        "target_url": target_url,
        "staged_payload_hash": staged_payload_hash,
        "approval_required": approval_required,
        "staged_state": "expired" if now > staged_state_expires_at else "staged",
        "staged_state_created_at": now,
        "staged_state_expires_at": staged_state_expires_at,
        "committed_at": None,
        "commit_count": 0,
        "requires_restaging": now > staged_state_expires_at,
        "browser_session_staged_state_hash": "",
    }
    state["browser_session_staged_state_hash"] = _hash(
        {k: v for k, v in state.items() if k != "browser_session_staged_state_hash"}
    )
    return state


def transition_staged_state(
    *,
    staged_state: dict[str, Any],
    next_state: str,
    now: float,
    reason: str,
) -> dict[str, Any]:
    if next_state not in VALID_STAGED_STATES:
        raise ValueError(f"Unknown staged state: {next_state}")

    updated = dict(staged_state)
    updated["staged_state"] = next_state
    updated["transitioned_at"] = now
    updated["transition_reason"] = reason

    if next_state == "expired":
        updated["requires_restaging"] = True
    if next_state == "abandoned":
        updated["requires_restaging"] = True

    updated.pop("browser_session_staged_state_hash", None)
    updated["browser_session_staged_state_hash"] = _hash(
        {k: v for k, v in updated.items() if k != "browser_session_staged_state_hash"}
    )
    return updated


def assert_staged_state_commit_allowed(
    *,
    staged_state: dict[str, Any],
    current_payload: dict[str, Any],
    approval_hash: str | None,
    approved_payload_hash: str | None,
    now: float,
) -> dict[str, Any]:
    reasons: list[str] = []

    current_payload_hash = canonical_payload_hash(current_payload)

    if staged_state["staged_state"] not in COMMITTABLE_STATES:
        reasons.append("staged_state_not_committable")

    if now > float(staged_state["staged_state_expires_at"]):
        reasons.append("staged_state_expired")

    if staged_state.get("requires_restaging") is True:
        reasons.append("restaging_required")

    if int(staged_state.get("commit_count", 0)) > 0:
        reasons.append("staged_state_already_committed")

    if current_payload_hash != staged_state["staged_payload_hash"]:
        reasons.append("staged_payload_mutated")

    if staged_state.get("approval_required") is True:
        if not approval_hash:
            reasons.append("missing_approval_hash")
        if not approved_payload_hash:
            reasons.append("missing_approved_payload_hash")
        elif approved_payload_hash != staged_state["staged_payload_hash"]:
            reasons.append("approved_payload_hash_mismatch")

    allowed = not reasons

    result = {
        "schema_version": "aion.browser_staged_commit_assertion.v0",
        "mission_id": staged_state["mission_id"],
        "mission_run_id": staged_state["mission_run_id"],
        "provider": staged_state["provider"],
        "browser_worker_id": staged_state["browser_worker_id"],
        "action_type": staged_state["action_type"],
        "target_url": staged_state["target_url"],
        "browser_session_staged_state_hash": staged_state["browser_session_staged_state_hash"],
        "staged_payload_hash": staged_state["staged_payload_hash"],
        "current_payload_hash": current_payload_hash,
        "approved_payload_hash": approved_payload_hash,
        "approval_hash": approval_hash,
        "now": now,
        "commit_allowed": allowed,
        "gateway_state": "staged_commit_allowed" if allowed else "staged_commit_blocked",
        "reasons": reasons,
        "commit_assertion_hash": "",
    }
    result["commit_assertion_hash"] = _hash(
        {k: v for k, v in result.items() if k != "commit_assertion_hash"}
    )
    return result


def commit_staged_state(
    *,
    staged_state: dict[str, Any],
    commit_assertion: dict[str, Any],
    now: float,
    provider_response_hash: str,
) -> dict[str, Any]:
    if not commit_assertion["commit_allowed"]:
        raise ValueError("Cannot commit blocked staged browser state")

    committed = dict(staged_state)
    committed["staged_state"] = "committed"
    committed["committed_at"] = now
    committed["commit_count"] = int(committed.get("commit_count", 0)) + 1
    committed["provider_response_hash"] = provider_response_hash
    committed["commit_assertion_hash"] = commit_assertion["commit_assertion_hash"]
    committed["requires_restaging"] = False
    committed.pop("browser_session_staged_state_hash", None)
    committed["browser_session_staged_state_hash"] = _hash(
        {k: v for k, v in committed.items() if k != "browser_session_staged_state_hash"}
    )
    return committed


def create_staged_state_receipt(
    *,
    committed_state: dict[str, Any],
) -> dict[str, Any]:
    if committed_state["staged_state"] != "committed":
        raise ValueError("Cannot create staged state receipt for uncommitted state")

    result = {
        "schema_version": "aion.browser_staged_state_receipt.v0",
        "mission_id": committed_state["mission_id"],
        "mission_run_id": committed_state["mission_run_id"],
        "provider": committed_state["provider"],
        "browser_worker_id": committed_state["browser_worker_id"],
        "action_type": committed_state["action_type"],
        "target_url": committed_state["target_url"],
        "staged_payload_hash": committed_state["staged_payload_hash"],
        "commit_assertion_hash": committed_state["commit_assertion_hash"],
        "provider_response_hash": committed_state["provider_response_hash"],
        "committed_state_hash": committed_state["browser_session_staged_state_hash"],
        "receipt_hash": "",
    }
    result["receipt_hash"] = _hash({k: v for k, v in result.items() if k != "receipt_hash"})
    return result
