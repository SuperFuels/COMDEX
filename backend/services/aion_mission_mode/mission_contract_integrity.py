"""
AION Phase 20P — Mission Contract Integrity Layer

Contract:
- Detect safe-looking step sequences that combine into forbidden outcomes.
- Detect tool-combination bypass attempts.
- Detect disguised deployment, scraping, messaging, payment or memory mutation.
- Emit deterministic integrity_hash.
- Fail closed when aggregate intent violates mission contract.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from hashlib import sha256
import json
from typing import Any


FORBIDDEN_AGGREGATE_OUTCOMES = {
    "external_message_send",
    "payment_capture",
    "booking_creation",
    "production_deployment",
    "escrow_creation",
    "memory_mutation",
    "live_reputation_write",
    "scraping_or_exfiltration",
}

DISGUISED_ACTION_TOKENS = {
    "send": "external_message_send",
    "message_customer": "external_message_send",
    "whatsapp": "external_message_send",
    "email_customer": "external_message_send",
    "charge": "payment_capture",
    "capture_payment": "payment_capture",
    "take_payment": "payment_capture",
    "book_customer": "booking_creation",
    "create_booking": "booking_creation",
    "deploy": "production_deployment",
    "publish_live": "production_deployment",
    "production": "production_deployment",
    "escrow": "escrow_creation",
    "mutate_memory": "memory_mutation",
    "write_memory": "memory_mutation",
    "write_reputation": "live_reputation_write",
    "scrape": "scraping_or_exfiltration",
    "crawl": "scraping_or_exfiltration",
    "exfiltrate": "scraping_or_exfiltration",
}

AGGREGATE_PATTERNS = {
    ("draft_customer_message", "resolve_customer_contact", "send_customer_message"): "external_message_send",
    ("quote_preview", "collect_payment_details", "capture_payment"): "payment_capture",
    ("availability_preview", "select_time_slot", "create_booking"): "booking_creation",
    ("draft_page", "build_live_bundle", "deploy_production"): "production_deployment",
    ("calculate_escrow_terms", "prepare_escrow_payload", "create_escrow"): "escrow_creation",
    ("summarise_mission", "promote_to_business_memory", "write_memory"): "memory_mutation",
    ("read_many_profiles", "extract_contact_details", "export_contacts"): "scraping_or_exfiltration",
}


@dataclass(frozen=True)
class IntegrityFinding:
    finding_type: str
    severity: str
    outcome: str
    step_ids: list[str]
    action_types: list[str]
    reason: str


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _hash(value: Any) -> str:
    return "sha256:" + sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _slug(value: Any) -> str:
    return (
        str(value or "")
        .strip()
        .lower()
        .replace("-", "_")
        .replace(" ", "_")
    )


def _step_id(step: dict[str, Any]) -> str:
    return str(step.get("step_id") or step.get("id") or step.get("action_type") or "")


def _action_type(step: dict[str, Any]) -> str:
    return _slug(step.get("action_type") or step.get("action") or step.get("step_id") or "")


def _payload_text(step: dict[str, Any]) -> str:
    return _canonical_json(step).lower().replace("-", "_").replace(" ", "_")


def detect_disguised_action(step: dict[str, Any]) -> IntegrityFinding | None:
    text = _payload_text(step)
    action = _action_type(step)

    for token, outcome in sorted(DISGUISED_ACTION_TOKENS.items()):
        if token in action or token in text:
            return IntegrityFinding(
                finding_type="disguised_forbidden_action",
                severity="high",
                outcome=outcome,
                step_ids=[_step_id(step)],
                action_types=[action],
                reason=f"disguised_token_detected:{token}",
            )

    return None


def detect_aggregate_patterns(steps: list[dict[str, Any]]) -> list[IntegrityFinding]:
    actions = [_action_type(step) for step in steps]
    findings: list[IntegrityFinding] = []

    for pattern, outcome in sorted(AGGREGATE_PATTERNS.items()):
        pattern_list = list(pattern)
        idx = 0
        matched_indices: list[int] = []

        for i, action in enumerate(actions):
            if idx < len(pattern_list) and action == pattern_list[idx]:
                matched_indices.append(i)
                idx += 1

        if idx == len(pattern_list):
            findings.append(
                IntegrityFinding(
                    finding_type="aggregate_forbidden_outcome",
                    severity="critical",
                    outcome=outcome,
                    step_ids=[_step_id(steps[i]) for i in matched_indices],
                    action_types=[actions[i] for i in matched_indices],
                    reason=f"allowed_sequence_combines_to_forbidden_outcome:{outcome}",
                )
            )

    return findings


def detect_tool_combination_bypass(steps: list[dict[str, Any]]) -> list[IntegrityFinding]:
    tool_names = {_slug(step.get("tool") or step.get("tool_id") or "") for step in steps}
    actions = {_action_type(step) for step in steps}
    findings: list[IntegrityFinding] = []

    if {"draft_tool", "contact_lookup_tool", "external_send_tool"}.issubset(tool_names):
        findings.append(
            IntegrityFinding(
                finding_type="tool_combination_bypass",
                severity="critical",
                outcome="external_message_send",
                step_ids=[_step_id(step) for step in steps],
                action_types=sorted(actions),
                reason="tool_combination_can_send_external_message",
            )
        )

    if {"quote_tool", "payment_payload_tool", "payment_capture_tool"}.issubset(tool_names):
        findings.append(
            IntegrityFinding(
                finding_type="tool_combination_bypass",
                severity="critical",
                outcome="payment_capture",
                step_ids=[_step_id(step) for step in steps],
                action_types=sorted(actions),
                reason="tool_combination_can_capture_payment",
            )
        )

    if {"page_builder_tool", "bundle_tool", "deploy_tool"}.issubset(tool_names):
        findings.append(
            IntegrityFinding(
                finding_type="tool_combination_bypass",
                severity="critical",
                outcome="production_deployment",
                step_ids=[_step_id(step) for step in steps],
                action_types=sorted(actions),
                reason="tool_combination_can_deploy_production",
            )
        )

    return findings


def evaluate_mission_contract_integrity(
    *,
    mission_id: str,
    mission_run_id: str,
    steps: list[dict[str, Any]],
) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []

    # Priority order matters for deterministic diagnostics:
    # 1. aggregate forbidden outcomes;
    # 2. explicit tool-combination bypasses;
    # 3. disguised payload/action tokens.
    #
    # A tool-combination bypass is the stronger structural finding, so it should
    # appear before token-level disguised-action findings when both match.
    findings.extend(asdict(f) for f in detect_aggregate_patterns(steps))
    findings.extend(asdict(f) for f in detect_tool_combination_bypass(steps))

    for step in steps:
        finding = detect_disguised_action(step)
        if finding:
            findings.append(asdict(finding))

    critical = any(f["severity"] == "critical" for f in findings)
    high = any(f["severity"] == "high" for f in findings)

    state = "blocked_for_safety" if critical else "waiting_human_review" if high else "integrity_passed"

    result = {
        "schema_version": "aion.mission_contract_integrity.v0",
        "mission_id": mission_id,
        "mission_run_id": mission_run_id,
        "integrity_passed": not findings,
        "runtime_mount_allowed": not findings,
        "mission_runtime_state": state,
        "findings": findings,
        "finding_count": len(findings),
        "integrity_hash": "",
    }
    result["integrity_hash"] = _hash({k: v for k, v in result.items() if k != "integrity_hash"})
    return result


def create_mission_threat_model_entry(
    *,
    mission_id: str,
    observed_pattern: str,
    mitigation: str,
    source: str = "home_fixed_demo_run",
) -> dict[str, Any]:
    entry = {
        "schema_version": "aion.mission_threat_model_entry.v0",
        "mission_id": mission_id,
        "observed_pattern": observed_pattern,
        "mitigation": mitigation,
        "source": source,
    }
    entry["threat_model_entry_hash"] = _hash(entry)
    return entry
