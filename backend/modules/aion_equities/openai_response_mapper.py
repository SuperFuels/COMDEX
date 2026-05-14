from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Optional


def _as_dict(value: Any) -> Dict[str, Any]:
    return deepcopy(value) if isinstance(value, dict) else {}


def map_openai_trade_review_response(
    response: Dict[str, Any],
    *,
    company_ref: str,
    proposal_id: str,
    review_id: Optional[str] = None,
    thesis_ref: Optional[str] = None,
    generated_by: str = "aion_equities.openai_response_mapper",
) -> Dict[str, Dict[str, Any]]:
    """
    Split a structured OpenAI trade review response into:
    - normalized decision_notes
    - normalized execution_instruction
    - store-ready payloads for both
    """
    if not isinstance(response, dict):
        raise TypeError("response must be a dict")

    decision_notes = _as_dict(response.get("decision_notes"))
    execution_instruction = _as_dict(response.get("execution_instruction"))

    if not decision_notes:
        raise ValueError("response missing decision_notes")
    if not execution_instruction:
        raise ValueError("response missing execution_instruction")

    resolved_review_id = (
        review_id
        or str(response.get("review_id") or "").strip()
        or f"review/{proposal_id}"
    )

    required_human_approval = bool(
        execution_instruction.get("required_human_approval", True)
    )

    decision_notes_payload: Dict[str, Any] = {
        "review_id": resolved_review_id,
        "company_ref": company_ref,
        "proposal_id": proposal_id,
        "decision_notes": decision_notes,
        "generated_by": generated_by,
    }

    if thesis_ref is not None:
        decision_notes_payload["thesis_ref"] = thesis_ref

    execution_instruction_payload: Dict[str, Any] = {
        "review_id": resolved_review_id,
        "company_ref": company_ref,
        "proposal_id": proposal_id,
        "execution_instruction": execution_instruction,
        "generated_by": generated_by,
        "payload_patch": {
            "approval_state": (
                "pending_human_approval"
                if required_human_approval
                else "approved_no_human_required"
            ),
            "instruction_status": "pending_guardrail_review",
        },
    }

    if thesis_ref is not None:
        execution_instruction_payload["thesis_ref"] = thesis_ref
        execution_instruction_payload["payload_patch"]["thesis_ref"] = thesis_ref

    return {
        "decision_notes": decision_notes,
        "execution_instruction": execution_instruction,
        "decision_notes_payload": decision_notes_payload,
        "execution_instruction_payload": execution_instruction_payload,
    }


__all__ = [
    "map_openai_trade_review_response",
]