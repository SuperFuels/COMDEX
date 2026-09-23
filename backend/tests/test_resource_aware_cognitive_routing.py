from pathlib import Path

from backend.modules.hexcore.resource_aware_cognitive_routing import run


def test_resource_route_transfers_and_rejects_spoofed_lightweight_authority(tmp_path: Path) -> None:
    result = run(result_path=tmp_path / "result.json", champion_path=tmp_path / "champion.json")
    assert result["passed"] is True
    assert result["selected"] == "authority_scoped_specialist"
    assert result["gate"]["legitimate_transfers"] == 3
    assert result["gate"]["protected_full_cognition"] == 3
    assert result["gate"]["spoofed_routes_rejected"] == 6
    assert result["gate"]["heavy_components_initialized_in_probe"] == 0
    assert (tmp_path / "champion.json").exists()
