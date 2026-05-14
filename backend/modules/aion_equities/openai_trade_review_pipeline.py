from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from backend.modules.aion_equities.decision_notes_store import DecisionNotesStore
from backend.modules.aion_equities.execution_instruction_store import ExecutionInstructionStore
from backend.modules.aion_equities.openai_context_packet_builder import OpenAIContextPacketBuilder
from backend.modules.aion_equities.openai_response_mapper import map_openai_trade_review_response
from backend.modules.aion_equities.trade_execution_guardrails import TradeExecutionGuardrails


class OpenAITradeReviewPipeline:
    def __init__(
        self,
        *,
        context_packet_builder: OpenAIContextPacketBuilder,
        decision_notes_store: DecisionNotesStore,
        execution_instruction_store: ExecutionInstructionStore,
        guardrails: TradeExecutionGuardrails,
        openai_client: Callable[[Dict[str, Any]], Dict[str, Any]],
    ):
        self.context_packet_builder = context_packet_builder
        self.decision_notes_store = decision_notes_store
        self.execution_instruction_store = execution_instruction_store
        self.guardrails = guardrails
        self.openai_client = openai_client

    def run_review(
        self,
        *,
        company_ref: str,
        proposal_id: str,
        review_id: str,
        thesis_ref: Optional[str] = None,
        proposal_packet: Optional[Dict[str, Any]] = None,
        current_business_status: Optional[Dict[str, Any]] = None,
        company_intelligence_pack: Optional[Dict[str, Any]] = None,
        operating_brief_id: Optional[str] = None,
        operating_brief_version: Optional[str] = None,
        generated_by: str = "aion_equities.openai_trade_review_pipeline",
    ) -> Dict[str, Any]:
        context_packet = self.context_packet_builder.build_context_packet(
            company_ref=company_ref,
            proposal_id=proposal_id,
            review_id=review_id,
            thesis_ref=thesis_ref,
            proposal_packet=proposal_packet or {},
            current_business_status=current_business_status or {},
            company_intelligence_pack=company_intelligence_pack or {},
            operating_brief_id=operating_brief_id,
            operating_brief_version=operating_brief_version,
            generated_by=generated_by,
        )

        raw_response = self.openai_client(context_packet)

        mapped = map_openai_trade_review_response(
            raw_response,
            company_ref=company_ref,
            proposal_id=proposal_id,
            review_id=review_id,
            thesis_ref=thesis_ref,
            generated_by=generated_by,
        )

        # mapper returns payload inputs; keep defensive fallbacks
        decision_notes = (
            (mapped.get("decision_notes_payload") or {}).get("decision_notes")
            or raw_response.get("decision_notes")
            or {}
        )
        execution_instruction = (
            (mapped.get("execution_instruction_payload") or {}).get("execution_instruction")
            or raw_response.get("execution_instruction")
            or {}
        )

        saved_notes = self.decision_notes_store.save_decision_notes(
            review_id=review_id,
            company_ref=company_ref,
            proposal_id=proposal_id,
            thesis_ref=thesis_ref,
            decision_notes=decision_notes,
            generated_by=generated_by,
        )

        saved_instruction = self.execution_instruction_store.save_execution_instruction(
            review_id=review_id,
            company_ref=company_ref,
            proposal_id=proposal_id,
            thesis_ref=thesis_ref,
            execution_instruction=execution_instruction,
            generated_by=generated_by,
        )

        guardrail_result = self.guardrails.evaluate(
            execution_instruction=execution_instruction,
            current_business_status=current_business_status or {},
            company_intelligence_pack=company_intelligence_pack or {},
        )

        return {
            "review_id": review_id,
            "company_ref": company_ref,
            "proposal_id": proposal_id,
            "thesis_ref": thesis_ref,
            "decision_notes_ref": saved_notes["decision_notes_id"],
            "execution_instruction_ref": saved_instruction["execution_instruction_id"],
            "guardrail_result": guardrail_result,
            "approved_for_human_review": bool(guardrail_result.get("approved")),
        }


__all__ = [
    "OpenAITradeReviewPipeline",
]