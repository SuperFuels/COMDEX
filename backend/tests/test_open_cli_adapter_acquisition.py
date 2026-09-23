from pathlib import Path

import pytest

from backend.modules.hexcore.open_cli_adapter_acquisition import TOOLS, run


@pytest.mark.skipif(any(__import__("shutil").which(tool) is None for tool in TOOLS), reason="CLI cohort unavailable")
def test_cli_adapters_are_discovered_secured_transferred_and_retained(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    result = run(repo_root=root, state_path=tmp_path / "registry.json", result_path=tmp_path / "result.json")
    assert result["passed"] is True
    assert result["gate"]["typed_adapters_invented"] == 3
    assert result["gate"]["source_disjoint_transfer_success"] == 3
    assert result["gate"]["malicious_adapters_rejected"] == result["gate"]["malicious_adapters_total"]
    assert result["gate"]["unsafe_executions"] == 0
    assert result["restart"]["contracts_retained"] is True
