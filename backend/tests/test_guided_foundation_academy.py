from pathlib import Path

from backend.modules.hexcore.guided_foundation_academy import GuidedFoundationAcademy, MODULES


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_academy_is_depth_first_and_imports_python_certificate(tmp_path):
    academy = GuidedFoundationAcademy(
        repo_root=REPO_ROOT, state_path=tmp_path / "academy/state.json",
        teacher_cache_path=tmp_path / "academy/teacher.json",
    )
    assert len(MODULES) == 13
    assert academy.state["modules"]["python_core"]["status"] == "passed_bounded"
    assert academy.state["modules"]["algorithms_data_structures"]["status"] == "ready"
    assert academy.state["modules"]["software_engineering"]["status"] == "locked"
    assert academy.state["allocation"] == {
        "primary_academy": 0.70, "retention_remediation": 0.20, "cross_domain_transfer": 0.10,
    }


def test_academy_compiles_next_contract_without_teacher_authority(tmp_path):
    academy = GuidedFoundationAcademy(
        repo_root=REPO_ROOT, state_path=tmp_path / "academy/state.json",
        teacher_cache_path=tmp_path / "academy/teacher.json",
    )
    outcome = academy.step(live_teacher=False)
    assert outcome["cycle"]["action"]["module_id"] == "algorithms_data_structures"
    row = academy.state["modules"]["algorithms_data_structures"]
    assert row["status"] == "executor_required"
    assert row["contract"]["teacher_has_exam_authority"] is False
    assert row["contract"]["requires_delayed_retention"] is True
    assert academy.state["modules"]["advanced_python"]["status"] == "ready"


def test_academy_control_plane_promotes_without_claiming_completion(tmp_path):
    academy = GuidedFoundationAcademy(
        repo_root=REPO_ROOT, state_path=tmp_path / "academy/state.json",
        teacher_cache_path=tmp_path / "academy/teacher.json",
    )
    academy.step(live_teacher=False)
    result = academy.promote(result_path=tmp_path / "result.json")
    assert result["passed"] is True
    assert result["gate"]["unrelated_subject_hopping_disabled"] is True
    assert result["gate"]["primary_academy_complete"] is False

