from __future__ import annotations

from backend.modules.aion_equities.assessment_runtime import AssessmentRuntime
from backend.modules.aion_equities.assessment_store import AssessmentStore
from backend.modules.aion_equities.company_intelligence_snapshot_loader import CompanyIntelligenceSnapshotLoader
from backend.modules.aion_equities.company_trigger_map_store import CompanyTriggerMapStore
from backend.modules.aion_equities.openai_context_packet_builder import OpenAIContextPacketBuilder
from backend.modules.aion_equities.openai_operating_brief_store import OpenAIOperatingBriefStore
from backend.modules.aion_equities.pilot_company_seed import PilotCompanySeedStore
from backend.modules.aion_equities.quarter_event_store import QuarterEventStore
from backend.modules.aion_equities.thesis_runtime import ThesisRuntime
from backend.modules.aion_equities.thesis_store import ThesisStore
from backend.modules.aion_equities.variable_watch_store import VariableWatchStore


def test_context_packet_builder_uses_snapshot_loader_when_pack_missing(tmp_path):
    brief_store = OpenAIOperatingBriefStore(base_dir=tmp_path)
    saved = brief_store.save_operating_brief(
        brief_id="brief/aion_equities_default",
        version="v1",
        title="AION Equities",
        summary="Operating brief",
        sections=[{"title": "Role", "content": "Trade review"}],
    )
    brief_store.set_active_brief(saved["brief_id"])

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

    qe = qe_store.save_quarter_event(
        company_ref="company/AHT.L",
        document_ref="document/AHT.L/2026-Q1",
        quarter_event={
            "fiscal_period": "2026-Q1",
            "published_at": "2026-06-18",
            "headline": "Q1 update",
            "summary": "Trading in line",
            "key_numbers": {"revenue": 1000.0, "ebit": 120.0},
        },
    )
    tm = tm_store.save_company_trigger_map(
        company_ref="company/AHT.L",
        fiscal_period_ref="2026-Q1",
        trigger_entries=[{"trigger_id": "t1", "variable_name": "utilisation"}],
        validate=False,
    )
    vw = vw_store.save_variable_watch(
        company_ref="company/AHT.L",
        fiscal_period_ref="2026-Q1",
        variable_watch_seed={"variables": ["utilisation"]},
    )

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

    builder = OpenAIContextPacketBuilder(
        operating_brief_store=brief_store,
        company_snapshot_loader=loader,
    )

    packet = builder.build_context_packet(
        company_ref="company/AHT.L",
        proposal_id="proposal/test",
        review_id="review/test",
        requested_action="review_trade",
        # NOTE: no company_intelligence_pack passed
        proposal_packet={"proposal_id": "proposal/test", "requested_action": "review_trade"},
    )

    assert packet["company_intelligence_pack"]["company_ref"] == "company/AHT.L"
    assert packet["company_intelligence_pack"]["assessment"]["assessment_id"] == assessment["assessment_id"]