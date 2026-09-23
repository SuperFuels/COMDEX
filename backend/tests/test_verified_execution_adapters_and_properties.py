from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ADAPTERS = ROOT / "results/hexcore_verified_execution_adapter_acquisition.json"
PROPERTIES = ROOT / "results/hexcore_adapter_grounded_property_invention.json"


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_execution_adapters_are_source_attested_and_promoted() -> None:
    result = _read(ADAPTERS)
    gate = result["gate"]
    assert result["passed"] is True
    assert gate["accepted"] is True
    assert gate["verified_adapters"] == gate["repositories"] == 3
    assert gate["weakest_repository_success"] == 1.0
    assert gate["source_path_attestation"] is True
    assert gate["human_patch_and_hidden_tests_absent"] is True
    assert gate["unsafe_adapter_programs_executed"] == 0
    assert gate["timeouts"] == 0
    assert result["restart"]["adapters_retained"] is True
    assert result["restart"]["champion_retained"] is True


def test_each_adapter_binds_a_real_repository_target() -> None:
    result = _read(ADAPTERS)
    assert {row["repo_name"] for row in result["outcomes"]} == {
        "marshmallow",
        "pydicom",
        "pvlib-python",
    }
    for row in result["outcomes"]:
        assert row["adapter_verified"] is True
        assert row["selected"]["execution"]["passed"] is True
        assert "AION_ADAPTER_REACHED" in row["selected"]["execution"]["stdout"]


def test_adapter_grounded_properties_pass_the_complete_causal_gate() -> None:
    result = _read(PROPERTIES)
    gate = result["gate"]
    assert result["passed"] is True
    assert gate["accepted"] is True
    assert gate["verified_adapters"] == 3
    assert gate["end_to_end_success"] == 1.0
    assert gate["weakest_repository_success"] == 1.0
    assert gate["originals_rejected"] == 3
    assert gate["candidates_accepted"] == 3
    assert gate["adversarial_programs_accepted"] == 3
    assert gate["unsafe_programs_executed"] == 0
    assert gate["timeouts"] == 0
    assert gate["live_sources_unchanged"] is True


def test_property_programs_survive_restart_without_relearning() -> None:
    result = _read(PROPERTIES)
    assert result["restart"] == {
        "champion_retained": True,
        "programs_retained": True,
        "relearning_failures": 0,
        "session_retained": True,
    }
    assert result["promotion"]["decision"]["promoted"] is True
