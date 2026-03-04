from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Optional

from backend.modules.aion_equities.openai_operating_brief_store import (
    OpenAIOperatingBriefStore,
)


class OpenAIContextPacketBuilder:
    def __init__(self, *, operating_brief_store: OpenAIOperatingBriefStore):
        self.operating_brief_store = operating_brief_store

    def _load_brief(
        self,
        *,
        operating_brief_id: Optional[str] = None,
        operating_brief_version: Optional[str] = None,
    ) -> Dict[str, Any]:
        if operating_brief_id:
            brief = self.operating_brief_store.load_operating_brief(operating_brief_id)
        else:
            brief = self.operating_brief_store.load_active_brief()

        if operating_brief_version and str(brief.get("version")) != str(operating_brief_version):
            raise ValueError(
                f"Operating brief version mismatch: expected {operating_brief_version}, "
                f"got {brief.get('version')}"
            )

        return deepcopy(brief)

    def build_context_packet(
        self,
        *,
        # primary identifiers
        company_ref: Optional[str] = None,
        proposal_id: Optional[str] = None,
        proposal_ref: Optional[str] = None,
        review_id: Optional[str] = None,
        thesis_ref: Optional[str] = None,

        # NEW: explicit requested action (tests require this)
        requested_action: Optional[str] = None,

        # inputs (accept multiple alias shapes)
        proposal_packet: Optional[Dict[str, Any]] = None,
        proposal: Optional[Dict[str, Any]] = None,

        current_business_status: Optional[Dict[str, Any]] = None,
        business_status: Optional[Dict[str, Any]] = None,

        company_intelligence_pack: Optional[Dict[str, Any]] = None,
        company_state: Optional[Dict[str, Any]] = None,
        company_profile: Optional[Dict[str, Any]] = None,
        company_snapshot: Optional[Dict[str, Any]] = None,

        # brief selectors
        operating_brief_id: Optional[str] = None,
        operating_brief_version: Optional[str] = None,

        generated_by: str = "aion_equities.openai_context_packet_builder",
        **_: Any,
    ) -> Dict[str, Any]:
        brief = self._load_brief(
            operating_brief_id=operating_brief_id,
            operating_brief_version=operating_brief_version,
        )

        resolved_proposal_packet = deepcopy(proposal_packet or proposal or {})
        resolved_business_status = deepcopy(current_business_status or business_status or {})
        resolved_company_pack = deepcopy(
            company_intelligence_pack
            or company_state
            or company_profile
            or company_snapshot
            or {}
        )

        resolved_company_ref = company_ref or resolved_company_pack.get("company_ref")
        resolved_proposal_id = proposal_id or proposal_ref or resolved_proposal_packet.get("proposal_id")
        resolved_review_id = review_id or resolved_proposal_packet.get("review_id")

        resolved_requested_action = (
            requested_action
            or resolved_proposal_packet.get("requested_action")
            or resolved_proposal_packet.get("action")
        )

        packet: Dict[str, Any] = {
            "context_packet_type": "openai_trade_review",
            "generated_by": str(generated_by),

            # legacy top-level fields (tests expect these)
            "brief_id": brief.get("brief_id"),
            "operating_brief_id": brief.get("brief_id"),
            "operating_brief_version": brief.get("version"),
            "proposal_id": resolved_proposal_id,
            "review_id": resolved_review_id,
            "company_ref": resolved_company_ref,
            "thesis_ref": thesis_ref,
            "requested_action": resolved_requested_action,

            # tests also expect runtime_notes.operating_brief_version
            "runtime_notes": {
                "operating_brief_id": brief.get("brief_id"),
                "operating_brief_version": brief.get("version"),
            },

            # nested structure for pipeline usage
            "operating_brief": {
                "brief_id": brief.get("brief_id"),
                "version": brief.get("version"),
                "title": brief.get("title"),
                "summary": brief.get("summary"),
                "sections": deepcopy(brief.get("sections", [])),
                "brief_text": brief.get("brief_text", ""),
            },
            "review_context": {
                "review_id": resolved_review_id,
                "company_ref": resolved_company_ref,
                "proposal_id": resolved_proposal_id,
                "thesis_ref": thesis_ref,
                "requested_action": resolved_requested_action,
            },
            "current_business_status": resolved_business_status,
            "company_intelligence_pack": resolved_company_pack,
            "proposal_packet": resolved_proposal_packet,
        }

        return packet


__all__ = [
    "OpenAIContextPacketBuilder",
]