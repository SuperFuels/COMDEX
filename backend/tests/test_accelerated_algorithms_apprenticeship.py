from pathlib import Path

from backend.modules.hexcore.accelerated_algorithms_apprenticeship import (
    INITIAL_SOURCE,
    REMEDIATED_SOURCE,
    SEALED_TEST,
    _execute,
    _generated_properties,
    run,
)
from backend.modules.hexcore.guided_foundation_academy import GuidedFoundationAcademy


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_sealed_counterexample_rejects_negative_edge_then_remediation_passes():
    assert _execute(INITIAL_SOURCE, SEALED_TEST)["passed"] is False
    assert _execute(REMEDIATED_SOURCE, SEALED_TEST)["passed"] is True
    assert _generated_properties(REMEDIATED_SOURCE, cases=120)["passed"] is True


def test_accelerated_module_records_verified_academy_receipt(tmp_path):
    academy_path = tmp_path / "academy/state.json"
    academy = GuidedFoundationAcademy(
        repo_root=REPO_ROOT, state_path=academy_path,
        teacher_cache_path=tmp_path / "academy/teacher.json",
    )
    academy.step(live_teacher=False)
    result_path = tmp_path / "algorithms/result.json"
    result = run(
        repo_root=REPO_ROOT, academy_state_path=academy_path,
        state_path=tmp_path / "algorithms/state.json", result_path=result_path,
    )
    assert result["passed"] is True
    assert result["academy_receipt"]["verified"] is True
    restarted = GuidedFoundationAcademy(
        repo_root=REPO_ROOT, state_path=academy_path,
        teacher_cache_path=tmp_path / "academy/teacher.json",
    )
    assert restarted.state["modules"]["algorithms_data_structures"]["status"] == "passed_bounded"
    assert restarted.state["modules"]["software_engineering"]["status"] == "locked"
