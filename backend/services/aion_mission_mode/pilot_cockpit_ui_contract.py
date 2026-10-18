from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List


FORBIDDEN_LIVE_ACTION_LABELS = {
    "send email now",
    "send whatsapp now",
    "publish post now",
    "buy domain now",
    "deploy production now",
    "capture payment now",
    "create booking now",
    "create escrow now",
    "mutate live reputation now",
    "write long-term memory now",
}


def canonical_hash(payload: Dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"sha256:{hashlib.sha256(raw).hexdigest()}"


def build_pilot_cockpit_read_model(
    *,
    mission_id: str,
    mission_run_id: str,
    business_id: str,
    current_step: Dict[str, Any],
    steps: List[Dict[str, Any]],
    artifacts: List[Dict[str, Any]],
    approvals: List[Dict[str, Any]],
    blocked_actions: List[Dict[str, Any]],
    feedback_events: List[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    feedback_events = feedback_events or []

    model = {
        "schema_version": "aion.phase21a.pilot_cockpit_ui.v1",
        "surface_type": "read_model_only",
        "mission_id": mission_id,
        "mission_run_id": mission_run_id,
        "business_id": business_id,
        "pilot_identity": {
            "name": "AION Pilot",
            "executor_type": "native_aion_runtime",
            "ui_automation": False,
        },
        "mission_stream": {
            "current_step": current_step,
            "completed_steps": [s for s in steps if s.get("state") == "completed"],
            "waiting_approval_steps": [s for s in steps if s.get("state") == "waiting_approval"],
            "waiting_human_task_steps": [s for s in steps if s.get("state") == "waiting_human_task"],
            "blocked_steps": [s for s in steps if s.get("state") == "blocked"],
            "skipped_steps": [s for s in steps if s.get("state") == "skipped"],
        },
        "plan_canvas": {
            "matrix_visible": True,
            "sub_plans_visible": True,
            "plan_diff_visible": True,
            "change_impact_visible": True,
            "canvas_is_execution_surface": False,
        },
        "artifacts": [
            {
                **artifact,
                "container_visible": True,
                "provenance_visible": all(
                    key in artifact for key in ["mission_id", "mission_run_id", "step_id", "artifact_hash"]
                ),
            }
            for artifact in artifacts
        ],
        "approval_surface": {
            "exact_payload_cards": approvals,
            "blocked_actions": blocked_actions,
            "safety_message": (
                "No money, post, deploy, booking, payment, external send, escrow or "
                "reputation mutation happens without approval."
            ),
        },
        "feedback_surface": {
            "enabled": True,
            "feedback_mutates_live_memory": False,
            "events": feedback_events,
            "allowed_feedback_actions": [
                "request_revision",
                "approve_draft",
                "reject_draft",
                "ask_pilot_to_explain_step",
                "ask_where_file_was_saved",
                "ask_what_is_blocked_and_why",
                "start_follow_up_mission",
            ],
        },
        "proof_surface": {
            "proof_visible": True,
            "replay_visible": True,
            "receipts_visible": True,
            "ets_preview_visible": True,
            "replay_executes_tools": False,
            "ets_mutates_reputation": False,
        },
        "raw_live_action_buttons_present": False,
        "forbidden_live_action_labels": sorted(FORBIDDEN_LIVE_ACTION_LABELS),
    }

    model["cockpit_hash"] = canonical_hash(model)
    return model


def validate_pilot_cockpit_read_model(model: Dict[str, Any]) -> Dict[str, Any]:
    reasons: List[str] = []

    if model.get("surface_type") != "read_model_only":
        reasons.append("pilot_cockpit_must_be_read_model_only")

    if model.get("raw_live_action_buttons_present") is True:
        reasons.append("raw_live_action_buttons_present")

    if model.get("pilot_identity", {}).get("ui_automation") is True:
        reasons.append("pilot_must_not_be_presented_as_ui_automation")

    if model.get("plan_canvas", {}).get("canvas_is_execution_surface") is True:
        reasons.append("canvas_must_not_be_execution_surface")

    if model.get("feedback_surface", {}).get("feedback_mutates_live_memory") is True:
        reasons.append("feedback_must_not_mutate_live_memory")

    proof = model.get("proof_surface", {})
    if proof.get("replay_executes_tools") is True:
        reasons.append("replay_must_not_execute_tools")
    if proof.get("ets_mutates_reputation") is True:
        reasons.append("ets_preview_must_not_mutate_reputation")

    for artifact in model.get("artifacts", []):
        if not artifact.get("provenance_visible"):
            reasons.append(f"artifact_missing_visible_provenance:{artifact.get('artifact_id', 'unknown')}")

    allowed = not reasons
    result = {
        "schema_version": "aion.phase21a.pilot_cockpit_validation.v1",
        "allowed": allowed,
        "validation_state": "pilot_cockpit_contract_valid" if allowed else "pilot_cockpit_contract_invalid",
        "reasons": reasons if reasons else ["pilot_cockpit_read_model_verified"],
        "cockpit_hash": model.get("cockpit_hash", "none"),
    }
    result["validation_hash"] = canonical_hash(result)
    return result
