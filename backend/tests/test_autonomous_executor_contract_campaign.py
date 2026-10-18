import json
from pathlib import Path

from backend.modules.hexcore.autonomous_executor_contract_campaign import (
    _invent_contract,
)
from backend.modules.hexcore.autonomous_general_apprentice import (
    AutonomousGeneralApprentice,
)


def test_invented_executor_contract_remains_proposal_only():
    task = {
        "gate": "cross_domain_transfer",
        "authority_id": "local_executable:node",
    }
    outcome = {
        "procedure_id": "procedure_verified_parent",
        "capabilities": ["execute_properties", "retain_contract"],
        "authorities": ["local_executable:node"],
        "transfer_family": "event_driven_polyglot_execution",
    }
    contract = _invent_contract(task, outcome)
    assert contract["proposal_only"] is True
    assert contract["authorities"] == ["local_executable:node"]
    assert "transfer_to_unfamiliar_family" in contract["capabilities"]


def test_retained_artifact_store_cannot_be_selected_as_outcome_authority(tmp_path):
    results = tmp_path / "results"
    results.mkdir()
    (results / "hexcore_minimal.json").write_text(json.dumps({
        "schema_version": "aion.test.v1",
        "procedure_id": "procedure_minimal",
        "passed": True,
        "promotion": {
            "candidate": {"procedure_id": "procedure_minimal", "steps": ["retain evidence"]},
            "decision": {"promoted": True},
        },
    }), encoding="utf-8")
    apprentice = AutonomousGeneralApprentice(
        state_path=tmp_path / "state.json", repo_root=tmp_path
    )
    apprentice.authorize(
        objective="Learn unfamiliar subjects from independent outcomes.",
        allowed_authorities=["cau_verified_artifact_store"], action_budget=2,
    )
    apprentice.refresh_evidence()
    task = apprentice.next_task()
    assert task["task_type"] == "invent_or_acquire_outcome_authority"
    assert task["authority_id"] is None


def test_promoted_campaign_has_three_authorities_and_transfer_families():
    result = json.loads(Path(
        "results/hexcore_autonomous_executor_contract_campaign.json"
    ).read_text(encoding="utf-8"))
    assert result["passed"] is True
    assert result["gate"]["verified_executor_inventions"] == 3
    assert result["gate"]["distinct_outcome_authorities"] == 3
    assert result["gate"]["distinct_transfer_families"] == 3
    assert result["gate"]["unsafe_actions"] == 0
