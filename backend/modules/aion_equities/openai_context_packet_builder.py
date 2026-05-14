# /workspaces/COMDEX/backend/modules/aion_equities/openai_context_packet_builder.py
from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Optional

from backend.modules.aion_equities.company_intelligence_snapshot_loader import (
    CompanyIntelligenceSnapshotLoader,
)
from backend.modules.aion_equities.openai_operating_brief_store import (
    OpenAIOperatingBriefStore,
)


class OpenAIContextPacketBuilder:
    """
    Builds the canonical OpenAI trade review context packet.

    New capability:
      - If no company_intelligence_pack is supplied, but a CompanyIntelligenceSnapshotLoader
        is provided, we auto-load a linked replay snapshot (one-pass pack) for company_ref.

    Backward compatibility:
      - Accepts alias shapes for proposal and business status
      - Preserves legacy top-level keys required by existing tests
    """

    def __init__(
        self,
        *,
        operating_brief_store: OpenAIOperatingBriefStore,
        company_snapshot_loader: Optional[CompanyIntelligenceSnapshotLoader] = None,
    ):
        self.operating_brief_store = operating_brief_store
        self.company_snapshot_loader = company_snapshot_loader

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

    def _resolve_company_pack(
        self,
        *,
        company_ref: Optional[str],
        provided_pack: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        If caller provided a pack, use it.
        Else if we have a loader + company_ref, load snapshot.
        """
        if provided_pack:
            return deepcopy(provided_pack)

        if self.company_snapshot_loader is None:
            return {}

        if not company_ref:
            return {}

        try:
            snap = self.company_snapshot_loader.load_snapshot(company_ref=str(company_ref))
            return deepcopy(snap)
        except Exception:
            # best-effort: packet builder should not hard-fail if snapshot is missing
            return {}

    def build_context_packet(
        self,
        *,
        # primary identifiers
        company_ref: Optional[str] = None,
        proposal_id: Optional[str] = None,
        proposal_ref: Optional[str] = None,
        review_id: Optional[str] = None,
        thesis_ref: Optional[str] = None,

        # explicit requested action
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

        # Prefer explicit pack if supplied; otherwise allow snapshot loader fallback.
        provided_pack = deepcopy(
            company_intelligence_pack
            or company_state
            or company_profile
            or company_snapshot
            or {}
        )

        # Resolve IDs
        resolved_company_ref = company_ref or provided_pack.get("company_ref")
        resolved_proposal_id = proposal_id or proposal_ref or resolved_proposal_packet.get("proposal_id")
        resolved_review_id = review_id or resolved_proposal_packet.get("review_id")

        resolved_requested_action = (
            requested_action
            or resolved_proposal_packet.get("requested_action")
            or resolved_proposal_packet.get("action")
        )

        # If no pack provided, try to auto-load linked snapshot
        resolved_company_pack = self._resolve_company_pack(
            company_ref=resolved_company_ref,
            provided_pack=provided_pack,
        )

        # If pack load resolved company_ref but the caller didn't provide it, sync it back
        if not resolved_company_ref:
            resolved_company_ref = resolved_company_pack.get("company_ref")

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