from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Dict, List


class PilotBlockedActionPanelError(ValueError):
    pass


def _hash(payload: Dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True)
class PilotBlockedActionPanel:
    VALID_REQUIRED_APPROVALS = {
        "exact_payload_approval",
        "human_task_required",
        "plan_matrix_review",
        "approval_lattice_review",
        "commercial_re_review",
        "provider_credential_review",
        "governance_approval",
    }

    FORBIDDEN_CONTINUE_STATES = {
        "payment_submit",
        "domain_purchase",
        "production_deploy",
        "public_post",
        "external_send",
        "booking_create",
        "escrow_create",
        "reputation_mutation",
        "live_memory_mutation",
    }

    @classmethod
    def build_blocked_action_record(cls, payload: Dict[str, Any]) -> Dict[str, Any]:
        required = [
            "business_id",
            "mission_id",
            "mission_run_id",
            "step_id",
            "action_id",
            "action_type",
            "blocked_reason",
            "would_have_happened",
            "safe_alternative",
            "required_approval",
        ]
        for key in required:
            if not payload.get(key):
                raise PilotBlockedActionPanelError(f"missing blocked action field: {key}")

        required_approval = payload["required_approval"]
        if required_approval not in cls.VALID_REQUIRED_APPROVALS:
            raise PilotBlockedActionPanelError(f"unsupported required approval: {required_approval}")

        action_type = payload["action_type"]
        live_action_blocked = action_type in cls.FORBIDDEN_CONTINUE_STATES

        record = {
            "schema_version": "aion.phase21h.blocked_action_record.v1",
            "business_id": payload["business_id"],
            "mission_id": payload["mission_id"],
            "mission_run_id": payload["mission_run_id"],
            "step_id": payload["step_id"],
            "action_id": payload["action_id"],
            "action_type": action_type,
            "blocked_reason": payload["blocked_reason"],
            "would_have_happened": payload["would_have_happened"],
            "safe_alternative": payload["safe_alternative"],
            "required_approval": required_approval,
            "timeline_hash": payload.get("timeline_hash", "none"),
            "proof_hash": payload.get("proof_hash", "none"),
            "outcome_summary_hash": payload.get("outcome_summary_hash", "none"),
            "blocked_state": "blocked_for_safety",
            "live_action_blocked": live_action_blocked,
            "can_continue_without_exact_approval": False,
            "external_side_effect_executed": False,
            "raw_tool_execution_visible": False,
            "safety_message": "AION stopped itself before doing anything risky.",
        }
        record["blocked_action_hash"] = _hash(record)
        return record

    @classmethod
    def build_panel_view(cls, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        sorted_records = sorted(records, key=lambda r: (r["step_id"], r["action_id"], r["blocked_action_hash"]))

        panel = {
            "schema_version": "aion.phase21h.blocked_action_panel.v1",
            "panel_title": "Blocked Actions",
            "blocked_action_count": len(sorted_records),
            "records": sorted_records,
            "record_hashes": [r["blocked_action_hash"] for r in sorted_records],
            "shows_blocked_reason": True,
            "shows_would_have_happened": True,
            "shows_safe_alternative": True,
            "shows_required_approval": True,
            "links_to_timeline": True,
            "links_to_proof": True,
            "links_to_outcome_summary": True,
            "live_external_action_buttons_visible": False,
            "raw_tool_execution_visible": False,
            "private_reasoning_visible": False,
            "safety_message": "AION stopped itself before doing anything risky.",
        }
        panel["panel_hash"] = _hash(panel)
        return panel

    @classmethod
    def assert_cannot_continue_without_exact_approval(
        cls,
        record: Dict[str, Any],
        approval: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        approval = approval or {}
        exact_approval_valid = approval.get("approval_type") == record["required_approval"] and approval.get("approved") is True
        approved_payload_hash = approval.get("payload_hash")
        expected_payload_hash = approval.get("expected_payload_hash")

        allowed = bool(exact_approval_valid and approved_payload_hash and approved_payload_hash == expected_payload_hash)

        assertion = {
            "schema_version": "aion.phase21h.blocked_action_continue_assertion.v1",
            "action_id": record["action_id"],
            "blocked_action_hash": record["blocked_action_hash"],
            "required_approval": record["required_approval"],
            "continue_allowed": allowed,
            "external_side_effect_executed": False,
            "reason": (
                "exact_approval_present"
                if allowed
                else "blocked_action_cannot_continue_without_exact_approval"
            ),
        }
        assertion["assertion_hash"] = _hash(assertion)
        return assertion
