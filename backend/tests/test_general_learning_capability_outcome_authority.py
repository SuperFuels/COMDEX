from backend.modules.hexcore.general_learning_capability_outcome_authority import (
    CAPABILITY_SUBSKILLS,
    SCENARIOS,
    build_general_learning_capability_runners,
)
from backend.modules.hexcore.progressive_competency_executor import RUNNERS


def test_every_previously_unserved_learning_capability_has_a_runner() -> None:
    runners = build_general_learning_capability_runners()
    assert len(runners) == 17
    assert set(runners) == set(CAPABILITY_SUBSKILLS)
    assert set(runners) <= set(RUNNERS)


def test_every_declared_subskill_produces_falsifiable_practical_evidence() -> None:
    runners = build_general_learning_capability_runners()
    for subject_id, subskills in CAPABILITY_SUBSKILLS.items():
        for subskill in subskills:
            result = runners[subject_id](
                {"requirement": {"kind": "exercise", "subskills": [subskill]}}, []
            )
            assert result["passed"] is True
            assert result["evidenced_subskills"] == [subskill]
            assert result["gate"]["candidate_execution_passed"] is True
            assert result["gate"]["counterexamples_rejected"] == 1
            assert result["experience_class"] == "bounded_cross_domain_practical_qualification"


def test_capability_portfolios_are_finite_and_cross_domain() -> None:
    runner = build_general_learning_capability_runners()["capability_systems_thinking"]
    evidence = []
    families = []
    contract = {"requirement": {"kind": "project", "subskills": ["model_feedback"]}}
    for _ in SCENARIOS:
        result = runner(contract, evidence)
        assert result["passed"] is True
        assert result["unfamiliar"] is True
        families.append(result["project_family"])
        evidence.append({"kind": "project", "project_family": result["project_family"]})
    assert len(set(families)) == len(SCENARIOS)
    exhausted = runner(contract, evidence)
    assert exhausted["status"] == "diverse_project_executor_required"
