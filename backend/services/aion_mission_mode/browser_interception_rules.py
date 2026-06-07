"""
AION Phase 20H.5 — Browser Worker Interception Rules + DOM/Network Mutation Whitelist

Locks:
- Browser workers must intercept network, DOM, popup, download and navigation events.
- Off-domain requests are blocked unless explicitly whitelisted.
- Dangerous HTTP methods are blocked unless approved.
- Hidden submit/payment/publish/deploy mutations are blocked.
- Third-party iframe/script injection is blocked unless whitelisted.
- Every interception decision emits deterministic hashes.
"""

from __future__ import annotations

from hashlib import sha256
import json
from typing import Any


SAFE_HTTP_METHODS = {"GET", "HEAD", "OPTIONS"}
MUTATING_HTTP_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

SAFE_DOM_MUTATIONS = {
    "read_text",
    "read_attribute",
    "focus",
    "scroll",
    "fill_input_staged",
    "select_option_staged",
    "check_box_staged",
    "capture_screenshot",
}

DANGEROUS_DOM_MUTATIONS = {
    "click_submit",
    "click_payment",
    "click_publish",
    "click_deploy",
    "click_send",
    "click_book",
    "upload_identity_document",
    "upload_legal_document",
    "download_file",
    "open_popup",
    "inject_script",
    "create_iframe",
}

VALID_EVENT_TYPES = {
    "network_request",
    "navigation",
    "dom_mutation",
    "popup",
    "download",
    "iframe",
    "script",
}


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _hash(value: Any) -> str:
    return "sha256:" + sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _domain_allowed(url: str, allowed_domains: list[str]) -> bool:
    return any(url.startswith(domain) for domain in allowed_domains)


def create_interception_policy(
    *,
    mission_id: str,
    mission_run_id: str,
    business_id: str,
    provider: str,
    browser_worker_id: str,
    browser_session_hash: str,
    allowed_domains: list[str],
    allowed_iframe_domains: list[str] | None = None,
    allowed_script_domains: list[str] | None = None,
    allow_downloads: bool = False,
    allow_popups: bool = False,
    allow_mutating_methods: bool = False,
) -> dict[str, Any]:
    policy = {
        "schema_version": "aion.browser_interception_policy.v0",
        "mission_id": mission_id,
        "mission_run_id": mission_run_id,
        "business_id": business_id,
        "provider": provider,
        "browser_worker_id": browser_worker_id,
        "browser_session_hash": browser_session_hash,
        "allowed_domains": sorted(set(allowed_domains)),
        "allowed_iframe_domains": sorted(set(allowed_iframe_domains or [])),
        "allowed_script_domains": sorted(set(allowed_script_domains or [])),
        "allow_downloads": allow_downloads,
        "allow_popups": allow_popups,
        "allow_mutating_methods": allow_mutating_methods,
        "policy_hash": "",
    }
    policy["policy_hash"] = _hash({k: v for k, v in policy.items() if k != "policy_hash"})
    return policy


def evaluate_network_request(
    *,
    policy: dict[str, Any],
    request_url: str,
    method: str,
    request_payload_hash: str | None = None,
    approval_hash: str | None = None,
) -> dict[str, Any]:
    method = method.upper()
    reasons: list[str] = []

    if not _domain_allowed(request_url, policy["allowed_domains"]):
        reasons.append("network_request_outside_allowed_domains")

    if method in MUTATING_HTTP_METHODS and not policy["allow_mutating_methods"]:
        reasons.append("mutating_http_method_blocked")

    if method in MUTATING_HTTP_METHODS and not approval_hash:
        reasons.append("missing_approval_hash_for_mutating_request")

    if method not in SAFE_HTTP_METHODS and method not in MUTATING_HTTP_METHODS:
        reasons.append("unknown_http_method_blocked")

    allowed = not reasons

    result = {
        "schema_version": "aion.browser_network_interception.v0",
        "mission_id": policy["mission_id"],
        "mission_run_id": policy["mission_run_id"],
        "provider": policy["provider"],
        "browser_worker_id": policy["browser_worker_id"],
        "policy_hash": policy["policy_hash"],
        "event_type": "network_request",
        "request_url": request_url,
        "method": method,
        "request_payload_hash": request_payload_hash,
        "approval_hash": approval_hash,
        "allowed": allowed,
        "interception_state": "allowed" if allowed else "blocked",
        "reasons": reasons,
        "interception_hash": "",
    }
    result["interception_hash"] = _hash({k: v for k, v in result.items() if k != "interception_hash"})
    return result


def evaluate_navigation(
    *,
    policy: dict[str, Any],
    target_url: str,
    redirect_chain: list[str] | None = None,
) -> dict[str, Any]:
    redirect_chain = redirect_chain or []
    reasons: list[str] = []

    if not _domain_allowed(target_url, policy["allowed_domains"]):
        reasons.append("navigation_outside_allowed_domains")

    for redirected_url in redirect_chain:
        if not _domain_allowed(redirected_url, policy["allowed_domains"]):
            reasons.append("redirect_chain_outside_allowed_domains")
            break

    allowed = not reasons

    result = {
        "schema_version": "aion.browser_navigation_interception.v0",
        "mission_id": policy["mission_id"],
        "mission_run_id": policy["mission_run_id"],
        "provider": policy["provider"],
        "browser_worker_id": policy["browser_worker_id"],
        "policy_hash": policy["policy_hash"],
        "event_type": "navigation",
        "target_url": target_url,
        "redirect_chain": redirect_chain,
        "allowed": allowed,
        "interception_state": "allowed" if allowed else "blocked",
        "reasons": reasons,
        "interception_hash": "",
    }
    result["interception_hash"] = _hash({k: v for k, v in result.items() if k != "interception_hash"})
    return result


