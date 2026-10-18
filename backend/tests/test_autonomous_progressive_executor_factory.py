from pathlib import Path

from backend.modules.hexcore.autonomous_progressive_executor_factory import run


def test_factory_installs_verified_cross_domain_adapters_and_abstains_outside_fabric(tmp_path: Path):
    root=Path(__file__).resolve().parents[2]
    result=run(repo_root=root,result_path=tmp_path/"result.json",state_path=tmp_path/"state.json")
    assert result["passed"] is True
    assert result["gate"]["verified_family_adapters"] >= 7
    assert result["gate"]["distinct_authority_families"] >= 6
    assert result["gate"]["unsupported_family_abstention"] is True
    assert result["gate"]["restart_retention"] is True
