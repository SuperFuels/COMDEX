from __future__ import annotations

from backend.modules.aion_equities.assessment_runtime import AssessmentRuntime
from backend.modules.aion_equities.pilot_company_seed import PilotCompanySeedStore
from backend.modules.aion_equities.quarter_event_store import QuarterEventStore


def _setup_company_seed(seed_store: PilotCompanySeedStore) -> None:
    seed_store.save_company_seed(
        company_ref="company/ULVR.L",
        company_id="company/ULVR.L",
        ticker="ULVR.L",
        name="Unilever PLC",
        sector="consumer_staples",
        country="GB",
        sector_template_ref="sector/consumer_staples",
        fingerprint_ref="company/ULVR.L/fingerprint/core",
        credit_profile_ref="company/ULVR.L/credit",
        pair_context_ref="pair_context/uk_europe_consumer",
        predictability_profile={
            "acs_band": "high",
            "sector_confidence_tier": "tier_1",
        },
        generated_by="pytest",
        validate=False,
    )


def _setup_quarter_event(event_store: QuarterEventStore) -> str:
    payload = event_store.save_quarter_event(
        ticker="ULVR.L",
        fiscal_year=2026,
        fiscal_quarter=4,
        as_reported_date="2026-12-20",
        created_by="pytest",
        document_refs=["company/ULVR.L/document/2026-Q4-report"],
        source_hashes=["sha256:testhash"],
        financials={
            "revenue": 15500.0,
            "ebit": 2550.0,
            "free_cash_flow": 980.0,
            "net_debt": 1450.0,
            "guidance_delta": 6.0,
        },
        narrative_summary="Stable demand profile with selective margin expansion.",
        validate=False,
    )
    return payload["quarter_event_id"]


def test_assessment_runtime_builds_assessment(tmp_path):
    seed_store = PilotCompanySeedStore(tmp_path)
    event_store = QuarterEventStore(tmp_path)

    _setup_company_seed(seed_store)
    quarter_event_id = _setup_quarter_event(event_store)

    runtime = AssessmentRuntime(
        pilot_company_seed_store=seed_store,
        quarter_event_store=event_store,
    )

    out = runtime.build_assessment(
        company_ref="company/ULVR.L",
        quarter_event_id=quarter_event_id,
        thesis_ref="thesis/ULVR.L/long/medium_term",
        write_to_kg=False,
        write_to_sqi_container=False,
    )

    assert out["entity_id"] == "company/ULVR.L"
    assert out["scores"]["business_quality_score"] > 0.0
    assert out["scores"]["analytical_confidence_score"] > 0.0
    assert out["linked_refs"]["quarter_event_ref"] == quarter_event_id


def test_assessment_runtime_flags_risk_on_negative_profile(tmp_path):
    seed_store = PilotCompanySeedStore(tmp_path)
    event_store = QuarterEventStore(tmp_path)

    _setup_company_seed(seed_store)
    payload = event_store.save_quarter_event(
        ticker="ULVR.L",
        fiscal_year=2027,
        fiscal_quarter=1,
        as_reported_date="2027-03-31",
        created_by="pytest",
        document_refs=["company/ULVR.L/document/2027-Q1-report"],
        source_hashes=["sha256:testhash2"],
        financials={
            "revenue": 10000.0,
            "ebit": 500.0,
            "free_cash_flow": 100.0,
            "net_debt": 3200.0,
            "guidance_delta": -8.0,
        },
        narrative_summary="",
        validate=False,
    )

    runtime = AssessmentRuntime(
        pilot_company_seed_store=seed_store,
        quarter_event_store=event_store,
    )

    out = runtime.build_assessment(
        company_ref="company/ULVR.L",
        quarter_event_id=payload["quarter_event_id"],
        write_to_kg=False,
        write_to_sqi_container=False,
    )

    assert "elevated_net_debt" in out["risk_flags"]
    assert "thin_operating_margin" in out["risk_flags"]
    assert "negative_guidance_drift" in out["risk_flags"]


def test_assessment_runtime_can_write_to_real_bridges(tmp_path):
    seed_store = PilotCompanySeedStore(tmp_path)
    event_store = QuarterEventStore(tmp_path)

    _setup_company_seed(seed_store)
    quarter_event_id = _setup_quarter_event(event_store)

    runtime = AssessmentRuntime(
        pilot_company_seed_store=seed_store,
        quarter_event_store=event_store,
    )

    out = runtime.run_first_pass_for_company(
        company_ref="company/ULVR.L",
        quarter_event_id=quarter_event_id,
        thesis_ref="thesis/ULVR.L/long/medium_term",
        write_to_kg=True,
        write_to_sqi_container=True,
    )

    assert out["scores"]["business_quality_score"] > 0.0
    assert out["scores"]["analytical_confidence_score"] > 0.0


def test_assessment_runtime_preserves_predictability_context(tmp_path):
    seed_store = PilotCompanySeedStore(tmp_path)
    event_store = QuarterEventStore(tmp_path)

    _setup_company_seed(seed_store)
    quarter_event_id = _setup_quarter_event(event_store)

    runtime = AssessmentRuntime(
        pilot_company_seed_store=seed_store,
        quarter_event_store=event_store,
    )

    out = runtime.build_assessment(
        company_ref="company/ULVR.L",
        quarter_event_id=quarter_event_id,
        write_to_kg=False,
        write_to_sqi_container=False,
    )

    assert out["predictability_context"]["acs_band"] == "high"
    assert out["predictability_context"]["sector_confidence_tier"] == "tier_1"