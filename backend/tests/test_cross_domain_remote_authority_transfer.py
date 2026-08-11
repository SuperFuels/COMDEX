from pathlib import Path

import pytest

from backend.modules.hexcore.cross_domain_remote_authority_transfer import close_later_challenges, run


@pytest.mark.network
def test_remote_acquisition_method_transfers_to_unrelated_domains(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    result = run(parent_result_path=root / "results/hexcore_shortlist_free_remote_authority_acquisition.json",
                 state_path=tmp_path / "state.json", result_path=tmp_path / "result.json", minimum_later_delay_seconds=300)
    assert result["passed"] is True
    assert result["gate"]["successful_remote_acquisitions"] == 2
    assert result["gate"]["distinct_authority_domains"] == 2
    assert result["gate"]["supplied_source_catalogues"] == 0
    assert result["gate"]["search_to_adapter_attempt_reduction_vs_actual_parent"] >= .70
    assert result["gate"]["later_retention_credits"] == 0
    import json
    state = json.loads((tmp_path / "state.json").read_text())
    for row in state["episodes"]:
        row["later_challenge"]["not_before_epoch"] = 0
    (tmp_path / "state.json").write_text(json.dumps(state))
    closed = close_later_challenges(state_path=tmp_path / "state.json", result_path=tmp_path / "result.json")
    assert closed["gate"]["later_retention_credits"] == 2
    assert all(row["status"] == "CONSEQUENCE_CONFIRMED" for row in closed["later_challenges"])
