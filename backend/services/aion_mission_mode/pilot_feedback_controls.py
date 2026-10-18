from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Dict, List


class PilotFeedbackContractError(ValueError):
    pass


def _hash(payload: Dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True)
class PilotFeedbackControls:
    VALID_ACTIONS = {
        "approve",
        "reject",
        "revise",
        "stop",
        "retry",
        "continue",
    }

    SAFE_STATE_TRANSITIONS = {
        "approve": "waiting_approval_chain",
        "reject": "feedback_rejected",
        "revise": "revision_requested",
        "stop": "stopped_by_user",
        "retry": "retry_requested",
        "continue": "continue_requested",
    }

    FORBIDDEN_MUTATION_TARGETS = {
        "live_memory",
        "reusable_template",
        "provider_state",
        "reputation",
        "external_system",
        "payment",
        "deployment",
        "public_post",
        "message_send",
        "booking",
        "escrow",
    }

    @classmethod
    def build_feedback_event(cls, payload: Dict[str, Any]) -> Dict[str, Any]:
        required = [
            "business_id",
            "mission_id",
            "mission_run_id",
            "step_id",
            "actor_id",
            "feedback_action",
            "feedback_text",
        ]
        for key in required:
            if not payload.get(key):
                raise PilotFeedbackContractError(f"missing required feedback field: {key}")

        action = payload["feedback_action"]
        if action not in cls.VALID_ACTIONS:
            raise PilotFeedbackContractError(f"unsupported feedback action: {action}")

        mutation_targets = set(payload.get("mutation_targets", []))
        blocked = sorted(mutation_targets.intersection(cls.FORBIDDEN_MUTATION_TARGETS))
        if blocked:
            raise PilotFeedbackContractError(
                "feedback cannot silently mutate forbidden targets: " + ",".join(blocked)
            )

        event = {
            "schema_version": "aion.phase21g.pilot_feedback_event.v1",
            "business_id": payload["business_id"],
            "mission_id": payload["mission_id"],
            "mission_run_id": payload["mission_run_id"],
            "step_id": payload["step_id"],
            "actor_id": payload["actor_id"],
            "feedback_action": action,
            "feedback_text": payload["feedback_text"],
            "current_state": payload.get("current_state", "waiting_user_feedback"),
            "next_state": cls.SAFE_STATE_TRANSITIONS[action],
            "governed_feedback_event": True,
            "approval_lattice_bypass_allowed": False,
            "silent_memory_mutation_allowed": False,
            "silent_template_mutation_allowed": False,
            "silent_provider_mutation_allowed": False,
            "silent_reputation_mutation_allowed": False,
            "live_external_side_effect_allowed": False,
            "requires_existing_aion_approval_chain": action == "approve",
        }
        event["feedback_event_hash"] = _hash(event)
        return event

    @classmethod
    def build_feedback_controls_view(
        cls,
        mission_id: str,
        run_id: str,
        current_state: str,
        feedback_events: List[Dict[str, Any]] | None = None,
    ) -> Dict[str, Any]:
        events = feedback_events or []
        view = {
            "schema_version": "aion.phase21g.pilot_feedback_controls_view.v1",
            "mission_id": mission_id,
            "mission_run_id": run_id,
            "current_state": current_state,
            "available_controls": sorted(cls.VALID_ACTIONS),
            "visible_controls": {
                "approve": True,
                "reject": True,
                "revise": True,
                "stop": True,
                "retry": True,
                "continue": True,
            },
            "feedback_text_box_visible": True,
            "private_reasoning_visible": False,
            "raw_tool_execution_visible": False,
            "live_external_action_buttons_visible": False,
            "approval_lattice_bypass_allowed": False,
            "events": events,
            "event_hashes": sorted(e["feedback_event_hash"] for e in events),
            "safety_message": "Feedback is governed. It cannot silently mutate memory, templates, provider state or reputation.",
        }
        view["view_hash"] = _hash(view)
        return view

    @classmethod
    def apply_feedback_to_mission_state(
        cls,
        mission_state: Dict[str, Any],
        feedback_event: Dict[str, Any],
    ) -> Dict[str, Any]:
        if feedback_event.get("approval_lattice_bypass_allowed") is not False:
            raise PilotFeedbackContractError("feedback cannot bypass approval lattice")

        next_state = feedback_event["next_state"]
        updated = {
            **mission_state,
            "mission_id": feedback_event["mission_id"],
            "mission_run_id": feedback_event["mission_run_id"],
            "state": next_state,
            "last_feedback_event_hash": feedback_event["feedback_event_hash"],
            "live_memory_mutated": False,
            "template_mutated": False,
            "provider_state_mutated": False,
            "reputation_mutated": False,
            "external_side_effect_executed": False,
        }
        updated["mission_state_hash"] = _hash(updated)
        return updated
