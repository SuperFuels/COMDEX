from __future__ import annotations

from backend.modules.aion_equities.pilot_company_seed import PilotCompanySeedStore
from backend.modules.aion_equities.reference_maintenance_runtime import (
    ReferenceMaintenanceRuntime,
)


def _setup_company_seed(seed_store: PilotCompanySeedStore) -> None:
    seed_store.save_company_seed(
        company_id="company/ULVR.L",
        ticker="ULVR.L",
        name="Unilever PLC",
        sector="consumer_staples",
        country="GB",
        generated_by="pytest",
        payload_patch={
            "sector_template_ref": "sector/consumer_staples",
            "fingerprint_ref": "company/ULVR.L/fingerprint/core",
            "credit_profile_ref": "company/ULVR.L/credit",
            "pair_context_ref": "pair_context/uk_europe_consumer",
            "predictability_profile": {
                "acs_band": "high",
                "sector_confidence_tier": "tier_1",
            },
        },
    )


def test_reference_maintenance_updates_latest_assessment_and_active_thesis(tmp_path):
    seed_store = PilotCompanySeedStore(tmp_path)
    _setup_company_seed(seed_store)

    runtime = ReferenceMaintenanceRuntime(pilot_company_seed_store=seed_store)

    out = runtime.update_company_references(
        company_ref="company/ULVR.L",
        latest_assessment_ref="assessment/company/ULVR.L/2026-Q4",
        active_thesis_refs=["thesis/ULVR.L/long/medium_term"],
    )

    assert out["latest_assessment_ref"] == "assessment/company/ULVR.L/2026-Q4"
    assert out["active_thesis_refs"] == ["thesis/ULVR.L/long/medium_term"]


def test_reference_maintenance_appends_quarter_event_refs(tmp_path):
    seed_store = PilotCompanySeedStore(tmp_path)
    _setup_company_seed(seed_store)

    runtime = ReferenceMaintenanceRuntime(pilot_company_seed_store=seed_store)

    runtime.update_company_references(
        company_ref="company/ULVR.L",
        quarter_event_ref="quarter_event/ULVR.L/2026-Q3",
    )
    out = runtime.update_company_references(
        company_ref="company/ULVR.L",
        quarter_event_ref="quarter_event/ULVR.L/2026-Q4",
    )

    assert out["quarter_event_refs"] == [
        "quarter_event/ULVR.L/2026-Q4",
        "quarter_event/ULVR.L/2026-Q3",
    ]


def test_reference_maintenance_refresh_from_runtime_objects(tmp_path):
    seed_store = PilotCompanySeedStore(tmp_path)
    _setup_company_seed(seed_store)

    runtime = ReferenceMaintenanceRuntime(pilot_company_seed_store=seed_store)

    assessment = {"assessment_id": "assessment/company/ULVR.L/2026-Q4"}
    thesis = {
        "thesis_id": "thesis/ULVR.L/long/medium_term",
        "status": "active",
    }
    quarter_event = {"quarter_event_id": "quarter_event/ULVR.L/2026-Q4"}

    out = runtime.refresh_from_runtime_objects(
        company_ref="company/ULVR.L",
        assessment=assessment,
        thesis=thesis,
        quarter_event=quarter_event,
        catalyst_event_ref="catalyst/ULVR.L/price_reset",
    )

    assert out["latest_assessment_ref"] == "assessment/company/ULVR.L/2026-Q4"
    assert out["active_thesis_refs"] == ["thesis/ULVR.L/long/medium_term"]
    assert out["quarter_event_refs"] == ["quarter_event/ULVR.L/2026-Q4"]
    assert out["catalyst_event_refs"] == ["catalyst/ULVR.L/price_reset"]


def test_reference_maintenance_preserves_predictability_profile(tmp_path):
    seed_store = PilotCompanySeedStore(tmp_path)
    _setup_company_seed(seed_store)

    runtime = ReferenceMaintenanceRuntime(pilot_company_seed_store=seed_store)

    out = runtime.update_company_references(
        company_ref="company/ULVR.L",
        latest_assessment_ref="assessment/company/ULVR.L/2026-Q4",
    )

    assert out["predictability_profile"]["acs_band"] == "high"
    assert out["predictability_profile"]["sector_confidence_tier"] == "tier_1"