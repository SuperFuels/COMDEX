from __future__ import annotations

from backend.modules.aion_equities.assessment_runtime import AssessmentRuntime
from backend.modules.aion_equities.assessment_store import AssessmentStore
from backend.modules.aion_equities.company_intelligence_snapshot_loader import CompanyIntelligenceSnapshotLoader
from backend.modules.aion_equities.company_trigger_map_store import CompanyTriggerMapStore
from backend.modules.aion_equities.pilot_company_seed import PilotCompanySeedStore
from backend.modules.aion_equities.quarter_event_store import QuarterEventStore
from backend.modules.aion_equities.thesis_runtime import ThesisRuntime
from backend.modules.aion_equities.thesis_store import ThesisStore
from backend.modules.aion_equities.variable_watch_store import VariableWatchStore


def test_company_intelligence_snapshot_loader_one_pass(tmp_path):
    seed_store = PilotCompanySeedStore(base_dir=tmp_path)
    qe_store = QuarterEventStore(base_dir=tmp_path)
    tm_store = CompanyTriggerMapStore(base_dir=tmp_path)
    vw_store = VariableWatchStore(base_dir=tmp_path)
    assessment_store = AssessmentStore(base_dir=tmp_path)
    thesis_store = ThesisStore(base_dir=tmp_path)

    seed_store.save_company_seed(
        company_ref="company/AHT.L",
        company_id="company/AHT.L",
        ticker="AHT.L",
        name="Ashtead",
        sector="plant_hire",
        country="UK",
        predictability_profile={"acs_band": "high", "sector_confidence_tier": "tier_1"},
    )

    # quarter event (intake/simple path)
    qe = qe_store.save_quarter_event(
        company_ref="company/AHT.L",
        document_ref="document/AHT.L/2026-Q1",
        quarter_event={
            "fiscal_period": "2026-Q1",
            "published_at": "2026-06-18",
            "headline": "Q1 update",
            "summary": "Trading in line",
            "key_numbers": {"revenue": 1000.0, "ebit": 120.0, "free_cash_flow": 80.0, "net_debt": 2000.0},
        },
    )

    # trigger map
    tm = tm_store.save_company_trigger_map(
        company_ref="company/AHT.L",
        fiscal_period_ref="2026-Q1",
        trigger_entries=[{"trigger_id": "t1", "variable_name": "utilisation"}],
        validate=False,
    )

    # variable watch
    vw = vw_store.save_variable_watch(
        company_ref="company/AHT.L",
        fiscal_period_ref="2026-Q1",
        variable_watch_seed={"variables": ["utilisation"]},
    )

    # assessment + thesis
    ar = AssessmentRuntime(pilot_company_seed_store=seed_store, quarter_event_store=qe_store)
    assessment = ar.build_assessment(company_ref="company/AHT.L", quarter_event_id=qe["quarter_event_id"])
    assessment_store.save_assessment_payload(assessment, validate=False)

    tr = ThesisRuntime(pilot_company_seed_store=seed_store)
    thesis = tr.build_thesis(
        company_ref="company/AHT.L",
        assessment=assessment,
        mode="long",
        window="medium_term",
        trigger_map_ref=tm["company_trigger_map_id"],
        quarter_event_ref=qe["quarter_event_id"],
        write_to_store=False,
        write_to_kg=False,
        write_to_sqi_container=False,
    )
    thesis_store.save_thesis(thesis, validate=False)

    # update company refs
    seed_store.save_company_seed(
        company_ref="company/AHT.L",
        company_id="company/AHT.L",
        ticker="AHT.L",
        name="Ashtead",
        sector="plant_hire",
        country="UK",
        payload_patch={
            "latest_assessment_ref": assessment["assessment_id"],
            "active_thesis_refs": [thesis["thesis_id"]],
            "quarter_event_refs": [qe["quarter_event_id"]],
            "trigger_map_refs": [tm["company_trigger_map_id"]],
            "variable_watch_refs": [vw["variable_watch_id"]],
        },
    )

    loader = CompanyIntelligenceSnapshotLoader(
        pilot_company_seed_store=seed_store,
        assessment_store=assessment_store,
        thesis_store=thesis_store,
        quarter_event_store=qe_store,
        trigger_map_store=tm_store,
        variable_watch_store=vw_store,
    )

    snap = loader.load_snapshot(company_ref="company/AHT.L")

    assert snap["company"]["company_ref"] == "company/AHT.L"
    assert snap["assessment"]["assessment_id"] == assessment["assessment_id"]
    assert len(snap["theses"]) == 1
    assert snap["theses"][0]["thesis_id"] == thesis["thesis_id"]
    assert len(snap["quarter_events"]) == 1
    assert snap["trigger_map"]["company_trigger_map_id"] == tm["company_trigger_map_id"]
    assert snap["variable_watch"]["variable_watch_id"] == vw["variable_watch_id"]