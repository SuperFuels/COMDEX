# /workspaces/COMDEX/backend/modules/aion_equities/openai_document_analysis_runtime.py
from __future__ import annotations

import json
from copy import deepcopy
from typing import Any, Callable, Dict, List, Optional

from backend.modules.aion_equities.openai_operating_brief_store import OpenAIOperatingBriefStore


class OpenAIDocumentAnalysisRuntime:
    """
    Phase-1: full structured intake (profile/quarter/triggers/seeds) guided by operating brief.
    Phase-2: second call that *forces* variable_watch_seed.variables to be structured objects.

    Key design choice:
      - We do NOT rely on the OpenAI client wrapper having special packet_type support.
      - Phase-2 is executed by sending packet_type=openai_document_analysis again,
        but with an overridden operating_brief.brief_text that hard-requires
        variable_watch_seed.variables schema.

    Output:
      analyze_document(...) returns:
        {
          "analysis_response": <raw phase-1 openai dict>,
          "normalized_analysis": <normalized dict, with variable_watch_seed overwritten if phase-2 succeeded>
        }
    """

    def __init__(
        self,
        *,
        operating_brief_store: OpenAIOperatingBriefStore,
        openai_client: Callable[[Dict[str, Any]], Dict[str, Any]],
        enable_phase2_variable_spec: bool = True,
        phase2_document_text_max_chars: int = 14000,
        phase2_min_vars: int = 5,
        phase2_max_vars: int = 10,
    ):
        self.operating_brief_store = operating_brief_store
        self.openai_client = openai_client
        self.enable_phase2_variable_spec = bool(enable_phase2_variable_spec)
        self.phase2_document_text_max_chars = int(phase2_document_text_max_chars)
        self.phase2_min_vars = int(phase2_min_vars)
        self.phase2_max_vars = int(phase2_max_vars)

    # -----------------------------
    # helpers
    # -----------------------------
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
                f"Operating brief version mismatch: expected {operating_brief_version}, got {brief.get('version')}"
            )

        # HARDEN: never allow empty brief_text to reach OpenAI
        brief_text = str(brief.get("brief_text") or "").strip()
        if not brief_text:
            sections = brief.get("sections") or []
            if isinstance(sections, list):
                # store back-compat already derives it, but just in case:
                brief_text = "\n\n".join(
                    str((s or {}).get("content") or (s or {}).get("body") or (s or {}).get("text") or "").strip()
                    for s in sections
                    if isinstance(s, dict) and str((s.get("content") or s.get("body") or s.get("text") or "")).strip()
                ).strip()
            brief["brief_text"] = brief_text

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

    def _truncate_text(self, text: str, limit: int) -> str:
        t = str(text or "").strip()
        if limit > 0 and len(t) > limit:
            return t[:limit]
        return t

    # -----------------------------
    # normalization
    # -----------------------------
    def _normalize_trigger_map(self, root: Dict[str, Any]) -> Dict[str, Any]:
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
        fc_candidate = self._coalesce(root, "feed_candidates", "feeds", "feed_suggestions", default={})
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

    def _normalize_analysis_response(self, *, analysis_response: Dict[str, Any]) -> Dict[str, Any]:
        raw = self._ensure_dict(analysis_response, name="analysis_response")
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

        assessment_seed = self._ensure_dict(self._coalesce(root, "assessment_seed", "assessment", default={}), name="assessment_seed")
        thesis_seed = self._ensure_dict(self._coalesce(root, "thesis_seed", "thesis", default={}), name="thesis_seed")
        variable_watch_seed = self._ensure_dict(
            self._coalesce(root, "variable_watch_seed", "variable_watch", "watchlist", "variable_watch_list", default={}),
            name="variable_watch_seed",
        )

        quarter_event = self._ensure_dict(self._coalesce(root, "quarter_event", "quarter_event_seed", default={}), name="quarter_event")
        if not quarter_event:
            quarter_event = {
                "headline": quarter_summary.get("headline"),
                "summary": quarter_summary.get("summary"),
                "key_numbers": deepcopy(quarter_summary.get("key_numbers", {})),
                "fiscal_period": self._coalesce(quarter_summary, "fiscal_period", "period", default=None),
                "published_at": self._coalesce(quarter_summary, "published_at", "date", default=None),
            }

        normalized: Dict[str, Any] = {
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
                    "company_profile","profile","company",
                    "quarter_summary","quarter","summary",
                    "quarter_event","quarter_event_seed",
                    "fingerprint","company_fingerprint",
                    "trigger_map","triggers","triggering",
                    "feed_candidates","feeds","feed_suggestions",
                    "assessment_seed","assessment",
                    "thesis_seed","thesis",
                    "variable_watch_seed","variable_watch","watchlist","variable_watch_list",
                    "analysis","result",
                }
            },
        }

        # minimum stable shape enforcement
        if not isinstance(normalized.get("trigger_map"), dict):
            normalized["trigger_map"] = {"triggers": []}
        if not isinstance(normalized.get("feed_candidates"), dict):
            normalized["feed_candidates"] = {"feeds": []}
        if not isinstance(normalized["trigger_map"].get("triggers", []), list):
            normalized["trigger_map"]["triggers"] = []
        if not isinstance(normalized["feed_candidates"].get("feeds", []), list):
            normalized["feed_candidates"]["feeds"] = []

        if not isinstance(normalized.get("variable_watch_seed"), dict):
            normalized["variable_watch_seed"] = {}

        return normalized

    # -----------------------------
    # Phase-2 variable specification
    # -----------------------------
    def _extract_phase1_variable_names(self, normalized: Dict[str, Any]) -> List[str]:
        vws = normalized.get("variable_watch_seed") or {}
        if not isinstance(vws, dict):
            return []

        names: List[str] = []

        vars_list = vws.get("variables")
        if isinstance(vars_list, list):
            for v in vars_list:
                if isinstance(v, dict) and str(v.get("name") or "").strip():
                    names.append(str(v["name"]).strip())
                elif isinstance(v, str) and v.strip():
                    names.append(v.strip())

        kv = vws.get("key_variables")
        if isinstance(kv, list):
            for s in kv:
                if isinstance(s, str) and s.strip():
                    names.append(s.strip())

        payload = vws.get("payload")
        if isinstance(payload, dict) and isinstance(payload.get("key_variables"), list):
            for s in payload["key_variables"]:
                if isinstance(s, str) and s.strip():
                    names.append(s.strip())

        out: List[str] = []
        seen = set()
        for n in names:
            base = n.split(" - ", 1)[0].strip()
            if not base or base in seen:
                continue
            seen.add(base)
            out.append(base)

        return out

    def _phase2_brief_text(self) -> str:
        return (
            "You are AION Equities Phase-2 Variable Specification.\n"
            "Your job is to output MACHINE-TRACKABLE monitoring variables.\n"
            "Return ONLY valid JSON. No markdown. No commentary.\n\n"
            "REQUIRED: You MUST include variable_watch_seed.variables as a list of 5–10 objects.\n\n"
            "Each variable object MUST include EXACTLY these keys (no missing keys):\n"
            "{\n"
            '  "name": "non-empty string",\n'
            '  "why_it_matters": "non-empty string",\n'
            '  "data_source": "non-empty string (specific named public source)",\n'
            '  "feed_id": "non-empty snake_case string, unique",\n'
            '  "current_value": number | null,\n'
            '  "unit": "% | €bn | ratio | fx | index | other (non-empty string)",\n'
            '  "lag_weeks": integer >= 0,\n'
            '  "direction": "positive" | "negative",\n'
            '  "impact_weight": number 0.05–0.30,\n'
            '  "threshold_early": "numeric comparator + time window",\n'
            '  "threshold_confirm": "numeric comparator + time window",\n'
            '  "threshold_break": "numeric comparator + time window",\n'
            '  "thesis_action_on_confirm": "non-empty string imperative",\n'
            '  "thesis_action_on_break": "non-empty string imperative"\n'
            "}\n\n"
            "STRICT RULES:\n"
            "- name/data_source/feed_id/unit/threshold_*/thesis_action_* MUST NOT be null and MUST NOT be empty.\n"
            "- current_value may be null ONLY if not found in the provided document text.\n"
            "- thresholds MUST contain numbers and a time window.\n"
            "  VALID: \"USG >= 4.0 for 1 quarter\" | \"FX(EUR/BRL) <= 5.8 for 6 weeks\".\n"
            "  INVALID: \"improving\" | \"stable\" | \"watch\".\n"
            "- feed_id MUST be snake_case and unique.\n"
            "- Order variables by impact_weight DESC.\n"
            "- Total impact_weight should sum to ~1.0 (0.8–1.2 acceptable).\n"
        )

    def _build_phase2_packet(
        self,
        *,
        company_ref: str,
        document_ref: str,
        fiscal_period_ref: Optional[str],
        document_type: str,
        thesis_ref: Optional[str],
        document_text: str,
        variable_names: List[str],
        operating_brief_id: Optional[str],
        operating_brief_version: Optional[str],
        generated_by: str,
    ) -> Dict[str, Any]:
        txt = self._truncate_text(document_text, self.phase2_document_text_max_chars)

        base_brief = self._load_brief(
            operating_brief_id=operating_brief_id,
            operating_brief_version=operating_brief_version,
        )

        sections = deepcopy(base_brief.get("sections") or [])
        sections.append(
            {
                "section_id": "phase2_variable_spec_context",
                "title": "Phase-2 Variable Spec Context",
                "content": (
                    f"Company: {company_ref}\n"
                    f"Fiscal period: {fiscal_period_ref or ''}\n"
                    f"Document ref: {document_ref}\n\n"
                    "Phase-1 variable candidates:\n"
                    f"{json.dumps(variable_names, ensure_ascii=False)}\n"
                ),
            }
        )

        # Keep packet_type=openai_document_analysis for wrapper compatibility.
        return {
            "packet_type": "openai_document_analysis",
            "generated_by": str(generated_by),
            "company_ref": str(company_ref),
            "document_ref": str(document_ref),
            "document_type": str(document_type),
            "thesis_ref": thesis_ref,
            "fiscal_period_ref": str(fiscal_period_ref or ""),
            "operating_brief": {
                "brief_id": base_brief.get("brief_id"),
                "version": base_brief.get("version"),
                "title": base_brief.get("title"),
                "summary": base_brief.get("summary"),
                "sections": sections,
                "brief_text": self._phase2_brief_text(),
            },
            "current_business_status": {},
            "company_intelligence_pack": {
                "phase2": {
                    "variable_candidates": deepcopy(variable_names),
                    "min_vars": self.phase2_min_vars,
                    "max_vars": self.phase2_max_vars,
                }
            },
            "document": {
                "ref": str(document_ref),
                "type": str(document_type),
                "text": txt,
            },
        }

    def _get_phase2_variables(self, normalized: Dict[str, Any]) -> Any:
        vws = normalized.get("variable_watch_seed")
        if isinstance(vws, dict) and isinstance(vws.get("variables"), list):
            return vws.get("variables")
        return []

    def _validate_phase2_variables(self, variables: Any) -> List[Dict[str, Any]]:
        import re

        if not isinstance(variables, list):
            return []

        required = [
            "name","why_it_matters","data_source","feed_id","current_value","unit","lag_weeks",
            "direction","impact_weight","threshold_early","threshold_confirm","threshold_break",
            "thesis_action_on_confirm","thesis_action_on_break",
        ]

        def nonempty_str(x: Any) -> bool:
            return isinstance(x, str) and x.strip() != ""

        def snake_case(s: str) -> bool:
            return bool(re.fullmatch(r"[a-z][a-z0-9_]*", s.strip()))

        def looks_like_threshold(s: Any) -> bool:
            s2 = str(s or "")
            has_cmp = any(op in s2 for op in (">=", "<=", ">", "<", "==", "="))
            has_window = any(w in s2.lower() for w in ("quarter", "quarters", "week", "weeks", "month", "months", "days", "consecutive"))
            has_number = bool(re.search(r"\d", s2))
            return has_cmp and has_window and has_number

        out: List[Dict[str, Any]] = []
        seen_feed_ids = set()

        for v in variables:
            if not isinstance(v, dict):
                continue
            if any(k not in v for k in required):
                continue

            must_str = [
                "name","why_it_matters","data_source","feed_id","unit",
                "threshold_early","threshold_confirm","threshold_break",
                "thesis_action_on_confirm","thesis_action_on_break",
            ]
            if any(not nonempty_str(v.get(k)) for k in must_str):
                continue

            direction = str(v.get("direction") or "").strip().lower()
            if direction not in {"positive", "negative"}:
                continue

            try:
                lag = int(v.get("lag_weeks"))
                if lag < 0:
                    continue
            except Exception:
                continue

            try:
                w = float(v.get("impact_weight"))
                if not (0.05 <= w <= 0.30):
                    continue
            except Exception:
                continue

            cv = v.get("current_value")
            if cv is not None:
                try:
                    float(cv)
                except Exception:
                    continue

            if not looks_like_threshold(v.get("threshold_early")):
                continue
            if not looks_like_threshold(v.get("threshold_confirm")):
                continue
            if not looks_like_threshold(v.get("threshold_break")):
                continue

            fid = str(v.get("feed_id")).strip()
            if not snake_case(fid):
                continue
            if fid in seen_feed_ids:
                continue
            seen_feed_ids.add(fid)

            out.append(deepcopy(v))

        if len(out) < self.phase2_min_vars:
            return []
        if len(out) > self.phase2_max_vars:
            out = out[: self.phase2_max_vars]

        return out

    # -----------------------------
    # Packet build + analyze
    # -----------------------------
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
        fiscal_period_ref: Optional[str] = None,
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
            "fiscal_period_ref": str(fiscal_period_ref or ""),
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
        fiscal_period_ref: Optional[str] = None,
    ) -> Dict[str, Any]:
        # ---- Phase 1 ----
        packet1 = self.build_document_analysis_packet(
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
            fiscal_period_ref=fiscal_period_ref,
        )

        response1 = self.openai_client(packet1)
        if not isinstance(response1, dict):
            raise TypeError("OpenAI document analysis response must be a dict")

        normalized = self._normalize_analysis_response(analysis_response=response1)

        # ---- Phase 2 (optional) ----
        if self.enable_phase2_variable_spec:
            candidates = self._extract_phase1_variable_names(normalized)

            # If phase-1 was shallow, still run phase-2 using any key_variables as fallback.
            if not candidates:
                vws = normalized.get("variable_watch_seed") or {}
                if isinstance(vws, dict):
                    payload = vws.get("payload")
                    if isinstance(payload, dict) and isinstance(payload.get("key_variables"), list):
                        candidates = [
                            str(x).split(" - ", 1)[0].strip()
                            for x in payload.get("key_variables", [])
                            if str(x).strip()
                        ]
                candidates = [c for c in candidates if c]

            if candidates:
                packet2 = self._build_phase2_packet(
                    company_ref=company_ref,
                    document_ref=document_ref,
                    fiscal_period_ref=fiscal_period_ref,
                    document_type=document_type,
                    thesis_ref=thesis_ref,
                    document_text=document_text,
                    variable_names=candidates,
                    operating_brief_id=operating_brief_id,
                    operating_brief_version=operating_brief_version,
                    generated_by=generated_by,
                )

                try:
                    response2 = self.openai_client(packet2)
                except Exception:
                    response2 = None

                if isinstance(response2, dict):
                    normalized2 = self._normalize_analysis_response(analysis_response=response2)
                    vars_any = self._get_phase2_variables(normalized2)
                    variables = self._validate_phase2_variables(vars_any)

                    normalized.setdefault("_extra", {})
                    normalized["_extra"]["phase2_variable_candidates"] = deepcopy(candidates)
                    normalized["_extra"]["phase2_raw_response"] = deepcopy(response2)

                    if variables:
                        normalized["variable_watch_seed"] = {
                            "variables": deepcopy(variables),
                            "phase2_generated_by": str(generated_by),
                        }
                    else:
                        normalized["_extra"]["phase2_validation_failed"] = True
                        normalized["_extra"]["phase2_received_var_count"] = len(vars_any) if isinstance(vars_any, list) else None

        return {
            "company_ref": str(company_ref),
            "document_ref": str(document_ref),
            "document_type": str(document_type),
            "thesis_ref": thesis_ref,
            "analysis_packet": packet1,
            "analysis_response": deepcopy(response1),
            "normalized_analysis": deepcopy(normalized),
        }


__all__ = ["OpenAIDocumentAnalysisRuntime"]