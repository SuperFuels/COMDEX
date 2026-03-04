# backend/tests/test_aion_equities_openai_trade_review_runtime.py
from __future__ import annotations

from backend.modules.aion_equities.decision_notes_store import DecisionNotesStore
from backend.modules.aion_equities.execution_instruction_store import ExecutionInstructionStore
from backend.modules.aion_equities.openai_context_packet_builder import OpenAIContextPacketBuilder
from backend.modules.aion_equities.openai_operating_brief_store import OpenAIOperatingBriefStore
from backend.modules.aion_equities.openai_trade_review_runtime import OpenAITradeReviewRuntime


def _fake_openai_callable(_packet):
    return {
        "decision_notes": {
            "summary": "Approve; triggers satisfied; tranche plan recommended.",
            "risks": ["fx", "macro"],
            "invalidation": ["guidance cut", "margin collapse"],
        },
        "execution_instruction": {
            "approve_trade": True,
            "trade_type": "fundamental_long",
            "entry_method": "tranche_plan",
            "size_percent": 20,
            "max_capital_allowed": 20000,
            "required_human_approval": True,
            "stop_style": "thesis_based",
            "expires_at": "2099-01-01T00:00:00Z",
        },
    }


def test_openai_trade_review_runtime_writes_two_documents(tmp_path):
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
    decision_notes_store = DecisionNotesStore(tmp_path)
    instruction_store = ExecutionInstructionStore(tmp_path)

    runtime = OpenAITradeReviewRuntime(
        context_packet_builder=builder,
        decision_notes_store=decision_notes_store,
        execution_instruction_store=instruction_store,
        openai_callable=_fake_openai_callable,
    )

    out = runtime.review_trade_proposal(
        review_id="review/1",
        proposal_id="proposal/ULVR.L/2026-Q4",
        company_ref="company/ULVR.L",
        thesis_ref="thesis/ULVR.L/long/medium_term",
        requested_action="review_trade",
        business_status={"total_capital": 100000, "free_cash": 50000},
        company_intelligence_pack={"company_ref": "company/ULVR.L"},
        proposal_packet={"trade_type": "fundamental_long"},
    )

    assert out["decision_notes_ref"].startswith("decision_notes/")
    assert out["execution_instruction_ref"].startswith("execution_instruction/")

    dn_loaded = decision_notes_store.load_decision_notes(out["decision_notes_ref"])
    assert dn_loaded["decision_notes"]["summary"].startswith("Approve")

    ei_loaded = instruction_store.load_execution_instruction(out["execution_instruction_ref"])
    assert ei_loaded["execution_instruction"]["approve_trade"] is True
    assert ei_loaded["execution_instruction"]["size_percent"] == 20