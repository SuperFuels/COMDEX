import json

import pytest

from backend.modules.hexcore.autonomous_general_apprentice import (
    AutonomousGeneralApprentice,
    EVIDENCE_GATES,
)


def _positive_artifact(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "schema_version": "aion.test.curriculum.v1",
        "procedure_id": "procedure_test_curriculum",
        "passed": True,
        "promotion": {
            "candidate": {
                "procedure_id": "procedure_test_curriculum",
                "steps": ["select experiments by information gain per cost"],
            },
            "decision": {"promoted": True},
        },
        "gate": {"transfer": True, "restart_retention": True},
    }), encoding="utf-8")


def test_general_apprentice_protects_terminal_mission_and_derives_curriculum(tmp_path):
    _positive_artifact(tmp_path / "results/hexcore_curriculum_test.json")
    ledger = tmp_path / "results/hexcore_long_duration_campaign_v15_ledger.jsonl"
    ledger.write_text(json.dumps({
        "cycle": 1, "changes_detected": ["source_a"], "all_outcomes_safe": True,
        "execution": {"passed": True}, "transaction": {"passed": True},
        "outcome_sha256": "a" * 64,
    }) + "\n", encoding="utf-8")
    apprentice = AutonomousGeneralApprentice(
        state_path=tmp_path / "state.json", repo_root=tmp_path
    )
    objective = "Learn unfamiliar subjects and transfer verified methods."
    apprentice.authorize(
        objective=objective,
        allowed_authorities=["public_delayed_outcome_ledger:v15"],
        action_budget=10,
    )
    with pytest.raises(ValueError):
        apprentice.authorize(
            objective="Replace the terminal objective.",
            allowed_authorities=["public_delayed_outcome_ledger:v15"],
            action_budget=10,
        )
    apprentice.refresh_evidence()
    task = apprentice.next_task()
    assert len(apprentice.state["gate_state"]) == len(EVIDENCE_GATES) == 10
    assert task["human_supplied_task_fields"] == 0
    assert task["derived_task_fields"] == 10
    assert task["delayed_outcome_contract"]["cursor"] == 1
    assert apprentice.bind_new_delayed_outcome()["status"] == "waiting"


def test_delayed_authority_cannot_reuse_precommit_rows(tmp_path):
    _positive_artifact(tmp_path / "results/hexcore_curriculum_test.json")
    ledger = tmp_path / "results/hexcore_long_duration_campaign_v15_ledger.jsonl"
    first = {
        "cycle": 1, "changes_detected": ["source_a"], "all_outcomes_safe": True,
        "execution": {"passed": True}, "transaction": {"passed": True},
        "outcome_sha256": "a" * 64,
    }
    ledger.write_text(json.dumps(first) + "\n", encoding="utf-8")
    apprentice = AutonomousGeneralApprentice(
        state_path=tmp_path / "state.json", repo_root=tmp_path
    )
    apprentice.authorize(
        objective="Learn unfamiliar subjects from later consequences.",
        allowed_authorities=["public_delayed_outcome_ledger:v15"],
        action_budget=10,
    )
    apprentice.refresh_evidence()
    task = apprentice.next_task()
    assert apprentice.bind_new_delayed_outcome()["status"] == "waiting"
    second = {
        "cycle": 2, "changes_detected": ["source_a"], "all_outcomes_safe": True,
        "execution": {"passed": True}, "transaction": {"passed": True},
        "outcome_sha256": "b" * 64,
    }
    with ledger.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(second) + "\n")
    bound = apprentice.bind_new_delayed_outcome()
    assert bound["status"] == "bound"
    assert bound["outcome"]["revealed_cycle"] == 2
    assert bound["outcome"]["pre_action_commitment"] == task["delayed_outcome_contract"]["commitment"]
    assert bound["receipt"]["verified"] is True


def test_promoted_kernel_result_tracks_control_plane_not_long_term_completion():
    result = json.loads(open("results/hexcore_autonomous_general_apprentice.json", encoding="utf-8").read())
    assert result["passed"] is True
    assert result["gate"]["evidence_gates_tracked"] == 10
    assert result["gate"]["terminal_objective_immutable"] is True
    assert all(not row["externally_complete"] for row in result["gate_state"].values())
