from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Dict, List


class PilotComposerSecurityError(ValueError):
    pass


def _hash(payload: Dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


FORBIDDEN_LIVE_ACTIONS = {
    "send_email",
    "send_whatsapp",
    "take_payment",
    "create_booking",
    "deploy_production",
    "buy_domain",
    "publish_post",
    "start_ad_spend",
    "mutate_live_memory",
    "mutate_reputation",
}


@dataclass(frozen=True)
class PilotMissionComposerArtifactPreview:
    business_id: str
    mission_id: str
    mission_run_id: str
    requested_by: str = "operator"

    def compose_artifact_mission(
        self,
        user_request: str,
        *,
        artifact_type: str = "pdf_document",
        output_name: str = "pilot-output.pdf",
        source_data_label: str = "operator_supplied_data",
    ) -> Dict[str, Any]:
        request_lower = user_request.lower()

        for forbidden in FORBIDDEN_LIVE_ACTIONS:
            if forbidden.replace("_", " ") in request_lower or forbidden in request_lower:
                raise PilotComposerSecurityError(
                    f"Pilot composer blocked live action request: {forbidden}"
                )

        safe_output_name = output_name.replace("/", "_").replace("..", "_")
        container_path = (
            f"business/{self.business_id}/missions/{self.mission_id}/"
            f"runs/{self.mission_run_id}/artifacts/{safe_output_name}"
        )

        plan_steps: List[Dict[str, Any]] = [
            {
                "step_id": "step_001",
                "title": "Understand artifact request",
                "lane": "autonomous",
                "status": "planned",
                "side_effect": "none",
            },
            {
                "step_id": "step_002",
                "title": "Prepare draft content",
                "lane": "autonomous",
                "status": "planned",
                "side_effect": "business_container_preview_only",
            },
            {
                "step_id": "step_003",
                "title": "Create artifact preview",
                "lane": "autonomous",
                "status": "planned",
                "side_effect": "writes_preview_artifact_inside_business_container",
            },
            {
                "step_id": "step_004",
                "title": "Wait for operator feedback",
                "lane": "human_feedback",
                "status": "waiting_feedback",
                "side_effect": "none",
            },
        ]

        mission = {
            "schema_version": "aion.pilot.mission_composer_artifact_preview.v1",
            "business_id": self.business_id,
            "mission_id": self.mission_id,
            "mission_run_id": self.mission_run_id,
            "requested_by": self.requested_by,
            "user_request": user_request,
            "pilot_status": "plan_preview_ready",
            "artifact_type": artifact_type,
            "source_data_label": source_data_label,
            "output_name": safe_output_name,
            "business_container_path": container_path,
            "plan_steps": plan_steps,
            "live_external_action_buttons_visible": False,
            "raw_tool_access_visible": False,
            "credentials_visible": False,
            "requires_feedback_before_finalisation": True,
            "safety_message": "AION stopped itself before doing anything risky.",
        }

        mission["mission_preview_hash"] = _hash(mission)
        return mission

    def create_artifact_preview_record(
        self,
        mission_preview: Dict[str, Any],
        *,
        preview_status: str = "draft_preview",
    ) -> Dict[str, Any]:
        if not mission_preview["business_container_path"].startswith(
            f"business/{self.business_id}/"
        ):
            raise PilotComposerSecurityError("Artifact path escaped business container")

        artifact = {
            "schema_version": "aion.pilot.artifact_preview_record.v1",
            "business_id": self.business_id,
            "mission_id": self.mission_id,
            "mission_run_id": self.mission_run_id,
            "step_id": "step_003",
            "artifact_type": mission_preview["artifact_type"],
            "artifact_name": mission_preview["output_name"],
            "business_container_path": mission_preview["business_container_path"],
            "preview_status": preview_status,
            "mission_preview_hash": mission_preview["mission_preview_hash"],
            "live_external_side_effect": False,
            "download_enabled": True,
            "open_output_enabled": True,
            "view_receipt_enabled": True,
        }

        artifact["artifact_hash"] = _hash(artifact)
        return artifact

    def create_feedback_event(
        self,
        artifact_record: Dict[str, Any],
        *,
        feedback_action: str,
        feedback_text: str = "",
    ) -> Dict[str, Any]:
        allowed = {"approve", "reject", "revise", "stop", "retry", "continue"}
        if feedback_action not in allowed:
            raise PilotComposerSecurityError(f"Unknown feedback action: {feedback_action}")

        event = {
            "schema_version": "aion.pilot.feedback_event.v1",
            "business_id": self.business_id,
            "mission_id": self.mission_id,
            "mission_run_id": self.mission_run_id,
            "step_id": artifact_record["step_id"],
            "artifact_hash": artifact_record["artifact_hash"],
            "feedback_action": feedback_action,
            "feedback_text": feedback_text,
            "mutates_live_memory": False,
            "mutates_reusable_template": False,
            "mutates_provider_state": False,
            "mutates_reputation": False,
            "governed_feedback_event": True,
        }

        event["feedback_event_hash"] = _hash(event)
        return event

    def build_cockpit_payload(
        self,
        mission_preview: Dict[str, Any],
        artifact_record: Dict[str, Any],
        feedback_events: List[Dict[str, Any]] | None = None,
    ) -> Dict[str, Any]:
        payload = {
            "schema_version": "aion.pilot.cockpit_artifact_preview_payload.v1",
            "business_id": self.business_id,
            "mission_id": self.mission_id,
            "mission_run_id": self.mission_run_id,
            "pilot_status": mission_preview["pilot_status"],
            "composer_request": mission_preview["user_request"],
            "plan_preview": mission_preview["plan_steps"],
            "artifact_outputs": [artifact_record],
            "business_container_files": [
                {
                    "path": artifact_record["business_container_path"],
                    "artifact_hash": artifact_record["artifact_hash"],
                    "status": artifact_record["preview_status"],
                }
            ],
            "visible_controls": [
                "approve",
                "reject",
                "revise",
                "stop",
                "retry",
                "continue",
                "open_output",
                "download_output",
                "view_receipt",
                "view_replay",
            ],
            "hidden_controls": [
                "send_email_now",
                "send_whatsapp_now",
                "take_payment_now",
                "deploy_now",
                "publish_now",
                "book_now",
                "mutate_reputation_now",
            ],
            "feedback_events": feedback_events or [],
            "safety_message": "AION stopped itself before doing anything risky.",
            "raw_credentials_visible": False,
            "live_external_action_buttons_visible": False,
        }

        payload["cockpit_payload_hash"] = _hash(payload)
        return payload
