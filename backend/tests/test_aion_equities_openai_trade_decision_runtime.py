from __future__ import annotations

from backend.modules.aion_equities.openai_context_packet_builder import OpenAIContextPacketBuilder
from backend.modules.aion_equities.openai_operating_brief_store import OpenAIOperatingBriefStore
from backend.modules.aion_equities.openai_trade_decision_runtime import OpenAITradeDecisionRuntime


def _mock_openai_client(packet: dict) -> dict:
    assert packet["proposal_id"] == "proposal/ULVR.L/2026-Q4"
    assert packet["company_ref"] == "company/ULVR.L"
    return {
        "decision_notes": {
            "summary": "Approve with staged entry.",
            "conditions_met": ["high_sqi", "trigger_confirmed"],
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


def test_openai_trade_decision_runtime_builds_context_and_maps_response(tmp_path):
    brief_store = OpenAIOperatingBriefStore(tmp_path)
    brief_store.save_operating_brief(
        brief_id="brief/aion/v1",
        version="v1",
        title="AION Operating Brief",
        content="System brief",
        generated_by="pytest",
    )

    builder = OpenAIContextPacketBuilder(operating_brief_store=brief_store)
    runtime = OpenAITradeDecisionRuntime(
        context_packet_builder=builder,
        openai_client=_mock_openai_client,
    )

    out = runtime.run_trade_decision(
        company_ref="company/ULVR.L",
        proposal_id="proposal/ULVR.L/2026-Q4",
        review_id="review/ULVR.L/2026-Q4",
        thesis_ref="thesis/ULVR.L/long/medium_term",
        proposal_packet={"requested_action": "review_trade", "current_price": 4210},
        current_business_status={"total_capital": 100000, "free_cash": 75000},
        company_intelligence_pack={"sqi_score": 0.92, "trigger_state": "confirmed"},
        operating_brief_id="brief/aion/v1",
        operating_brief_version="v1",
        generated_by="pytest",
    )

    assert out["review_id"] == "review/ULVR.L/2026-Q4"
    assert out["company_ref"] == "company/ULVR.L"
    assert out["proposal_id"] == "proposal/ULVR.L/2026-Q4"
    assert out["context_packet"]["operating_brief"]["brief_id"] == "brief/aion/v1"
    assert out["decision_notes_payload"]["decision_notes"]["summary"] == "Approve with staged entry."
    assert out["execution_instruction_payload"]["execution_instruction"]["approve_trade"] is True


def test_openai_trade_decision_runtime_preserves_raw_response(tmp_path):
    brief_store = OpenAIOperatingBriefStore(tmp_path)
    brief_store.save_operating_brief(
        brief_id="brief/aion/v1",
        version="v1",
        title="AION Operating Brief",
        body="System brief",
        generated_by="pytest",
    )

    builder = OpenAIContextPacketBuilder(operating_brief_store=brief_store)

    def client(_: dict) -> dict:
        return {
            "decision_notes": {"summary": "Reject."},
            "execution_instruction": {
                "approve_trade": False,
                "trade_type": "no_trade",
                "entry_method": "none",
                "size_percent": 0,
                "max_capital_allowed": 0,
                "required_human_approval": True,
                "stop_style": "none",
                "expires_at": "2099-01-01T00:00:00Z",
            },
        }

    runtime = OpenAITradeDecisionRuntime(
        context_packet_builder=builder,
        openai_client=client,
    )

    out = runtime.run_trade_decision(
        company_ref="company/PG.L",
        proposal_id="proposal/PG.L/2026-Q4",
        review_id="review/PG.L/2026-Q4",
        proposal_packet={"requested_action": "review_trade"},
        current_business_status={},
        company_intelligence_pack={},
        operating_brief_id="brief/aion/v1",
        generated_by="pytest",
    )

    assert out["raw_response"]["decision_notes"]["summary"] == "Reject."
    assert out["execution_instruction_payload"]["execution_instruction"]["trade_type"] == "no_trade"