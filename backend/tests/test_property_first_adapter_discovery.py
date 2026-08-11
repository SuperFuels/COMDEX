from pathlib import Path

import pytest

from backend.modules.hexcore.property_first_adapter_discovery import run


@pytest.mark.skipif(not Path("/usr/bin/apropos").exists(), reason="local manual index unavailable")
def test_property_first_shortlist_free_discovery(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    result = run(repo_root=root, state_path=tmp_path / "registry.json", result_path=tmp_path / "result.json")
    assert result["passed"] is True
    assert result["gate"]["properties_formulated"] == 3
    assert result["gate"]["supplied_tool_shortlists"] == 0
    assert result["gate"]["supplied_requirement_labels"] == 0
    assert result["gate"]["source_disjoint_transfer_success"] == 3
    assert result["gate"]["ambiguous_objective_abstention"] is True
    assert result["gate"]["malicious_candidates_rejected"] == result["gate"]["malicious_candidates_total"]
    assert result["restart"]["champion_retained"] is True
