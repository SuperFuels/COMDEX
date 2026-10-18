from __future__ import annotations

import json

import pytest

from backend.modules.aion_business.contracts.business_containers import (
    BusinessContainerMeta,
    BusinessMapContainer,
)
from backend.modules.aion_business.runtime.sovereign_boardroom_bridge import SovereignBoardroomBridge
from backend.modules.aion_business.runtime.sovereign_brain_setup import SovereignBrainSetup


def test_empty_brain_registers_boardroom_as_the_only_business_map_authority(tmp_path):
    status = SovereignBrainSetup(tmp_path).initialize(owner_display_name="Owner")

    assert status["boardroom_business_map"]["ok"] is True
    assert status["boardroom_business_map"]["workspace_count"] == 0
    store = json.loads((tmp_path / "brain" / "stores" / "business_map.json").read_text())
    assert len(store["records"]) == 1
    binding = store["records"][0]
    assert binding["source_of_truth"] == "boardroom_business_containers"
    assert binding["parallel_business_map_allowed"] is False
    assert "facts" not in binding


def test_empty_workspace_uses_existing_boardroom_contracts_without_demo_facts(tmp_path):
    setup = SovereignBrainSetup(tmp_path)
    status = setup.initialize(owner_display_name="Owner")
    bridge = SovereignBoardroomBridge(tmp_path)
    workspace = bridge.create_empty_workspace("new-company", owner_id=status["owner_id"])

    assert workspace["ok"] is True
    assert workspace["source_of_truth"] == "boardroom_business_containers"
    assert workspace["business_map_revision"] == 0
    assert workspace["evidence_empty"] is True
    assert workspace["container_kinds"] == [
        "business_identity", "business_structure", "business_map", "department_intelligence"
    ]
    assert bridge.status()["workspace_count"] == 1


def test_existing_boardroom_map_is_registered_and_never_replaced(tmp_path):
    setup = SovereignBrainSetup(tmp_path)
    status = setup.initialize(owner_display_name="Owner")
    bridge = SovereignBoardroomBridge(tmp_path)
    bridge.create_empty_workspace("existing-company", owner_id=status["owner_id"])
    original = BusinessMapContainer(
        id="existing-company.business_map",
        workspace_id="existing-company",
        meta=BusinessContainerMeta(
            workspace_id="existing-company", container_key="business_map", source="boardroom"
        ),
        facts=[{"field": "offer", "value": "Repairs", "source_ref": "owner", "confidence": 1.0}],
        revision=7,
    )
    bridge.repository.save_model(original)

    before = bridge.repository.load_dict("existing-company", "business_map")
    registered = bridge.create_empty_workspace("existing-company", owner_id=status["owner_id"])
    after = bridge.repository.load_dict("existing-company", "business_map")

    assert after == before
    assert registered["business_map_revision"] == 7
    assert registered["fact_count"] == 1
    assert registered["evidence_empty"] is False


def test_bridge_rejects_unsafe_workspace_identifier(tmp_path):
    SovereignBrainSetup(tmp_path).initialize(owner_display_name="Owner")
    bridge = SovereignBoardroomBridge(tmp_path)
    with pytest.raises(ValueError, match="workspace_id_invalid"):
        bridge.create_empty_workspace("../other-customer", owner_id="owner")
