import pytest

from backend.modules.aion_business.runtime.creative_publication_service import CreativePublicationService
from backend.modules.aion_business.runtime.local_asset_store import LocalAssetStore


def test_publication_package_is_hash_bound_and_external_execution_remains_closed(tmp_path):
    asset = tmp_path / "finished.mp4"
    asset.write_bytes(b"owned-video-evidence")
    service = CreativePublicationService(LocalAssetStore(root_dir=tmp_path / "tessaris"))
    package = service.prepare("demo", {
        "asset_path": str(asset), "channel": "instagram", "mode": "organic",
        "caption": "A verified campaign caption.", "call_to_action": "Request a quote",
    })
    assert package["status"] == "prepared"
    assert package["external_execution_available"] is False
    with pytest.raises(PermissionError):
        service.approve("demo", package["id"], {
            "expected_approval_hash": package["approval_hash"], "approved_by_person_id": "owner",
            "maximum_total_spend_eur": 0, "external_publish_authorized": False,
        })
    approved = service.approve("demo", package["id"], {
        "expected_approval_hash": package["approval_hash"], "approved_by_person_id": "owner",
        "maximum_total_spend_eur": 0, "external_publish_authorized": True,
    })
    assert approved["status"] in {"approved_waiting_connector", "approved_ready_for_validate_only"}


def test_campaign_outcomes_calculate_real_efficiency_and_escalate_false_claims(tmp_path):
    asset = tmp_path / "finished.mp4"
    asset.write_bytes(b"owned-video-evidence")
    service = CreativePublicationService(LocalAssetStore(root_dir=tmp_path / "tessaris"))
    package = service.prepare("demo", {
        "asset_path": str(asset), "channel": "meta_ads", "mode": "paid",
        "caption": "A verified campaign caption.", "daily_budget_eur": 10,
    })
    measured = service.record_outcome("demo", package["id"], {
        "impressions": 1000, "clicks": 50, "qualified_actions": 10, "conversions": 2,
        "spend_eur": 100, "revenue_eur": 400, "false_or_unsafe_claims": 1,
    })
    outcome = measured["latest_outcome"]
    assert outcome["ctr"] == 0.05
    assert outcome["cost_per_qualified_action"] == 10
    assert outcome["roas"] == 4
    assert measured["status"] == "measurement_escalated"
