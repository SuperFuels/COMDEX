from pathlib import Path

from backend.modules.hexcore.autonomous_useful_work_controller import run


ROOT=Path(__file__).resolve().parents[2]


def test_selects_and_completes_measurable_north_star_work(tmp_path):
    result=run(repo_root=ROOT,registry_path=tmp_path/"registry.json",skills_path=tmp_path/"skills.json",state_path=tmp_path/"state.json",result_path=tmp_path/"result.json")
    assert result["passed"] is True
    assert result["selected_project"]["task_id"]=="acquire_real_toolchain_executors"
    assert set(result["outcome"]["new_verified_adapters"])=={"python","javascript_typescript","rust","sql_databases"}
    assert result["outcome"]["counterexamples_rejected"]==39
    assert result["outcome"]["unsafe_live_writes"]==0
    assert result["next_opportunity"]["objective"]


def test_second_cycle_advances_to_system_project_authority(tmp_path):
    args=dict(repo_root=ROOT,registry_path=tmp_path/"registry.json",skills_path=tmp_path/"skills.json",state_path=tmp_path/"state.json",result_path=tmp_path/"result.json")
    first=run(**args);second=run(**args)
    assert first["selected_project"]["task_id"]=="acquire_real_toolchain_executors"
    assert second["selected_project"]["task_id"]=="acquire_system_project_authority"
    assert second["passed"] is True
    assert len(second["outcome"]["new_verified_adapters"])==8
    assert second["outcome"]["cross_system_capstone"] is True
