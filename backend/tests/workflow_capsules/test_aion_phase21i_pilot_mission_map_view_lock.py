import pytest

from backend.services.aion_mission_mode.pilot_mission_map_view import (
    PilotMissionMapContractError,
    PilotMissionMapView,
)


def test_phase21i_demo_map_builds():
    mission_map = PilotMissionMapView.demo_home_fixed_pdf_map()
    assert mission_map["schema_version"] == "aion.pilot.mission_map.v1"
    assert mission_map["business_id"] == "home-fixed"
    assert mission_map["read_model_only"] is True
    assert mission_map["tool_execution_allowed"] is False
    assert mission_map["live_side_effect_allowed"] is False
    assert mission_map["mission_map_hash"].startswith("sha256:")


def test_phase21i_nodes_have_lanes():
    mission_map = PilotMissionMapView.demo_home_fixed_pdf_map()
    lanes = {node["lane"] for node in mission_map["nodes"]}
    assert "autonomous_preview" in lanes
    assert "blocked" in lanes


def test_phase21i_artifacts_attach_to_steps():
    mission_map = PilotMissionMapView.demo_home_fixed_pdf_map()
    artifact_nodes = [node for node in mission_map["nodes"] if node["artifact_refs"]]
    assert artifact_nodes
    assert "business/home-fixed/missions/" in artifact_nodes[0]["artifact_refs"][0]


def test_phase21i_receipts_and_replay_attach_to_steps():
    mission_map = PilotMissionMapView.demo_home_fixed_pdf_map()
    node = next(node for node in mission_map["nodes"] if node["node_id"] == "step_3")
    assert node["receipt_refs"] == ["sha256:preview_receipt_hash"]
    assert node["replay_refs"] == ["sha256:preview_replay_hash"]


def test_phase21i_blocked_actions_attach_to_blocked_node():
    mission_map = PilotMissionMapView.demo_home_fixed_pdf_map()
    blocked = next(node for node in mission_map["nodes"] if node["lane"] == "blocked")
    assert blocked["blocked_action_refs"] == ["external_send", "production_deploy"]


def test_phase21i_blocks_raw_tool_execution_actions():
    with pytest.raises(PilotMissionMapContractError):
        PilotMissionMapView.build_node({
            "step_id": "bad",
            "title": "Bad live tool",
            "lane": "autonomous_preview",
            "status": "ready",
            "action": "raw_tool_call",
        })


def test_phase21i_blocks_live_side_effect_actions():
    with pytest.raises(PilotMissionMapContractError):
        PilotMissionMapView.build_node({
            "step_id": "bad",
            "title": "Bad live deploy",
            "lane": "approval_required",
            "status": "ready",
            "action": "live_deploy",
        })


def test_phase21i_rejects_unknown_lane():
    with pytest.raises(PilotMissionMapContractError):
        PilotMissionMapView.build_node({
            "step_id": "x",
            "title": "Unknown lane",
            "lane": "secret_execution",
            "status": "ready",
        })


def test_phase21i_hash_is_deterministic():
    a = PilotMissionMapView.demo_home_fixed_pdf_map()
    b = PilotMissionMapView.demo_home_fixed_pdf_map()
    assert a["mission_map_hash"] == b["mission_map_hash"]


def test_phase21i_safety_message_present():
    mission_map = PilotMissionMapView.demo_home_fixed_pdf_map()
    assert mission_map["safety_message"] == "AION stopped itself before doing anything risky."
