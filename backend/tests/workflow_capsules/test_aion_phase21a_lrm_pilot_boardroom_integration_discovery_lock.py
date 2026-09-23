from pathlib import Path


DOC = Path("docs/rfc/aion_phase21a_lrm_pilot_boardroom_integration_discovery_lock.tex")
APP = Path("desktop/mac/src/app.js")
MISSION = Path("backend/services/aion_mission_mode")
LRM = Path("backend/modules/aion_lrm")
LOCAL_NODE = Path("backend/api/local_node_router.py")
BOARDROOM_API = Path("backend/modules/aion_business/api/boardroom_api.py")


def test_phase21a_lock_doc_exists():
    assert DOC.exists()


def test_phase21a_real_backend_targets_exist():
    assert MISSION.exists()
    assert LRM.exists()
    assert LOCAL_NODE.exists()
    assert BOARDROOM_API.exists()


def test_phase21a_real_frontend_targets_exist():
    text = APP.read_text()

    for term in [
        "function renderBoardroomDashboardView",
        "function renderBoardroomSurface",
        "function getAionPilotCockpitSnapshot",
        "function renderAionPilotCockpitPanel",
        "function renderAionPilotSimpleTaskStream",
        "function getAionPilotFrontendInteractionState",
        "function createAionPilotFrontendDraftMission",
        "function renderAionPilotFrontendStreamEvents",
    ]:
        assert term in text


def test_phase21a_existing_backend_modules_are_named():
    required = [
        "mission_contract.py",
        "mission_planner.py",
        "mission_runtime.py",
        "mission_approval.py",
        "pilot_native_runtime.py",
        "pilot_frontend_interaction.py",
        "pilot_mission_composer_artifact_preview.py",
        "pilot_artifact_builder_runtime.py",
        "pilot_filesystem_container_view.py",
        "pilot_mission_map_view.py",
        "boardroom_mission_control_contract.py",
        "boardroom_replay_sync.py",
        "business_container_artifacts.py",
        "capability_receipts.py",
    ]

    for name in required:
        assert (MISSION / name).exists(), name


def test_phase21a_lrm_modules_are_available():
    required = [
        "reasoning_packet.py",
        "reasoning_memory_snapshot.py",
        "reasoning_replay_trace.py",
        "reasoning_replay_boardroom.py",
        "reasoning_recommendation_card.py",
        "human_review_decision_envelope.py",
        "evidence_gap_envelope.py",
        "evidence_satisfaction_envelope.py",
        "lrm_end_to_end_decision_loop.py",
    ]

    for name in required:
        assert (LRM / name).exists(), name


def test_phase21a_doc_contains_integration_targets_and_boundaries():
    text = DOC.read_text()

    for term in [
        "Phase 21A",
        "AION-LRM",
        "Pilot",
        "Boardroom",
        "integration discovery",
        "renderBoardroomDashboardView",
        "renderBoardroomSurface",
        "getAionPilotCockpitSnapshot",
        "renderAionPilotCockpitPanel",
        "renderAionPilotSimpleTaskStream",
        "getAionPilotFrontendInteractionState",
        "backend/services/aion_mission_mode",
        "backend/modules/aion_lrm",
        "backend/api/local_node_router.py",
        "backend/modules/aion_business/api/boardroom_api.py",
        "Phase 21B",
        "LRM Pilot Context Payload Adapter",
        "preview-only",
        "human review",
        "no booking",
        "no payment",
        "no escrow",
        "no external message",
        "no live chain",
        "no duplicate Pilot",
        "no private chain-of-thought",
        "Tessaris AI",
        "Kevin Robinson",
    ]:
        assert term in text


def test_phase21a_is_discovery_only_not_implementation():
    text = DOC.read_text()

    assert "discovery-only" in text
    assert "MUST NOT implement new runtime behaviour" in text
    assert "MUST NOT:" in text
