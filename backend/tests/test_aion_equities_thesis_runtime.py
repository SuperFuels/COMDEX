from __future__ import annotations

from backend.modules.aion_equities.pilot_company_seed import PilotCompanySeedStore
from backend.modules.aion_equities.thesis_runtime import ThesisRuntime


class _FakeThesisStore:
    def __init__(self) -> None:
        self.items = {}

    def save_thesis(self, payload):
        self.items[payload["thesis_id"]] = payload
        return payload


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


def test_thesis_runtime_builds_active_long_thesis(tmp_path):
    seed_store = PilotCompanySeedStore(tmp_path)
    thesis_store = _FakeThesisStore()
    _setup_company_seed(seed_store)

    runtime = ThesisRuntime(
        pilot_company_seed_store=seed_store,
        thesis_store=thesis_store,
    )

    assessment = {
        "assessment_id": "assessment/company/ULVR.L/2026-Q4",
        "scores": {
            "business_quality_score": 82.0,
            "analytical_confidence_score": 78.0,
            "automation_opportunity_score": 61.0,
        },
        "risk_flags": [],
        "predictability_context": {
            "acs_band": "high",
            "sector_confidence_tier": "tier_1",
        },
    }

    out = runtime.build_thesis(
        company_ref="company/ULVR.L",
        assessment=assessment,
        trigger_map_ref="company/ULVR.L/trigger_map/2026Q4",
        quarter_event_ref="company/ULVR.L/quarter_event/2026Q4",
        write_to_store=True,
        write_to_kg=False,
        write_to_sqi_container=False,
    )

    assert out["status"] == "active"
    assert out["mode"] == "long"
    assert out["conviction"]["score"] > 60.0
    assert out["linked_refs"]["company_ref"] == "company/ULVR.L"
    assert out["linked_refs"]["trigger_map_ref"] == "company/ULVR.L/trigger_map/2026Q4"
    assert out["thesis_id"] in thesis_store.items


def test_thesis_runtime_downgrades_when_risk_flags_accumulate(tmp_path):
    seed_store = PilotCompanySeedStore(tmp_path)
    _setup_company_seed(seed_store)

    runtime = ThesisRuntime(
        pilot_company_seed_store=seed_store,
        thesis_store=_FakeThesisStore(),
    )

    assessment = {
        "assessment_id": "assessment/company/ULVR.L/2027-Q1",
        "scores": {
            "business_quality_score": 51.0,
            "analytical_confidence_score": 58.0,
            "automation_opportunity_score": 44.0,
        },
        "risk_flags": [
            "elevated_net_debt",
            "thin_operating_margin",
            "negative_guidance_drift",
        ],
        "predictability_context": {
            "acs_band": "high",
            "sector_confidence_tier": "tier_1",
        },
    }

    out = runtime.build_thesis(
        company_ref="company/ULVR.L",
        assessment=assessment,
        write_to_store=False,
        write_to_kg=False,
        write_to_sqi_container=False,
    )

    assert out["status"] in {"watch", "inactive"}
    assert out["decision_context"]["risk_penalty"] >= 24.0


def test_thesis_runtime_can_write_to_real_bridges(tmp_path):
    seed_store = PilotCompanySeedStore(tmp_path)
    _setup_company_seed(seed_store)

    runtime = ThesisRuntime(
        pilot_company_seed_store=seed_store,
        thesis_store=_FakeThesisStore(),
    )

    assessment = {
        "assessment_id": "assessment/company/ULVR.L/2026-Q4",
        "scores": {
            "business_quality_score": 80.0,
            "analytical_confidence_score": 76.0,
            "automation_opportunity_score": 63.0,
        },
        "risk_flags": [],
        "predictability_context": {
            "acs_band": "high",
            "sector_confidence_tier": "tier_1",
        },
    }

    out = runtime.run_first_pass_for_company(
        company_ref="company/ULVR.L",
        assessment=assessment,
        trigger_map_ref="company/ULVR.L/trigger_map/2026Q4",
        quarter_event_ref="company/ULVR.L/quarter_event/2026Q4",
        write_to_store=True,
        write_to_kg=True,
        write_to_sqi_container=True,
    )

    assert out["thesis_id"] == "thesis/ULVR.L/long/medium_term"
    assert out["conviction"]["band"] in {"medium", "high"}


def test_thesis_runtime_preserves_predictability_context(tmp_path):
    seed_store = PilotCompanySeedStore(tmp_path)
    _setup_company_seed(seed_store)

    runtime = ThesisRuntime(
        pilot_company_seed_store=seed_store,
        thesis_store=_FakeThesisStore(),
    )

    assessment = {
        "assessment_id": "assessment/company/ULVR.L/2026-Q4",
        "scores": {
            "business_quality_score": 80.0,
            "analytical_confidence_score": 76.0,
            "automation_opportunity_score": 63.0,
        },
        "risk_flags": [],
        "predictability_context": {
            "acs_band": "high",
            "sector_confidence_tier": "tier_1",
        },
    }

    out = runtime.build_thesis(
        company_ref="company/ULVR.L",
        assessment=assessment,
        write_to_store=False,
        write_to_kg=False,
        write_to_sqi_container=False,
    )

    assert out["predictability_context"]["acs_band"] == "high"
    assert out["predictability_context"]["sector_confidence_tier"] == "tier_1"