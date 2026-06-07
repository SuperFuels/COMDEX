import hashlib
import json
from typing import Any, Dict, List


class PilotMissionMapContractError(Exception):
    pass


class PilotMissionMapView:
    VALID_LANES = {
        "autonomous_preview",
        "approval_required",
        "human_task_required",
        "blocked",
    }

    FORBIDDEN_ACTIONS = {
        "execute_tool",
        "raw_tool_call",
        "live_payment",
        "live_deploy",
        "live_send",
        "live_post",
        "live_booking",
        "live_escrow",
        "mutate_memory",
        "write_reputation",
    }

    @staticmethod
    def canonical_hash(payload: Dict[str, Any]) -> str:
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return "sha256:" + hashlib.sha256(raw).hexdigest()

    @classmethod
    def build_node(cls, step: Dict[str, Any]) -> Dict[str, Any]:
        required = ["step_id", "title", "lane", "status"]
        missing = [key for key in required if not step.get(key)]
        if missing:
            raise PilotMissionMapContractError(f"missing required map node fields: {missing}")

        lane = step["lane"]
        if lane not in cls.VALID_LANES:
            raise PilotMissionMapContractError(f"unsupported mission map lane: {lane}")

        for forbidden in cls.FORBIDDEN_ACTIONS:
            if forbidden in json.dumps(step, sort_keys=True):
                raise PilotMissionMapContractError(f"mission map must not expose execution action: {forbidden}")

        node = {
            "node_id": step["step_id"],
            "title": step["title"],
            "lane": lane,
            "status": step["status"],
            "artifact_refs": list(step.get("artifact_refs", [])),
            "receipt_refs": list(step.get("receipt_refs", [])),
            "proof_refs": list(step.get("proof_refs", [])),
            "replay_refs": list(step.get("replay_refs", [])),
            "blocked_action_refs": list(step.get("blocked_action_refs", [])),
            "read_model_only": True,
            "tool_execution_allowed": False,
            "live_side_effect_allowed": False,
        }
        node["node_hash"] = cls.canonical_hash(node)
        return node

    @classmethod
    def build_mission_map(cls, mission: Dict[str, Any]) -> Dict[str, Any]:
        required = ["business_id", "mission_id", "mission_run_id", "steps"]
        missing = [key for key in required if not mission.get(key)]
        if missing:
            raise PilotMissionMapContractError(f"missing required mission map fields: {missing}")

        nodes = [cls.build_node(step) for step in mission["steps"]]

        mission_map = {
            "schema_version": "aion.pilot.mission_map.v1",
            "business_id": mission["business_id"],
            "mission_id": mission["mission_id"],
            "mission_run_id": mission["mission_run_id"],
            "map_state": mission.get("map_state", "preview"),
            "read_model_only": True,
            "tool_execution_allowed": False,
            "live_side_effect_allowed": False,
            "lanes": sorted(cls.VALID_LANES),
            "nodes": nodes,
            "edges": list(mission.get("edges", [])),
            "safety_message": "AION stopped itself before doing anything risky.",
        }
        mission_map["mission_map_hash"] = cls.canonical_hash(mission_map)
        return mission_map

    @classmethod
    def demo_home_fixed_pdf_map(cls) -> Dict[str, Any]:
        return cls.build_mission_map({
            "business_id": "home-fixed",
            "mission_id": "pilot_demo_pdf_mission",
            "mission_run_id": "pilot_demo_run_preview",
            "steps": [
                {
                    "step_id": "step_1",
                    "title": "Understand PDF document request",
                    "lane": "autonomous_preview",
                    "status": "completed",
                },
                {
                    "step_id": "step_2",
                    "title": "Draft deterministic document plan",
                    "lane": "autonomous_preview",
                    "status": "completed",
                    "proof_refs": ["sha256:preview_plan_hash"],
                },
                {
                    "step_id": "step_3",
                    "title": "Create draft PDF artifact inside business container",
                    "lane": "autonomous_preview",
                    "status": "completed",
                    "artifact_refs": ["business/home-fixed/missions/pilot_demo_pdf_mission/runs/pilot_demo_run_preview/artifacts/draft-document.pdf"],
                    "receipt_refs": ["sha256:preview_receipt_hash"],
                    "replay_refs": ["sha256:preview_replay_hash"],
                },
                {
                    "step_id": "step_4",
                    "title": "External send / publish / deploy",
                    "lane": "blocked",
                    "status": "blocked",
                    "blocked_action_refs": ["external_send", "production_deploy"],
                },
            ],
            "edges": [
                {"from": "step_1", "to": "step_2"},
                {"from": "step_2", "to": "step_3"},
                {"from": "step_3", "to": "step_4"},
            ],
        })
