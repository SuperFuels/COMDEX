import json
from pathlib import Path

from backend.modules.aion_business.runtime.business_container_service import BusinessContainerService


# Use the repository's actual base_dir. Do not hardcode the container path,
# because AIONBusinessPaths.ROOT is the source of truth.
ROOT = None


def test_goal_engine_business_container_kinds_are_registered():
    contracts = Path("backend/modules/aion_business/contracts/business_containers.py").read_text()
    repo = Path("backend/modules/aion_business/runtime/business_container_repository.py").read_text()

    for kind in [
        "goal_engine_state",
        "goal_engine_memory",
        "goal_engine_evidence",
        "goal_engine_experiments",
        "goal_engine_loops",
        "goal_engine_outcomes",
    ]:
        assert kind in contracts
        assert kind in repo


def test_goal_engine_business_container_bindings_are_declared():
    service = Path("backend/modules/aion_business/runtime/business_container_service.py").read_text()

    for topic in [
        "business.goal_engine.state",
        "business.goal_engine.memory",
        "business.goal_engine.evidence",
        "business.goal_engine.experiments",
        "business.goal_engine.loops",
        "business.goal_engine.outcomes",
    ]:
        assert topic in service

    assert "dry_run_preview_is_not_persistent_truth" in service
    assert "boardroom_is_projection_only" in service
    assert '"write_guard": "human_review"' in service or "'write_guard': 'human_review'" in service


def test_goal_engine_business_containers_are_created_for_workspace(tmp_path):
    service = BusinessContainerService()
    workspace_id = "costa-conexion"

    service.ensure_canonical_containers(workspace_id)

    base = service.repository.base_dir / workspace_id
    expected = [
        "goal_engine_state.json",
        "goal_engine_memory.json",
        "goal_engine_evidence.json",
        "goal_engine_experiments.json",
        "goal_engine_loops.json",
        "goal_engine_outcomes.json",
    ]

    for filename in expected:
        path = base / filename
        assert path.exists(), filename
        payload = json.loads(path.read_text())
        assert payload["workspace_id"] == workspace_id
        assert payload["governance"]["write_guard"] == "human_review"
        assert payload["governance"]["dry_run_preview_is_not_persistent_truth"] is True
        assert payload["governance"]["boardroom_is_projection_only"] is True
        assert isinstance(payload["records"], list)
        assert isinstance(payload["events"], list)


def test_boardroom_payload_exposes_preview_but_does_not_act_as_storage():
    service_source = Path("backend/modules/aion_business/runtime/business_container_service.py").read_text()

    boardroom_start = service_source.index("def get_boardroom_payload")
    boardroom_block = service_source[boardroom_start:boardroom_start + 2200]

    assert "_build_goal_engine_boardroom_runtime_preview_v1" in boardroom_block
    assert "goal_engine_preview_bundle" in service_source

    # Boardroom payload may project the preview, but persistent writes belong to
    # canonical business containers, not the Boardroom renderer/read endpoint.
    assert "goal_engine_state" not in boardroom_block
    assert "goal_engine_memory" not in boardroom_block
    assert "goal_engine_evidence" not in boardroom_block
    assert "goal_engine_experiments" not in boardroom_block
    assert "goal_engine_loops" not in boardroom_block
    assert "goal_engine_outcomes" not in boardroom_block
