from pathlib import Path

import pytest

from backend.modules.hexcore.shortlist_free_remote_authority_acquisition import close_later_challenge, run


@pytest.mark.network
def test_remote_authority_is_discovered_without_catalogue(tmp_path: Path) -> None:
    result = run(state_path=tmp_path / "state.json", result_path=tmp_path / "result.json",
                 minimum_later_delay_seconds=300)
    assert result["passed"] is True
    assert result["gate"]["supplied_source_catalogues"] == 0
    assert result["gate"]["typed_remote_adapters"] == 1
    assert result["gate"]["source_disjoint_transfer_success"] == 1
    assert result["gate"]["malicious_remote_candidates_rejected"] == result["gate"]["malicious_remote_candidates_total"]
    assert result["gate"]["later_retention_credit"] == 0
    import json
    state = json.loads((tmp_path / "state.json").read_text())
    state["later_challenge"]["not_before_epoch"] = 0
    (tmp_path / "state.json").write_text(json.dumps(state))
    closed = close_later_challenge(state_path=tmp_path / "state.json", result_path=tmp_path / "result.json")
    assert closed["gate"]["later_retention_credit"] == 1
    assert closed["later_challenge"]["status"] == "CONSEQUENCE_CONFIRMED"
