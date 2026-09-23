import json
from pathlib import Path

from backend.modules.hexcore.real_outcome_failure_arbitration import attribute_outcome, run


def test_world_change_is_not_misclassified_as_self_failure():
    row = {"remotes": {"feed": {"reachable": True}}, "execution": {"passed": True}, "transaction": {"passed": True}, "changes_detected": ["feed"]}
    result = attribute_outcome(row)
    assert result["class"] == "external_world_change"
    assert "repair" not in result["response"]


def test_internal_and_acquisition_failures_are_distinguished():
    base = {"remotes": {"feed": {"reachable": True}}, "execution": {"passed": True}, "transaction": {"passed": True}}
    execution = json.loads(json.dumps(base)); execution["execution"]["passed"] = False
    persistence = json.loads(json.dumps(base)); persistence["transaction"]["passed"] = False
    acquisition = json.loads(json.dumps(base)); acquisition["remotes"]["feed"]["reachable"] = False
    assert attribute_outcome(execution)["class"] == "execution_failure"
    assert attribute_outcome(persistence)["class"] == "persistence_failure"
    assert attribute_outcome(acquisition)["class"] == "evidence_acquisition_failure"


def test_campaign_outcomes_are_committed_and_retained(tmp_path: Path):
    repo = tmp_path / "repo"; (repo / "results").mkdir(parents=True)
    ledger = repo / "results/hexcore_long_duration_campaign_v15_ledger.jsonl"
    rows = []
    for cycle in range(1, 5):
        row = {
            "cycle": cycle,
            "pre_action_commitment": f"commit-{cycle}",
            "outcome_sha256": f"outcome-{cycle}",
            "remotes": {"feed": {"reachable": True}},
            "execution": {"passed": True},
            "transaction": {"passed": True},
            "changes_detected": ["feed"] if cycle == 4 else [],
            "all_outcomes_safe": True,
        }
        rows.append(json.dumps(row))
    ledger.write_text("\n".join(rows) + "\n", encoding="utf-8")
    result = run(repo_root=repo, state_path=tmp_path / "state.json", result_path=tmp_path / "result.json")
    assert result["passed"] is True
    assert result["gate"]["external_change_cycles"] == 1
    assert result["gate"]["external_changes_misrouted_to_self_repair"] == 0
    assert result["gate"]["private_audit_accuracy"] == 1.0
    assert result["restart"]["relearning_outcomes"] == 0
