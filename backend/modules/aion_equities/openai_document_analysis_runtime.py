# /workspaces/COMDEX/backend/modules/aion_equities/openai_document_analysis_runtime.py
from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable, Dict, Optional

from backend.modules.aion_equities.openai_operating_brief_store import (
    OpenAIOperatingBriefStore,
)


class OpenAIDocumentAnalysisRuntime:
    """
    Sends a document analysis packet to OpenAI and returns a normalized
    structured analysis payload.

    This runtime is intentionally document-in / structured-json-out.

    Key contract:
      - analyze_document(...) always returns:
        {
          ...,
          "analysis_response": <raw openai dict>,
          "normalized_analysis": <stable normalized dict>,
        }

    Normalization goals:
      - support alias field names from older/newer OpenAI outputs
      - tolerate top-level list aliases for triggers / feeds
      - enforce a minimum stable dict shape for downstream mappers
    """

    def __init__(
        self,
        *,
        operating_brief_store: OpenAIOperatingBriefStore,
        openai_client: Callable[[Dict[str, Any]], Dict[str, Any]],
    ):
        self.operating_brief_store = operating_brief_store
        self.openai_client = openai_client

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

    def _coalesce(self, d: Dict[str, Any], *keys: str, default: Any = None) -> Any:
        for k in keys:
            if k in d and d.get(k) is not None:
                return d.get(k)
        return default

    def _ensure_dict(self, x: Any, *, name: str) -> Dict[str, Any]:
        if x is None:
            return {}
        if not isinstance(x, dict):
            raise TypeError(f"{name} must be a dict")
        return x

    def _normalize_trigger_map(self, root: Dict[str, Any]) -> Dict[str, Any]:
        """
        Support all of:
          - {"trigger_map": {...}}
          - {"triggers": [...]}
          - {"trigger_map": {"triggers": [...]}}
        """
        tm_candidate = self._coalesce(root, "trigger_map", "triggers", "triggering", default={})

        if isinstance(tm_candidate, list):
            trigger_map: Dict[str, Any] = {"triggers": deepcopy(tm_candidate)}
        else:
            trigger_map = self._ensure_dict(tm_candidate, name="trigger_map")
            if "triggers" not in trigger_map:
                top_triggers = root.get("triggers")
                if isinstance(top_triggers, list):
                    trigger_map = {**trigger_map, "triggers": deepcopy(top_triggers)}

        if not isinstance(trigger_map.get("triggers", []), list):
            trigger_map["triggers"] = []

        return trigger_map

    def _normalize_feed_candidates(self, root: Dict[str, Any]) -> Dict[str, Any]:
        """
        Support all of:
          - {"feed_candidates": {...}}
          - {"feeds": [...]}
          - {"feed_candidates": {"feeds": [...]}}
        """
        fc_candidate = self._coalesce(
            root,
            "feed_candidates",
            "feeds",
            "feed_suggestions",
            default={},
        )

        if isinstance(fc_candidate, list):
            feed_candidates: Dict[str, Any] = {"feeds": deepcopy(fc_candidate)}
        else:
            feed_candidates = self._ensure_dict(fc_candidate, name="feed_candidates")
            if "feeds" not in feed_candidates:
                top_feeds = root.get("feeds")
                if isinstance(top_feeds, list):
                    feed_candidates = {**feed_candidates, "feeds": deepcopy(top_feeds)}

        if not isinstance(feed_candidates.get("feeds", []), list):
            feed_candidates["feeds"] = []

        return feed_candidates

    def _normalize_analysis_response(
        self,
        *,
        analysis_response: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Normalize OpenAI output into a stable internal shape.

        Alias support (examples):
          - profile -> company_profile
          - company -> company_profile
          - quarter -> quarter_summary
          - triggers -> trigger_map
          - trigger_map.triggers may be provided as triggers[] at top-level
          - feeds -> feed_candidates
          - assessment / assessment_seed -> assessment_seed
          - thesis / thesis_seed -> thesis_seed
          - variable_watch / watchlist / variable_watch_seed -> variable_watch_seed
          - quarter_event may appear as quarter_event / quarter / quarter_summary
        """
        raw = self._ensure_dict(analysis_response, name="analysis_response")

        # Allow OpenAI to wrap things in "analysis" or "result"
        root = raw
        wrapped = self._coalesce(raw, "analysis", "result", default=None)
        if isinstance(wrapped, dict):
            root = wrapped

        company_profile = self._ensure_dict(
            self._coalesce(root, "company_profile", "profile", "company", default={}),
            name="company_profile",
        )
        quarter_summary = self._ensure_dict(
            self._coalesce(root, "quarter_summary", "quarter", "summary", default={}),
            name="quarter_summary",
        )
        fingerprint = self._ensure_dict(
            self._coalesce(root, "fingerprint", "company_fingerprint", default={}),
            name="fingerprint",
        )

        trigger_map = self._normalize_trigger_map(root)
        feed_candidates = self._normalize_feed_candidates(root)

        assessment_seed = self._ensure_dict(
            self._coalesce(root, "assessment_seed", "assessment", default={}),
            name="assessment_seed",
        )
        thesis_seed = self._ensure_dict(
            self._coalesce(root, "thesis_seed", "thesis", default={}),
            name="thesis_seed",
        )
        variable_watch_seed = self._ensure_dict(
            self._coalesce(
                root,
                "variable_watch_seed",
                "variable_watch",
                "watchlist",
                "variable_watch_list",
                default={},
            ),
            name="variable_watch_seed",
        )

        quarter_event = self._ensure_dict(
            self._coalesce(root, "quarter_event", "quarter_event_seed", default={}),
            name="quarter_event",
        )

        # If quarter_event not provided, derive a minimal one from quarter_summary
        if not quarter_event:
            quarter_event = {
                "headline": quarter_summary.get("headline"),
                "summary": quarter_summary.get("summary"),
                "key_numbers": deepcopy(quarter_summary.get("key_numbers", {})),
                "fiscal_period": self._coalesce(
                    quarter_summary,
                    "fiscal_period",
                    "period",
                    default=None,
                ),
                "published_at": self._coalesce(
                    quarter_summary,
                    "published_at",
                    "date",
                    default=None,
                ),
            }

        normalized = {
            "company_profile": deepcopy(company_profile),
            "quarter_summary": deepcopy(quarter_summary),
            "quarter_event": deepcopy(quarter_event),
            "fingerprint": deepcopy(fingerprint),
            "trigger_map": deepcopy(trigger_map),
            "feed_candidates": deepcopy(feed_candidates),
            "assessment_seed": deepcopy(assessment_seed),
            "thesis_seed": deepcopy(thesis_seed),
            "variable_watch_seed": deepcopy(variable_watch_seed),
            "_extra": {
                k: deepcopy(v)
                for k, v in root.items()
                if k
                not in {
                    "company_profile",
                    "profile",
                    "company",
                    "quarter_summary",
                    "quarter",
                    "summary",
                    "quarter_event",
                    "quarter_event_seed",
                    "fingerprint",
                    "company_fingerprint",
                    "trigger_map",
                    "triggers",
                    "triggering",
                    "feed_candidates",
                    "feeds",
                    "feed_suggestions",
                    "assessment_seed",
                    "assessment",
                    "thesis_seed",
                    "thesis",
                    "variable_watch_seed",
                    "variable_watch",
                    "watchlist",
                    "variable_watch_list",
                    "analysis",
                    "result",
                }
            },
        }

        # Minimum stable shape enforcement
        if not isinstance(normalized["trigger_map"], dict):
            normalized["trigger_map"] = {"triggers": []}
        if not isinstance(normalized["feed_candidates"], dict):
            normalized["feed_candidates"] = {"feeds": []}
        if not isinstance(normalized["trigger_map"].get("triggers", []), list):
            normalized["trigger_map"]["triggers"] = []
        if not isinstance(normalized["feed_candidates"].get("feeds", []), list):
            normalized["feed_candidates"]["feeds"] = []

        return normalized

    def build_document_analysis_packet(
        self,
        *,
        company_ref: str,
        document_ref: str,
        document_text: str,
        document_type: str = "board_pack",
        thesis_ref: Optional[str] = None,
        current_business_status: Optional[Dict[str, Any]] = None,
        company_intelligence_pack: Optional[Dict[str, Any]] = None,
        operating_brief_id: Optional[str] = None,
        operating_brief_version: Optional[str] = None,
        generated_by: str = "aion_equities.openai_document_analysis_runtime",
    ) -> Dict[str, Any]:
        brief = self._load_brief(
            operating_brief_id=operating_brief_id,
            operating_brief_version=operating_brief_version,
        )

        return {
            "packet_type": "openai_document_analysis",
            "generated_by": str(generated_by),
            "company_ref": str(company_ref),
            "document_ref": str(document_ref),
            "document_type": str(document_type),
            "thesis_ref": thesis_ref,
            "operating_brief": {
                "brief_id": brief.get("brief_id"),
                "version": brief.get("version"),
                "title": brief.get("title"),
                "summary": brief.get("summary"),
                "sections": deepcopy(brief.get("sections", [])),
                "brief_text": brief.get("brief_text", ""),
            },
            "current_business_status": deepcopy(current_business_status or {}),
            "company_intelligence_pack": deepcopy(company_intelligence_pack or {}),
            "document": {
                "ref": str(document_ref),
                "type": str(document_type),
                "text": str(document_text or ""),
            },
        }

    def analyze_document(
        self,
        *,
        company_ref: str,
        document_ref: str,
        document_text: str,
        document_type: str = "board_pack",
        thesis_ref: Optional[str] = None,
        current_business_status: Optional[Dict[str, Any]] = None,
        company_intelligence_pack: Optional[Dict[str, Any]] = None,
        operating_brief_id: Optional[str] = None,
        operating_brief_version: Optional[str] = None,
        generated_by: str = "aion_equities.openai_document_analysis_runtime",
    ) -> Dict[str, Any]:
        packet = self.build_document_analysis_packet(
            company_ref=company_ref,
            document_ref=document_ref,
            document_text=document_text,
            document_type=document_type,
            thesis_ref=thesis_ref,
            current_business_status=current_business_status,
            company_intelligence_pack=company_intelligence_pack,
            operating_brief_id=operating_brief_id,
            operating_brief_version=operating_brief_version,
            generated_by=generated_by,
        )

        response = self.openai_client(packet)
        if not isinstance(response, dict):
            raise TypeError("OpenAI document analysis response must be a dict")

        normalized = self._normalize_analysis_response(analysis_response=response)

        return {
            "company_ref": str(company_ref),
            "document_ref": str(document_ref),
            "document_type": str(document_type),
            "thesis_ref": thesis_ref,
            "analysis_packet": packet,
            "analysis_response": deepcopy(response),
            "normalized_analysis": deepcopy(normalized),
        }


__all__ = [
    "OpenAIDocumentAnalysisRuntime",
]