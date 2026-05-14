# /workspaces/COMDEX/backend/modules/aion_equities/openai_company_profile_mapper.py
from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Optional


class OpenAICompanyProfileMapper:
    """
    Maps structured OpenAI document analysis output into canonical
    intake objects for storage.

    Conceptual behavior: this is now an *intake mapper* (profile + quarter event + seeds),
    but we keep the existing method name for backward compatibility with tests/callers.
    """

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

    def map_analysis_to_company_profile(
        self,
        *,
        company_ref: str,
        document_ref: str,
        analysis_response: Dict[str, Any],
        thesis_ref: Optional[str] = None,
        generated_by: str = "aion_equities.openai_company_profile_mapper",
    ) -> Dict[str, Any]:
        """
        Backward-compatible entrypoint.

        Accepts either:
          - raw OpenAI analysis dict, or
          - runtime output dict containing "normalized_analysis"
        """
        if not isinstance(analysis_response, dict):
            raise TypeError("analysis_response must be a dict")

        # Allow callers to pass the full runtime response shape
        normalized = analysis_response.get("normalized_analysis")
        if isinstance(normalized, dict):
            root = normalized
        else:
            # Allow OpenAI to wrap results
            wrapped = self._coalesce(analysis_response, "analysis", "result", default=None)
            root = wrapped if isinstance(wrapped, dict) else analysis_response

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
        trigger_map = self._ensure_dict(
            self._coalesce(root, "trigger_map", "triggers", default={}),
            name="trigger_map",
        )
        feed_candidates = self._ensure_dict(
            self._coalesce(root, "feed_candidates", "feeds", default={}),
            name="feed_candidates",
        )

        # New: seeds + quarter_event
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
        if not quarter_event:
            # Derive minimal quarter_event from quarter_summary if needed
            quarter_event = {
                "headline": quarter_summary.get("headline"),
                "summary": quarter_summary.get("summary"),
                "key_numbers": deepcopy(quarter_summary.get("key_numbers", {})),
                "fiscal_period": self._coalesce(quarter_summary, "fiscal_period", "period", default=None),
                "published_at": self._coalesce(quarter_summary, "published_at", "date", default=None),
            }

        mapped: Dict[str, Any] = {
            "company_ref": str(company_ref),
            "document_ref": str(document_ref),
            "thesis_ref": thesis_ref,
            "generated_by": str(generated_by),

            # Canonical company profile object
            "company_profile": {
                "company_ref": str(company_ref),
                "name": company_profile.get("name"),
                "sector": company_profile.get("sector"),
                "country": company_profile.get("country"),
                "description": company_profile.get("description"),
                "source_document_ref": str(document_ref),
                # keep passthrough extras if provided
                "extra": deepcopy(company_profile.get("extra", {})) if isinstance(company_profile.get("extra"), dict) else {},
            },

            # Quarter summary (lightweight)
            "quarter_summary": {
                "document_ref": str(document_ref),
                "headline": quarter_summary.get("headline"),
                "summary": quarter_summary.get("summary"),
                "key_numbers": deepcopy(quarter_summary.get("key_numbers", {})),
            },

            # New: quarter event (persistence-ready seed)
            "quarter_event": {
                "company_ref": str(company_ref),
                "document_ref": str(document_ref),
                "thesis_ref": thesis_ref,
                "source_document_ref": str(document_ref),
                "fiscal_period": quarter_event.get("fiscal_period"),
                "published_at": quarter_event.get("published_at"),
                "headline": quarter_event.get("headline"),
                "summary": quarter_event.get("summary"),
                "key_numbers": deepcopy(quarter_event.get("key_numbers", {})),
                "extra": deepcopy(quarter_event.get("extra", {})) if isinstance(quarter_event.get("extra"), dict) else {},
            },

            # Fingerprint seed
            "fingerprint": {
                "company_ref": str(company_ref),
                "fingerprint_ref": fingerprint.get("fingerprint_ref"),
                "traits": deepcopy(fingerprint.get("traits", [])),
                "source_document_ref": str(document_ref),
                "extra": deepcopy(fingerprint.get("extra", {})) if isinstance(fingerprint.get("extra"), dict) else {},
            },

            # Trigger map seed
            "trigger_map": {
                "company_ref": str(company_ref),
                "triggers": deepcopy(trigger_map.get("triggers", [])),
                "source_document_ref": str(document_ref),
                "extra": deepcopy(trigger_map.get("extra", {})) if isinstance(trigger_map.get("extra"), dict) else {},
            },

            # Feed candidates seed
            "feed_candidates": {
                "company_ref": str(company_ref),
                "feeds": deepcopy(feed_candidates.get("feeds", [])),
                "source_document_ref": str(document_ref),
                "extra": deepcopy(feed_candidates.get("extra", {})) if isinstance(feed_candidates.get("extra"), dict) else {},
            },

            # New: assessment seed
            "assessment_seed": {
                "company_ref": str(company_ref),
                "document_ref": str(document_ref),
                "thesis_ref": thesis_ref,
                "source_document_ref": str(document_ref),
                "payload": deepcopy(assessment_seed),
            },

            # New: thesis seed
            "thesis_seed": {
                "company_ref": str(company_ref),
                "document_ref": str(document_ref),
                "thesis_ref": thesis_ref,
                "source_document_ref": str(document_ref),
                "payload": deepcopy(thesis_seed),
            },

            # New: variable watch seed
            "variable_watch_seed": {
                "company_ref": str(company_ref),
                "document_ref": str(document_ref),
                "thesis_ref": thesis_ref,
                "source_document_ref": str(document_ref),
                "payload": deepcopy(variable_watch_seed),
            },
        }

        # Minimum-shape enforcement (lists)
        if not isinstance(mapped["trigger_map"].get("triggers", []), list):
            mapped["trigger_map"]["triggers"] = []
        if not isinstance(mapped["feed_candidates"].get("feeds", []), list):
            mapped["feed_candidates"]["feeds"] = []
        if not isinstance(mapped["fingerprint"].get("traits", []), list):
            mapped["fingerprint"]["traits"] = []

        return mapped


__all__ = [
    "OpenAICompanyProfileMapper",
]