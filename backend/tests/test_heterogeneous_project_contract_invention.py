from pathlib import Path

from backend.modules.hexcore.heterogeneous_project_contract_invention import run


def test_real_project_contracts_are_invented_before_hidden_outcomes(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    result = run(
        source_state_path=root / "backend/modules/hexcore/data/open_useful_objectives/state.json",
        state_path=tmp_path / "learning.json", result_path=tmp_path / "result.json",
    )
    assert result["passed"] is True
    assert result["gate"]["distinct_authority_programs"] == 5
    assert result["gate"]["independent_outcomes_passed"] == 5
    assert result["gate"]["counterexamples_rejected"] == 5
    assert result["gate"]["supplied_family_labels"] == 0
    assert result["gate"]["supplied_verifiers"] == 0
    assert result["gate"]["hidden_fields_visible_to_inventor"] == 0
    assert result["gate"]["ood_abstention"] is True
    assert result["gate"]["restart_champion_retained"] is True
