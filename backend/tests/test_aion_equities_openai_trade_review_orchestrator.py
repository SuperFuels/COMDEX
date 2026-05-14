from __future__ import annotations

from backend.modules.aion_equities.decision_notes_store import DecisionNotesStore
from backend.modules.aion_equities.execution_instruction_store import ExecutionInstructionStore
from backend.modules.aion_equities.openai_context_packet_builder import OpenAIContextPacketBuilder
from backend.modules.aion_equities.openai_operating_brief_store import OpenAIOperatingBriefStore
from backend.modules.aion_equities.openai_review_artifact_store import OpenAIReviewArtifactStore
from backend.modules.aion_equities.openai_trade_decision_runtime import OpenAITradeDecisionRuntime
from backend.modules.aion_equities.openai_trade_review_orchestrator import OpenAITradeReviewOrchestrator
from backend.modules.aion_equities.trade_execution_guardrails import TradeExecutionGuardrails


def _good_openai_client(_: dict) -> dict:
    return {
        "decision_notes": {
            "summary": "Approve with staged entry.",
            "conditions_met": ["high_sqi", "trigger_confirmed"],
            "key_risks": ["fx volatility"],
            "capital_rationale": "High-confidence predictable setup.",
            "timing_rationale": "Catalyst window approaching.",
            "thesis_invalidation": ["material margin collapse"],
            "watch_next": ["consensus revisions"],
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
            "buy_conditions": ["price <= threshold"],
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


def _bad_openai_client(_: dict) -> dict:
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


def _make_orchestrator(tmp_path, client):
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
    review_artifact_store = OpenAIReviewArtifactStore(tmp_path)
    guardrails = TradeExecutionGuardrails()

    runtime = OpenAITradeDecisionRuntime(
        context_packet_builder=builder,
        decision_notes_store=decision_notes_store,
        execution_instruction_store=execution_instruction_store,
        openai_client=client,
    )

    orchestrator = OpenAITradeReviewOrchestrator(
        trade_decision_runtime=runtime,
        review_artifact_store=review_artifact_store,
        guardrails=guardrails,
    )

    return orchestrator, review_artifact_store


def test_openai_trade_review_orchestrator_runs_end_to_end(tmp_path):
    orchestrator, review_artifact_store = _make_orchestrator(tmp_path, _good_openai_client)

    out = orchestrator.run_review(
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
    assert out["decision_notes_ref"].startswith("decision_notes/")
    assert out["execution_instruction_ref"].startswith("execution_instruction/")
    assert out["review_artifact_ref"].startswith("review_artifact/")
    assert out["guardrail_result"]["status"] == "pass"
    assert out["approved_for_human_review"] is True

    artifact = review_artifact_store.load_review_artifact(out["review_artifact_ref"])
    assert artifact["decision_notes"]["summary"] == "Approve with staged entry."
    assert artifact["execution_instruction"]["approve_trade"] is True


def test_openai_trade_review_orchestrator_blocks_on_guardrail_failure(tmp_path):
    orchestrator, review_artifact_store = _make_orchestrator(tmp_path, _bad_openai_client)

    out = orchestrator.run_review(
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

    assert out["guardrail_result"]["status"] == "fail"
    assert out["approved_for_human_review"] is False
    assert len(out["guardrail_result"]["failures"]) > 0

    artifact = review_artifact_store.load_review_artifact(out["review_artifact_ref"])
    assert artifact["guardrail_result"]["status"] == "fail"