def evaluate_dom_mutation(
    *,
    policy: dict[str, Any],
    mutation_type: str,
    selector: str,
    staged_payload_hash: str | None = None,
    approval_hash: str | None = None,
) -> dict[str, Any]:
    reasons: list[str] = []

    if mutation_type in DANGEROUS_DOM_MUTATIONS:
        reasons.append("dangerous_dom_mutation_blocked")

    if mutation_type in DANGEROUS_DOM_MUTATIONS and not approval_hash:
        reasons.append("missing_approval_hash_for_dom_mutation")

    if mutation_type not in SAFE_DOM_MUTATIONS and mutation_type not in DANGEROUS_DOM_MUTATIONS:
        reasons.append("unknown_dom_mutation_blocked")

    allowed = not reasons

    result = {
        "schema_version": "aion.browser_dom_interception.v0",
        "mission_id": policy["mission_id"],
        "mission_run_id": policy["mission_run_id"],
        "provider": policy["provider"],
        "browser_worker_id": policy["browser_worker_id"],
        "policy_hash": policy["policy_hash"],
        "event_type": "dom_mutation",
        "mutation_type": mutation_type,
        "selector": selector,
        "staged_payload_hash": staged_payload_hash,
        "approval_hash": approval_hash,
        "allowed": allowed,
        "interception_state": "allowed" if allowed else "blocked",
        "reasons": reasons,
        "interception_hash": "",
    }
    result["interception_hash"] = _hash({k: v for k, v in result.items() if k != "interception_hash"})
    return result


def evaluate_popup(
    *,
    policy: dict[str, Any],
    popup_url: str,
) -> dict[str, Any]:
    reasons: list[str] = []

    if not policy["allow_popups"]:
        reasons.append("popup_blocked_by_policy")

    if not _domain_allowed(popup_url, policy["allowed_domains"]):
        reasons.append("popup_url_outside_allowed_domains")

    allowed = not reasons

    result = {
        "schema_version": "aion.browser_popup_interception.v0",
        "mission_id": policy["mission_id"],
        "mission_run_id": policy["mission_run_id"],
        "provider": policy["provider"],
        "browser_worker_id": policy["browser_worker_id"],
        "policy_hash": policy["policy_hash"],
        "event_type": "popup",
        "popup_url": popup_url,
        "allowed": allowed,
        "interception_state": "allowed" if allowed else "blocked",
        "reasons": reasons,
        "interception_hash": "",
    }
    result["interception_hash"] = _hash({k: v for k, v in result.items() if k != "interception_hash"})
    return result


def evaluate_download(
    *,
    policy: dict[str, Any],
    download_url: str,
    file_name: str,
) -> dict[str, Any]:
    reasons: list[str] = []

    if not policy["allow_downloads"]:
        reasons.append("download_blocked_by_policy")

    if not _domain_allowed(download_url, policy["allowed_domains"]):
        reasons.append("download_url_outside_allowed_domains")

    allowed = not reasons

    result = {
        "schema_version": "aion.browser_download_interception.v0",
        "mission_id": policy["mission_id"],
        "mission_run_id": policy["mission_run_id"],
        "provider": policy["provider"],
        "browser_worker_id": policy["browser_worker_id"],
        "policy_hash": policy["policy_hash"],
        "event_type": "download",
        "download_url": download_url,
        "file_name": file_name,
        "allowed": allowed,
        "interception_state": "allowed" if allowed else "blocked",
        "reasons": reasons,
        "interception_hash": "",
    }
    result["interception_hash"] = _hash({k: v for k, v in result.items() if k != "interception_hash"})
    return result


def evaluate_iframe_or_script(
    *,
    policy: dict[str, Any],
    event_type: str,
    resource_url: str,
) -> dict[str, Any]:
    if event_type not in {"iframe", "script"}:
        raise ValueError(f"Unsupported resource event type: {event_type}")

    reasons: list[str] = []

    allowed_list = (
        policy["allowed_iframe_domains"]
        if event_type == "iframe"
        else policy["allowed_script_domains"]
    )

    if not _domain_allowed(resource_url, allowed_list):
        reasons.append(f"{event_type}_resource_outside_allowed_domains")

    allowed = not reasons

    result = {
        "schema_version": "aion.browser_resource_interception.v0",
        "mission_id": policy["mission_id"],
        "mission_run_id": policy["mission_run_id"],
        "provider": policy["provider"],
        "browser_worker_id": policy["browser_worker_id"],
        "policy_hash": policy["policy_hash"],
        "event_type": event_type,
        "resource_url": resource_url,
        "allowed": allowed,
        "interception_state": "allowed" if allowed else "blocked",
        "reasons": reasons,
        "interception_hash": "",
    }
    result["interception_hash"] = _hash({k: v for k, v in result.items() if k != "interception_hash"})
    return result


def summarize_interceptions(
    *,
    mission_id: str,
    mission_run_id: str,
    browser_worker_id: str,
    interceptions: list[dict[str, Any]],
) -> dict[str, Any]:
    blocked = [item for item in interceptions if not item["allowed"]]
    allowed = [item for item in interceptions if item["allowed"]]

    result = {
        "schema_version": "aion.browser_interception_summary.v0",
        "mission_id": mission_id,
        "mission_run_id": mission_run_id,
        "browser_worker_id": browser_worker_id,
        "allowed_count": len(allowed),
        "blocked_count": len(blocked),
        "blocked_reasons": sorted({reason for item in blocked for reason in item["reasons"]}),
        "interception_hashes": sorted(item["interception_hash"] for item in interceptions),
        "runtime_state": "blocked_for_safety" if blocked else "interceptions_clear",
        "summary_hash": "",
    }
    result["summary_hash"] = _hash({k: v for k, v in result.items() if k != "summary_hash"})
    return result
