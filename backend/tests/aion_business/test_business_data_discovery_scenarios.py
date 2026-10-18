from pathlib import Path

from backend.modules.aion_business.runtime.business_data_discovery_scenarios import (
    load_discovery_scenario_catalogue,
)


ROOT = Path(__file__).resolve().parents[3]


def test_discovery_catalogue_covers_every_required_session_and_registered_domain():
    result = load_discovery_scenario_catalogue(
        catalogue_path=ROOT / "config/business-data-discovery-scenarios.v1.json",
        manifest_path=ROOT / "config/business-data-manifest.v1.json",
    )
    assert result["complete"] is True
    assert result["scenario_count"] == 28
    indexed = {item["session_id"]: item for item in result["scenarios"]}
    assert "business.map" in indexed["boardroom-business-maps"]["expected_domains"]
    assert "departments.map" in indexed["boardroom-business-maps"]["expected_domains"]
    assert "onboarding.foundation_session" in indexed["business-onboarding"]["expected_domains"]
    assert "train_agent.automations" in indexed["automations-schedules"]["expected_domains"]
    assert "file_cabinet.originals" in indexed["files-documents"]["expected_domains"]
    assert "billing_control_plane" in indexed["billing-photon"]["expected_external_classes"]
