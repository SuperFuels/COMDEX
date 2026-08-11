from pathlib import Path

from backend.modules.hexcore.cross_system_intelligence_capstone import REQUIRED, run


ROOT=Path(__file__).resolve().parents[2]


def test_broad_mission_routes_and_executes_cross_system_capstone(tmp_path):
    result=run(repo_root=ROOT,state_path=tmp_path/"authority.json",result_path=tmp_path/"result.json")
    assert result["passed"] is True
    assert set(result["routed_subjects"])==set(REQUIRED)
    assert result["gate"]["integrated_counterexamples_rejected"]==4
    assert result["gate"]["malicious_plans_rejected"]==6
    assert len(result["component_manifest"])==6
