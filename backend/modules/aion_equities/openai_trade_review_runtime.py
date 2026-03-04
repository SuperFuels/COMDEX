from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional

from backend.modules.aion_equities.decision_notes_store import DecisionNotesStore
from backend.modules.aion_equities.execution_instruction_store import ExecutionInstructionStore
from backend.modules.aion_equities.openai_context_packet_builder import (
    OpenAIContextPacketBuilder,
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _require_dict(value: Any, name: str) -> Dict[str, Any]:
    if not isinstance(value, dict):
        raise TypeError(f"{name} must be a dict, got {type(value).__name__}")
    return value


class OpenAITradeReviewRuntime:
    """
    Builds a context packet, submits it to an injected OpenAI callable,
    then stores two formal artifacts:
    - decision notes document
    - execution instruction document

    The injected callable must return:
    {
      "decision_notes": {...},
      "execution_instruction": {...}
    }
    """

    def __init__(
        self,
        *,
        context_packet_builder: OpenAIContextPacketBuilder,
        decision_notes_store: DecisionNotesStore,
        execution_instruction_store: ExecutionInstructionStore,
        openai_callable: Callable[[Dict[str, Any]], Dict[str, Any]],
    ):
        self.context_packet_builder = context_packet_builder
        self.decision_notes_store = decision_notes_store
        self.execution_instruction_store = execution_instruction_store
        self.openai_callable = openai_callable

    def review_trade_proposal(
        self,
        *,
        review_id: str,
        proposal_id: str,
        company_ref: str,
        requested_action: str,
        business_status: Dict[str, Any],
        company_intelligence_pack: Dict[str, Any],
        proposal_packet: Dict[str, Any],
        thesis_ref: Optional[str] = None,
        operating_brief_id: Optional[str] = None,
        as_of: Optional[str] = None,
    ) -> Dict[str, Any]:
        as_of = as_of or _utc_now_iso()

        context_packet = self.context_packet_builder.build_context_packet(
            proposal_id=proposal_id,
            requested_action=requested_action,
            business_status=business_status,
            company_intelligence_pack=company_intelligence_pack,
            proposal_packet=proposal_packet,
            operating_brief_id=operating_brief_id,
            as_of=as_of,
        )

        raw_response = self.openai_callable(deepcopy(context_packet))
        raw_response = _require_dict(raw_response, "openai response")

        decision_notes = _require_dict(raw_response.get("decision_notes"), "decision_notes")
        execution_instruction = _require_dict(
            raw_response.get("execution_instruction"),
            "execution_instruction",
        )

        decision_notes_payload = self.decision_notes_store.save_decision_notes(
            review_id=review_id,
            company_ref=company_ref,
            proposal_id=proposal_id,
            decision_notes=decision_notes,
            thesis_ref=thesis_ref,
            generated_by="aion_equities.openai_trade_review_runtime",
        )

        execution_instruction_payload = self.execution_instruction_store.save_execution_instruction(
            review_id=review_id,
            company_ref=company_ref,
            proposal_id=proposal_id,
            execution_instruction=execution_instruction,
            thesis_ref=thesis_ref,
            generated_by="aion_equities.openai_trade_review_runtime",
        )

        return {
            "review_id": review_id,
            "proposal_id": proposal_id,
            "company_ref": company_ref,
            "as_of": as_of,
            "context_packet": context_packet,
            "decision_notes_ref": decision_notes_payload["decision_notes_id"],
            "execution_instruction_ref": execution_instruction_payload["execution_instruction_id"],
            "decision_notes": decision_notes_payload,
            "execution_instruction": execution_instruction_payload,
        }


__all__ = [
    "OpenAITradeReviewRuntime",
]