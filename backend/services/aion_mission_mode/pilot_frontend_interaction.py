from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List


class PilotFrontendContractError(ValueError):
    pass


ALLOWED_PILOT_STATES = {
    "idle",
    "planning",
    "waiting_plan_review",
    "waiting_approval",
    "running_safe_work",
    "blocked_for_safety",
    "completed",
    "failed",
}

ALLOWED_FEEDBACK_ACTIONS = {
    "approve_plan",
    "reject_plan",
    "revise_plan",
    "approve_payload",
    "reject_payload",
    "stop",
    "retry",
    "continue",
}

LIVE_ACTION_TYPES = {
    "payment_submit",
    "domain_purchase",
    "production_deploy",
    "publish_post",
    "send_external_message",
    "create_booking",
    "escrow_create",
    "reputation_mutation",
}


def canonical_hash(payload: Dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _assert_business_container_path(path: str, business_id: str) -> None:
    prefix = f"businesses/{business_id}/"
    if not path.startswith(prefix):
        raise PilotFrontendContractError(
            "Pilot artifact path must remain inside the selected business container"
        )


def build_pilot_frontend_state(
    *,
    business_id: str,
    mission_id: str,
    mission_run_id: str,
    user_request: str,
    pilot_state: str,
    plan_steps: List[Dict[str, Any]],
    artifacts: List[Dict[str, Any]] | None = None,
    receipts: List[Dict[str, Any]] | None = None,
    blocked_actions: List[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    if pilot_state not in ALLOWED_PILOT_STATES:
        raise PilotFrontendContractError(f"Unknown Pilot state: {pilot_state}")

    artifacts = artifacts or []
    receipts = receipts or []
    blocked_actions = blocked_actions or []

    for artifact in artifacts:
        _assert_business_container_path(artifact["path"], business_id)
        if artifact.get("artifact_type") in {"pdf", "document", "spreadsheet", "image", "site_preview"}:
            artifact.setdefault("openable", True)
        artifact.setdefault("downloadable", True)
        artifact.setdefault("receipt_required", True)

    visible_steps = []
    for index, step in enumerate(plan_steps, start=1):
        action_type = step.get("action_type", "unknown")
        lane = step.get("lane", "autonomous")
        live_action = action_type in LIVE_ACTION_TYPES

        visible_steps.append(
            {
                "step_index": index,
                "step_id": step["step_id"],
                "title": step["title"],
                "action_type": action_type,
                "lane": lane,
                "live_action": live_action,
                "requires_exact_approval": live_action or lane in {"approval", "human_approval_required"},
                "can_execute_from_ui": False if live_action else step.get("can_execute_from_ui", False),
                "status": step.get("status", "planned"),
            }
        )

    state = {
        "schema_version": "aion.phase20p.pilot_frontend_interaction.v1",
        "business_id": business_id,
        "mission_id": mission_id,
        "mission_run_id": mission_run_id,
        "user_request": user_request,
        "pilot_state": pilot_state,
        "pilot_entry_visible": True,
        "mission_composer_visible": True,
        "plan_review_visible": True,
        "pilot_stream_visible": True,
        "artifact_panel_visible": True,
        "business_container_file_view_visible": True,
        "feedback_controls_visible": True,
        "blocked_action_panel_visible": True,
        "mission_canvas_visible": True,
        "safety_message": "AION stopped itself before doing anything risky.",
        "product_message": "AION completed safe work autonomously and stopped itself before doing anything risky.",
        "plan_steps": visible_steps,
        "artifacts": artifacts,
        "receipts": receipts,
        "blocked_actions": blocked_actions,
        "ui_capabilities": {
            "approve": True,
            "reject": True,
            "revise": True,
            "stop": True,
            "retry": True,
            "continue": True,
            "open_output": True,
            "download_output": True,
            "view_receipt": True,
            "live_external_action_without_approval": False,
            "raw_credentials_visible": False,
            "raw_tool_buttons_visible": False,
        },
    }

    state["pilot_frontend_state_hash"] = canonical_hash(state)
    return state


def create_pdf_document_mission_preview(
    *,
    business_id: str,
    mission_id: str,
    mission_run_id: str,
    title: str,
    requested_data_label: str,
) -> Dict[str, Any]:
    artifact_path = (
        f"businesses/{business_id}/missions/{mission_id}/runs/{mission_run_id}/"
        f"artifacts/{title.lower().replace(' ', '_')}.pdf"
    )

    artifact = {
        "artifact_id": "artifact_pdf_001",
        "artifact_type": "pdf",
        "title": title,
        "path": artifact_path,
        "created_by": "aion_pilot",
        "status": "preview_ready",
        "data_label": requested_data_label,
        "receipt_hash": "sha256:pending_until_generation",
    }

    steps = [
        {
            "step_id": "plan_pdf_001",
            "title": "Understand requested PDF data",
            "action_type": "plan_document",
            "lane": "autonomous",
            "status": "completed",
        },
        {
            "step_id": "draft_pdf_001",
            "title": "Generate PDF draft inside business container",
            "action_type": "create_pdf_preview",
            "lane": "autonomous",
            "status": "completed",
        },
        {
            "step_id": "review_pdf_001",
            "title": "Wait for founder review",
            "action_type": "human_review",
            "lane": "human_task_required",
            "status": "waiting_review",
        },
    ]

    return build_pilot_frontend_state(
        business_id=business_id,
        mission_id=mission_id,
        mission_run_id=mission_run_id,
        user_request=f"Build me a PDF document with {requested_data_label}",
        pilot_state="completed",
        plan_steps=steps,
        artifacts=[artifact],
        receipts=[
            {
                "receipt_id": "receipt_pdf_001",
                "step_id": "draft_pdf_001",
                "receipt_hash": "sha256:pending_until_generation",
                "receipt_type": "artifact_preview_receipt",
            }
        ],
        blocked_actions=[],
    )


def apply_pilot_feedback(
    state: Dict[str, Any],
    *,
    feedback_action: str,
    note: str = "",
) -> Dict[str, Any]:
    if feedback_action not in ALLOWED_FEEDBACK_ACTIONS:
        raise PilotFrontendContractError(f"Unsupported Pilot feedback action: {feedback_action}")

    next_state = dict(state)
    next_state["last_feedback"] = {
        "action": feedback_action,
        "note": note,
        "mutates_external_provider": False,
        "requires_runtime_revalidation": feedback_action in {"retry", "continue", "revise_plan"},
    }

    if feedback_action in {"reject_plan", "stop"}:
        next_state["pilot_state"] = "blocked_for_safety"
    elif feedback_action in {"approve_plan", "continue", "retry"}:
        next_state["pilot_state"] = "waiting_approval"
    elif feedback_action == "revise_plan":
        next_state["pilot_state"] = "planning"

    next_state["pilot_frontend_state_hash"] = canonical_hash(
        {k: v for k, v in next_state.items() if k != "pilot_frontend_state_hash"}
    )
    return next_state


def assert_no_live_action_buttons(state: Dict[str, Any]) -> bool:
    for step in state.get("plan_steps", []):
        if step.get("live_action") and step.get("can_execute_from_ui"):
            raise PilotFrontendContractError("Live external action button exposed without approval")
    return True


def assert_no_raw_credentials_visible(state: Dict[str, Any]) -> bool:
    raw = json.dumps(state, sort_keys=True).lower()
    forbidden = ["password", "api_key", "access_token", "refresh_token", "cookie", "authorization"]
    for token in forbidden:
        if token in raw:
            raise PilotFrontendContractError(f"Model/UI state contains forbidden credential marker: {token}")
    return True
