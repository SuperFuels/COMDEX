from __future__ import annotations

from backend.modules.aion_equities.decision_notes_store import DecisionNotesStore
from backend.modules.aion_equities.execution_instruction_store import ExecutionInstructionStore
from backend.modules.aion_equities.openai_context_packet_builder import OpenAIContextPacketBuilder
from backend.modules.aion_equities.openai_operating_brief_store import OpenAIOperatingBriefStore
from backend.modules.aion_equities.openai_trade_review_pipeline import OpenAITradeReviewPipeline
from backend.modules.aion_equities.trade_execution_guardrails import TradeExecutionGuardrails


def _mock_openai_client(_: dict) -> dict:
    return {
        "decision_notes": {
            "summary": "Approve with staged entry.",
            "conditions_met": ["high_sqi", "trigger_confirmed"],
            "key_risks": ["fx volatility"],
            "capital_rationale": "High-confidence boring predictable setup.",
            "timing_rationale": "Catalyst window approaching with confirmation.",
            "thesis_invalidation": ["material margin collapse"],
            "watch_next": ["next company update", "consensus revisions"],
        },
        "execution_instruction": {
            "approve_trade": True,
            "trade_type": "fundamental_long",
            "entry_method": "tranche_plan",
            "tranche_plan": [
                {"stage": "now", "size_percent": 10},
                {"stage": "pre_catalyst", "size_percent": 10},
            ],
            "size_percent": 20,
            "max_capital_allowed": 20000,
            "buy_conditions": ["price <= fair_value_gap_threshold"],
            "add_conditions": ["trigger_state == confirmed"],
            "reduce_conditions": ["thesis_confidence drops"],
            "exit_conditions": ["target reached", "thesis invalidated"],
            "time_based_exit": "2099-01-01T00:00:00Z",
            "thesis_invalidation_rules": ["material margin collapse"],
            "stop_style": "thesis_based",
            "target_logic": "5_to_10_percent_into_catalyst",
            "priority_level": "high",
            "expires_at": "2099-01-01T00:00:00Z",
            "required_human_approval": True,
        },
    }


def test_openai_trade_review_pipeline_runs_end_to_end(tmp_path):
    brief_store = OpenAIOperatingBriefStore(tmp_path)
    brief_store.save_operating_brief(
        brief_id="brief/aion/v1",
        version="v1",
        title="AION Operating Brief",
        content="System brief",
        generated_by="pytest",
    )

    builder = OpenAIContextPacketBuilder(operating_brief_store=brief_store)
    decision_notes_store = DecisionNotesStore(tmp_path)
    execution_instruction_store = ExecutionInstructionStore(tmp_path)
    guardrails = TradeExecutionGuardrails()

    pipeline = OpenAITradeReviewPipeline(
        context_packet_builder=builder,
        decision_notes_store=decision_notes_store,
        execution_instruction_store=execution_instruction_store,
        guardrails=guardrails,
        openai_client=_mock_openai_client,
    )

    out = pipeline.run_review(
        company_ref="company/ULVR.L",
        proposal_id="proposal/ULVR.L/2026-Q4",
        review_id="review/ULVR.L/2026-Q4",
        thesis_ref="thesis/ULVR.L/long/medium_term",
        proposal_packet={
            "current_price": 4210,
            "requested_action": "review_trade",
        },
        current_business_status={
            "total_capital": 100000,
            "deployed_capital": 25000,
            "free_cash": 75000,
        },
        company_intelligence_pack={
            "sqi_score": 0.92,
            "trigger_state": "confirmed",
            "sector_confidence_tier": "tier_1",
        },
        operating_brief_id="brief/aion/v1",
        operating_brief_version="v1",
        generated_by="pytest",
    )

    assert out["review_id"] == "review/ULVR.L/2026-Q4"
    assert out["company_ref"] == "company/ULVR.L"
    assert out["proposal_id"] == "proposal/ULVR.L/2026-Q4"
    assert out["decision_notes_ref"].startswith("decision_notes/")
    assert out["execution_instruction_ref"].startswith("execution_instruction/")
    assert out["guardrail_result"]["approved"] is True
    assert out["approved_for_human_review"] is True

    saved_notes = decision_notes_store.load_decision_notes(out["decision_notes_ref"])
    assert saved_notes["decision_notes"]["summary"] == "Approve with staged entry."

    saved_instruction = execution_instruction_store.load_execution_instruction(
        out["execution_instruction_ref"]
    )
    assert saved_instruction["execution_instruction"]["approve_trade"] is True
    assert saved_instruction["execution_instruction"]["trade_type"] == "fundamental_long"


def test_openai_trade_review_pipeline_blocks_on_guardrail_failure(tmp_path):
    brief_store = OpenAIOperatingBriefStore(tmp_path)
    brief_store.save_operating_brief(
        brief_id="brief/aion/v1",
        version="v1",
        title="AION Operating Brief",
        body="System brief",
        generated_by="pytest",
    )

    builder = OpenAIContextPacketBuilder(operating_brief_store=brief_store)
    decision_notes_store = DecisionNotesStore(tmp_path)
    execution_instruction_store = ExecutionInstructionStore(tmp_path)
    guardrails = TradeExecutionGuardrails()

    def bad_client(_: dict) -> dict:
        return {
            "decision_notes": {
                "summary": "Reject due to oversized risk.",
            },
            "execution_instruction": {
                "approve_trade": True,
                "trade_type": "fundamental_long",
                "entry_method": "single_entry",
                "size_percent": 95,
                "max_capital_allowed": 95000,
                "required_human_approval": True,
                "stop_style": "thesis_based",
                "expires_at": "2099-01-01T00:00:00Z",
            },
        }

    pipeline = OpenAITradeReviewPipeline(
        context_packet_builder=builder,
        decision_notes_store=decision_notes_store,
        execution_instruction_store=execution_instruction_store,
        guardrails=guardrails,
        openai_client=bad_client,
    )

    out = pipeline.run_review(
        company_ref="company/PG.L",
        proposal_id="proposal/PG.L/2026-Q4",
        review_id="review/PG.L/2026-Q4",
        thesis_ref="thesis/PG.L/long/medium_term",
        proposal_packet={"requested_action": "review_trade"},
        current_business_status={"total_capital": 100000},
        company_intelligence_pack={"sqi_score": 0.88},
        operating_brief_id="brief/aion/v1",
        operating_brief_version="v1",
        generated_by="pytest",
    )

    assert out["guardrail_result"]["approved"] is False
    assert out["approved_for_human_review"] is False
    assert len(out["guardrail_result"]["violations"]) > 0