from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Optional

from backend.modules.aion_equities.openai_trade_decision_runtime import (
    OpenAITradeDecisionRuntime,
)
from backend.modules.aion_equities.openai_review_artifact_store import (
    OpenAIReviewArtifactStore,
)
from backend.modules.aion_equities.trade_execution_guardrails import (
    TradeExecutionGuardrails,
)


class OpenAITradeReviewOrchestrator:
    """
    Top-level orchestration layer for an OpenAI-backed trade review.

    Responsibilities:
    - invoke the trade decision runtime
    - persist a full review artifact
    - run execution guardrails against the produced instruction
    - return a single consolidated review result
    """

    def __init__(
        self,
        *,
        trade_decision_runtime: OpenAITradeDecisionRuntime,
        review_artifact_store: OpenAIReviewArtifactStore,
        guardrails: TradeExecutionGuardrails,
    ):
        self.trade_decision_runtime = trade_decision_runtime
        self.review_artifact_store = review_artifact_store
        self.guardrails = guardrails

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
        generated_by: str = "aion_equities.openai_trade_review_orchestrator",
    ) -> Dict[str, Any]:
        proposal_packet = deepcopy(proposal_packet or {})
        current_business_status = deepcopy(current_business_status or {})
        company_intelligence_pack = deepcopy(company_intelligence_pack or {})

        # Runtime returns payload wrappers, not direct notes/instruction fields
        decision_out = self.trade_decision_runtime.run_review(
            company_ref=company_ref,
            proposal_id=proposal_id,
            review_id=review_id,
            thesis_ref=thesis_ref,
            proposal_packet=proposal_packet,
            current_business_status=current_business_status,
            company_intelligence_pack=company_intelligence_pack,
            operating_brief_id=operating_brief_id,
            operating_brief_version=operating_brief_version,
            generated_by=generated_by,
        )

        decision_notes_payload = deepcopy(decision_out["decision_notes_payload"])
        execution_instruction_payload = deepcopy(decision_out["execution_instruction_payload"])

        decision_notes = deepcopy(decision_notes_payload.get("decision_notes") or {})
        execution_instruction = deepcopy(
            execution_instruction_payload.get("execution_instruction") or {}
        )

        guardrail_result = self.guardrails.validate_instruction(
            execution_instruction_payload=execution_instruction_payload,
            business_status=current_business_status,
        )
        approved = bool(guardrail_result.get("status") == "pass")

        decision_notes_ref = f"decision_notes/{company_ref}/{proposal_id}"
        execution_instruction_ref = f"execution_instruction/{company_ref}/{proposal_id}"

        artifact = self.review_artifact_store.save_review_artifact(
            review_id=review_id,
            company_ref=company_ref,
            proposal_id=proposal_id,
            thesis_ref=thesis_ref,
            context_packet=decision_out["context_packet"],
            raw_response=decision_out["raw_response"],
            decision_notes_payload=decision_notes_payload,
            execution_instruction_payload=execution_instruction_payload,
            generated_by=generated_by,
            payload_patch={
                "decision_notes": decision_notes,
                "execution_instruction": execution_instruction,
                "decision_notes_ref": decision_notes_ref,
                "execution_instruction_ref": execution_instruction_ref,
                "guardrail_result": guardrail_result,
            },
        )

        return {
            "review_id": review_id,
            "company_ref": company_ref,
            "proposal_id": proposal_id,
            "thesis_ref": thesis_ref,
            "decision_notes_ref": decision_notes_ref,
            "execution_instruction_ref": execution_instruction_ref,
            "review_artifact_ref": artifact["review_artifact_id"],
            "guardrail_result": guardrail_result,
            "approved_for_human_review": approved,
        }


__all__ = [
    "OpenAITradeReviewOrchestrator",
]