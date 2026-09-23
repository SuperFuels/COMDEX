from pathlib import Path

from backend.modules.hexcore.open_tool_environment_acquisition import (
    AdapterInventor,
    _fingerprint,
    run,
)


def test_content_fingerprint_ignores_filename_and_suffix():
    content = '{"x":1}\n{"x":2}\n'
    assert _fingerprint(content) == _fingerprint(content)
    assert _fingerprint(content) != _fingerprint('[{"x":1},{"x":2}]')


def test_security_scanner_rejects_every_privileged_operation(tmp_path: Path):
    inventor = AdapterInventor(tmp_path / "registry.json")
    for operation in ("eval", "exec", "subprocess", "shell", "network", "write", "import_dynamic"):
        assert inventor.security_scan({"operations": [operation]}) is False
    assert inventor.security_scan({"operations": ["split_lines", "parse_json"]}) is True


def test_open_tool_acquisition_transfers_repairs_and_persists(tmp_path: Path):
    result = run(workspace_root=tmp_path / "campaign", result_path=tmp_path / "result.json")

    assert result["passed"] is True
    assert result["gate"]["verified_outcomes"] == 9
    assert result["gate"]["source_disjoint_transfers"] == 4
    assert result["gate"]["invented_adapter_types"] == 5
    assert result["gate"]["transfer_attempt_reduction"] >= 0.50
    assert result["gate"]["drift_detected_and_repaired"] is True
    assert result["gate"]["malicious_adapters_rejected"] == result["gate"]["malicious_adapters_total"]
    assert result["gate"]["unsafe_execution"] == 0
    assert result["restart"]["relearning_tasks"] == 0
