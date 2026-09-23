import pytest

from backend.modules.hexcore.autonomous_mastery_runtime import (
    AutonomousMasteryController,
    OpenCapabilityGraphInventor,
    run_benchmark,
)


def test_open_diagnosis_and_autonomous_mastery_pass(tmp_path):
    result = run_benchmark(
        workspace_root=tmp_path / "workspace",
        result_path=tmp_path / "result.json",
    )
    assert result["passed"] is True
    assert result["gate"]["diagnostic_accuracy"] == 1.0
    assert result["gate"]["self_generated_criticism"] == 5
    assert result["gate"]["owner_targets_induced"] == 4
    assert result["gate"]["invented_capabilities_mastered"] == result["gate"]["invented_capabilities_total"]
    assert result["gate"]["restart_retained"] is True
    rerun = run_benchmark(
        workspace_root=tmp_path / "workspace",
        result_path=tmp_path / "result-rerun.json",
    )
    assert rerun["passed"] is True
    assert len(rerun["mastery_state"]["outcomes"]) == 34


def test_open_graph_requests_clarification_without_learning_target():
    result = OpenCapabilityGraphInventor().invent(
        mission_id="ambiguous",
        objective="Make the system better somehow.",
        authorities=["independent_test"],
    )
    assert result["status"] == "needs_clarification"


def test_authorized_terminal_objective_cannot_be_replaced(tmp_path):
    inventor = OpenCapabilityGraphInventor()
    first = inventor.invent(
        mission_id="mission",
        objective="Learn an unfamiliar symbolic language",
        authorities=["sealed_test"],
    )
    controller = AutonomousMasteryController(tmp_path / "state.json")
    controller.authorize(first)
    changed = inventor.invent(
        mission_id="mission",
        objective="Master a different terminal objective",
        authorities=["sealed_test"],
    )
    with pytest.raises(ValueError, match="immutable"):
        controller.authorize(changed)
