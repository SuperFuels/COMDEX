from pathlib import Path

from backend.modules.hexcore.software_system_project_authority import (
    SoftwareSystemProjectAuthority, SUBJECT_PROJECTS, run_benchmark,
)


ROOT=Path(__file__).resolve().parents[2]


def test_eight_system_adapters_cover_declared_subskills_and_reject_faults(tmp_path):
    result=run_benchmark(repo_root=ROOT,state_path=tmp_path/"state.json",result_path=tmp_path/"result.json")
    assert result["passed"] is True
    assert result["gate"]["verified_subject_adapters"]==8
    assert result["gate"]["distinct_executable_projects"]>=16
    assert result["gate"]["mapped_project_counterexamples_rejected"]==result["gate"]["mapped_project_counterexamples_total"]


def test_project_rotation_is_distinct_and_records_only_demonstrated_subskills(tmp_path):
    fabric=SoftwareSystemProjectAuthority(repo_root=ROOT,state_path=tmp_path/"state.json")
    contract={"requirement":{"kind":"project","subskills":["processes","scheduling","threads","memory"]}}
    first=fabric.run("operating_systems",contract,[])
    evidence=[{"project_family":first["project_family"]}]
    second=fabric.run("operating_systems",contract,evidence)
    assert first["passed"] and second["passed"]
    assert first["project_family"]!=second["project_family"]
    declared=set(fabric.state["adapters"]["operating_systems"]["required_subskills"])
    assert set(first["evidenced_subskills"])<=declared
    assert first["gate"]["unsafe_variants_rejected"]==6


def test_unsupported_human_authority_is_not_installed(tmp_path):
    fabric=SoftwareSystemProjectAuthority(repo_root=ROOT,state_path=tmp_path/"state.json")
    assert "social_commonsense" not in fabric.state["adapters"]
    assert set(fabric.state["adapters"])==set(SUBJECT_PROJECTS)
