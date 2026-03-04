from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable, Dict, Optional

from backend.modules.aion_equities.decision_notes_store import DecisionNotesStore
from backend.modules.aion_equities.execution_instruction_store import ExecutionInstructionStore
from backend.modules.aion_equities.openai_context_packet_builder import OpenAIContextPacketBuilder
from backend.modules.aion_equities.openai_response_mapper import map_openai_trade_review_response


class OpenAITradeDecisionRuntime:
    """
    Thin runtime that:
    - builds the OpenAI context packet
    - calls the OpenAI client
    - maps the structured response into decision/execution payloads
    - optionally persists decision_notes + execution_instruction if stores are provided
    """

    def __init__(
        self,
        *,
        context_packet_builder: OpenAIContextPacketBuilder,
        openai_client: Callable[[Dict[str, Any]], Dict[str, Any]],
        decision_notes_store: Optional[DecisionNotesStore] = None,
        execution_instruction_store: Optional[ExecutionInstructionStore] = None,
        **_: Any,
    ):
        self.context_packet_builder = context_packet_builder
        self.openai_client = openai_client
        self.decision_notes_store = decision_notes_store
        self.execution_instruction_store = execution_instruction_store

    def run_trade_decision(
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
        generated_by: str = "aion_equities.openai_trade_decision_runtime",
        **_: Any,
    ) -> Dict[str, Any]:
        context_packet = self.context_packet_builder.build_context_packet(
            company_ref=company_ref,
            proposal_id=proposal_id,
            review_id=review_id,
            thesis_ref=thesis_ref,
            proposal_packet=deepcopy(proposal_packet or {}),
            current_business_status=deepcopy(current_business_status or {}),
            company_intelligence_pack=deepcopy(company_intelligence_pack or {}),
            operating_brief_id=operating_brief_id,
            operating_brief_version=operating_brief_version,
            generated_by=generated_by,
        )

        raw_response = self.openai_client(deepcopy(context_packet))

        mapped = map_openai_trade_review_response(
            deepcopy(raw_response),
            company_ref=company_ref,
            proposal_id=proposal_id,
            review_id=review_id,
            thesis_ref=thesis_ref,
            generated_by=generated_by,
        )

        decision_notes_payload = deepcopy(mapped["decision_notes_payload"])
        execution_instruction_payload = deepcopy(mapped["execution_instruction_payload"])

        decision_notes = deepcopy(decision_notes_payload.get("decision_notes", {}))
        execution_instruction = deepcopy(
            execution_instruction_payload.get("execution_instruction", {})
        )

        decision_notes_ref: Optional[str] = None
        execution_instruction_ref: Optional[str] = None
        saved_notes: Optional[Dict[str, Any]] = None
        saved_instruction: Optional[Dict[str, Any]] = None

        if self.decision_notes_store is not None:
            saved_notes = self.decision_notes_store.save_decision_notes(**decision_notes_payload)
            decision_notes_ref = saved_notes.get("decision_notes_id")

        if self.execution_instruction_store is not None:
            saved_instruction = self.execution_instruction_store.save_execution_instruction(
                **execution_instruction_payload
            )
            execution_instruction_ref = saved_instruction.get("execution_instruction_id")

        out: Dict[str, Any] = {
            "review_id": review_id,
            "company_ref": company_ref,
            "proposal_id": proposal_id,
            "thesis_ref": thesis_ref,
            "context_packet": deepcopy(context_packet),
            "raw_response": deepcopy(raw_response),
            "raw_openai_response": deepcopy(raw_response),
            "decision_notes_payload": decision_notes_payload,
            "execution_instruction_payload": execution_instruction_payload,
            "decision_notes": decision_notes,
            "execution_instruction": execution_instruction,
        }

        if decision_notes_ref:
            out["decision_notes_ref"] = decision_notes_ref
        if execution_instruction_ref:
            out["execution_instruction_ref"] = execution_instruction_ref
        if saved_notes is not None:
            out["saved_decision_notes"] = saved_notes
        if saved_instruction is not None:
            out["saved_execution_instruction"] = saved_instruction

        return out

    def run_review(self, **kwargs: Any) -> Dict[str, Any]:
        """
        Legacy compatibility alias expected by orchestrator/tests.
        """
        return self.run_trade_decision(**kwargs)


__all__ = [
    "OpenAITradeDecisionRuntime",
]