# backend/tests/test_aion_equities_openai_context_packet_builder.py
from __future__ import annotations

from backend.modules.aion_equities.openai_context_packet_builder import OpenAIContextPacketBuilder
from backend.modules.aion_equities.openai_operating_brief_store import OpenAIOperatingBriefStore


def test_openai_context_packet_builder_uses_active_brief(tmp_path):
    brief_store = OpenAIOperatingBriefStore(tmp_path)
    brief_store.save_operating_brief(
        brief_id="briefs/active",
        version="v2",
        title="Active Brief",
        summary="Active summary",
        sections=[{"id": "constraints", "title": "Constraints", "body": "No leverage."}],
        generated_by="pytest",
        set_active=True,
    )

    builder = OpenAIContextPacketBuilder(operating_brief_store=brief_store)

    packet = builder.build_context_packet(
        proposal_id="proposal/ULVR.L/2026-Q4",
        requested_action="review_trade",
        business_status={"total_capital": 100000, "free_cash": 50000},
        company_intelligence_pack={"company_ref": "company/ULVR.L"},
        proposal_packet={"trade_type": "fundamental_long"},
    )

    assert packet["proposal_id"] == "proposal/ULVR.L/2026-Q4"
    assert packet["requested_action"] == "review_trade"
    assert packet["operating_brief"]["brief_id"] == "briefs/active"
    assert packet["runtime_notes"]["operating_brief_version"] == "v2"


def test_openai_context_packet_builder_can_override_brief_id(tmp_path):
    brief_store = OpenAIOperatingBriefStore(tmp_path)
    brief_store.save_operating_brief(
        brief_id="briefs/a",
        version="v1",
        title="A",
        summary="A",
        sections=[{"id": "a", "title": "A", "body": "A"}],
        generated_by="pytest",
        set_active=True,
    )
    brief_store.save_operating_brief(
        brief_id="briefs/b",
        version="v2",
        title="B",
        summary="B",
        sections=[{"id": "b", "title": "B", "body": "B"}],
        generated_by="pytest",
        set_active=False,
    )

    builder = OpenAIContextPacketBuilder(operating_brief_store=brief_store)

    packet = builder.build_context_packet(
        proposal_id="proposal/TEST",
        requested_action="review_trade",
        business_status={},
        company_intelligence_pack={},
        proposal_packet={},
        operating_brief_id="briefs/b",
    )

    assert packet["operating_brief"]["brief_id"] == "briefs/b"
    assert packet["operating_brief"]["version"] == "v2"