from pathlib import Path

from backend.modules.hexcore.cross_domain_competency_application_benchmark import run


def test_retained_competencies_are_selected_and_composed_on_fresh_work(tmp_path: Path):
    repo_root = Path(__file__).resolve().parents[2]
    result = run(repo_root=repo_root, result_path=tmp_path / "result.json")
    assert result["passed"] is True
    assert result["gate"]["single_domain_route_exact"] is True
    assert result["gate"]["mixed_domain_route_exact"] is True
    assert result["mixed_domain"]["algorithm_only_control"]["checks_passed"] == 4
    assert result["mixed_domain"]["algorithm_only_control"]["checks_total"] == 5
    assert result["mixed_domain"]["hidden"]["checks_passed"] == 5
    assert result["gate"]["unsafe_challenger_rejected"] is True
