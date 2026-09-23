from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List


class PilotCockpitFrontendMountError(Exception):
    pass


class PilotCockpitFrontendMount:
    """
    Phase 21B read-model contract for mounting the visible AION Pilot cockpit.

    This is not a live executor. It prepares safe UI data only.
    """

    VALID_STATUSES = {
        "idle",
        "planning",
        "waiting_approval",
        "running_safe_work",
        "blocked",
        "completed",
    }

    @staticmethod
    def canonical_hash(payload: Dict[str, Any]) -> str:
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return "sha256:" + hashlib.sha256(raw).hexdigest()

    @classmethod
    def build_pilot_entrypoint(cls, business_id: str, mission_id: str | None = None) -> Dict[str, Any]:
        entry = {
            "component": "aion_pilot_entrypoint",
            "business_id": business_id,
            "mission_id": mission_id or "none",
            "label": "AION Pilot",
            "description": "Native AION runtime operator for safe, plan-gated business work.",
            "visible": True,
            "enabled": True,
            "opens": "pilot_cockpit",
            "live_external_actions_enabled": False,
            "requires_existing_approval_chain": True,
        }
        entry["entrypoint_hash"] = cls.canonical_hash(entry)
        return entry

    @classmethod
    def build_status_strip(cls, status: str, blocked_count: int = 0, approval_count: int = 0) -> Dict[str, Any]:
        if status not in cls.VALID_STATUSES:
            raise PilotCockpitFrontendMountError(f"Unknown Pilot status: {status}")

        strip = {
            "component": "pilot_status_strip",
            "status": status,
            "blocked_count": int(blocked_count),
            "approval_count": int(approval_count),
            "status_message": cls._status_message(status),
            "safety_message": "No money, post, deploy, booking, payment or external send without approval.",
        }
        strip["status_hash"] = cls.canonical_hash(strip)
        return strip

    @classmethod
    def build_cockpit_shell(
        cls,
        business_id: str,
        mission_id: str | None = None,
        status: str = "idle",
        panels: List[str] | None = None,
    ) -> Dict[str, Any]:
        if status not in cls.VALID_STATUSES:
            raise PilotCockpitFrontendMountError(f"Unknown Pilot status: {status}")

        panel_list = panels or [
            "mission_composer",
            "plan_preview",
            "pilot_stream",
            "business_container_files",
            "artifact_outputs",
            "approvals",
            "blocked_actions",
            "mission_map",
            "proof_replay",
            "feedback",
        ]

        shell = {
            "component": "pilot_cockpit_shell",
            "business_id": business_id,
            "mission_id": mission_id or "none",
            "pilot_identity": "AION native runtime executor",
            "not_ui_automation": True,
            "status": status,
            "panels": panel_list,
            "safe_read_model": True,
            "can_execute_raw_tools": False,
            "can_mutate_external_systems": False,
            "can_mutate_live_memory": False,
            "requires_plan_review": True,
            "requires_exact_payload_approval_for_live_actions": True,
            "required_visible_message": "AION stopped itself before doing anything risky.",
        }
        shell["cockpit_hash"] = cls.canonical_hash(shell)
        return shell

    @classmethod
    def build_boardroom_mount_payload(cls, business_id: str, mission_id: str | None = None) -> Dict[str, Any]:
        payload = {
            "schema_version": "aion.phase21b.pilot_cockpit_frontend_mount.v1",
            "entrypoint": cls.build_pilot_entrypoint(business_id, mission_id),
            "status_strip": cls.build_status_strip("idle"),
            "cockpit_shell": cls.build_cockpit_shell(business_id, mission_id, "idle"),
            "mount_location": "boardroom",
            "render_mode": "visible_operator_panel",
            "live_action_buttons_default": "hidden",
        }
        payload["mount_payload_hash"] = cls.canonical_hash(payload)
        return payload

    @staticmethod
    def _status_message(status: str) -> str:
        return {
            "idle": "Pilot is ready.",
            "planning": "Pilot is preparing a governed plan.",
            "waiting_approval": "Pilot is waiting for approval.",
            "running_safe_work": "Pilot is running safe internal work.",
            "blocked": "Pilot stopped before a risky action.",
            "completed": "Pilot completed the mission safely.",
        }[status]
