from pathlib import Path

from backend.modules.hexcore.learning_strategy_outcome_authority import (
    CASES,
    run_learning_strategy,
)
from backend.modules.hexcore.progressive_competency_executor import RUNNERS


def test_all_learning_strategy_subskills_have_closed_counterexample_cases():
    for skill in CASES:
        result = run_learning_strategy(
            {"requirement": {"kind": "knowledge_test", "subskills": [skill]}}, []
        )
        assert result["passed"] is True
        assert result["gate"]["source_disjoint_transfer"] is True
        assert result["gate"]["counterexamples_rejected"] == 1
        assert result["gate"]["counterexamples_total"] == 1
        assert result["evidenced_subskills"] == [skill]


def test_learning_strategy_cases_are_finite_and_never_replayed():
    contract = {"requirement": {"kind": "exercise", "subskills": ["monitor_comprehension"]}}
    evidence = []
    families = []
    for index in range(4):
        result = run_learning_strategy(contract, evidence)
        assert result["passed"] is True
        assert result["project_family"] not in families
        families.append(result["project_family"])
        evidence.append({"kind": "exercise", "project_family": result["project_family"]})
    exhausted = run_learning_strategy(contract, evidence)
    assert exhausted["passed"] is False
    assert exhausted["status"] == "diverse_project_executor_required"


def test_learning_strategy_has_twelve_distinct_cross_domain_projects():
    contract = {"requirement": {
        "kind": "project",
        "subskills": ["diagnose_missing_knowledge", "choose_learning_depth",
                      "plan_prerequisites", "monitor_comprehension"],
    }}
    evidence = []
    families = []
    for _ in range(12):
        result = run_learning_strategy(contract, evidence)
        assert result["passed"] is True
        families.append(result["project_family"])
        evidence.append({"kind": "project", "project_family": result["project_family"]})
    assert len(set(families)) == 12
    assert run_learning_strategy(contract, evidence)["status"] == "diverse_project_executor_required"


def test_learning_strategy_adapter_is_installed_in_progressive_runtime():
    assert "capability_learning_strategy" in RUNNERS
