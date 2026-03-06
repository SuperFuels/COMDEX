# /workspaces/COMDEX/backend/modules/aion_equities/openai_document_intake_runtime.py
from __future__ import annotations

import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from backend.modules.aion_equities.assessment_runtime import AssessmentRuntime
from backend.modules.aion_equities.assessment_store import AssessmentStore
from backend.modules.aion_equities.company_trigger_map_store import CompanyTriggerMapStore
from backend.modules.aion_equities.openai_company_profile_mapper import OpenAICompanyProfileMapper
from backend.modules.aion_equities.openai_document_analysis_runtime import OpenAIDocumentAnalysisRuntime
from backend.modules.aion_equities.quarter_event_store import QuarterEventStore
from backend.modules.aion_equities.reference_maintenance_runtime import ReferenceMaintenanceRuntime
from backend.modules.aion_equities.source_document_store import SourceDocumentStore
from backend.modules.aion_equities.thesis_runtime import ThesisRuntime
from backend.modules.aion_equities.thesis_store import ThesisStore
from backend.modules.aion_equities.variable_watch_store import VariableWatchStore


def _safe_read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _safe_read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _coalesce(*values: Any, default: Any = None) -> Any:
    for v in values:
        if v is None:
            continue
        if isinstance(v, str):
            if v.strip():
                return v
            continue
        return v
    return default


def _ticker_from_company_ref(company_ref: str) -> str:
    # company/ULVR.L -> ULVR.L
    parts = str(company_ref or "").split("/")
    return parts[-1].strip() if parts else ""


def _company_folder_name(company_ref: str) -> str:
    # repo uses: company_ULVR.L
    t = _ticker_from_company_ref(company_ref)
    return f"company_{t}" if t else "company_unknown"


def _normalize_key(s: Any) -> str:
    """
    Used for matching master variable name <-> trigger variable_name.
    Keeps this intentionally conservative (no lossy tokenization).
    """
    txt = str(s or "").strip().lower()
    txt = re.sub(r"\s+", " ", txt)
    return txt


class OpenAIDocumentIntakeRuntime:
    """
    End-to-end document intake bridge.

    Responsibilities:
    - call OpenAI document analysis runtime (Phase-1 + optional Phase-2)
    - normalize the analysis result
    - map normalized analysis into persistence-ready AION intake objects
    - persist quarter-event output automatically (if store provided)
    - persist trigger-map output automatically (if store provided)
    - persist variable-watch output automatically (if store provided)
    - build + persist assessment (if runtime+store provided)
    - build + persist thesis (if runtime+store provided)
    - update company reference pointers (if reference maintenance runtime provided)
    - OPTIONAL: auto-load document_text from SourceDocumentStore.parsed_text_ref if document_text empty
    - HARDEN: ensure quarter_event seed contains fiscal_period (required by QuarterEventStore)
    - HARDEN: allow caller to provide fiscal_period_ref so we never fall back to "unknown" for period-bearing stores

    NEW (critical):
    - Load master variables from:
        backend/modules/aion_equities/master_intelligence/company_<TICKER>/v1.variables.json
      and:
        * if OpenAI yields 0 variables -> fallback to master variables (never persist empty)
        * otherwise -> merge master + OpenAI variables (master baseline + any new candidates)

    NEW (critical for live monitoring):
    - Enrich trigger entries with feed_id (machine routing key) using master variables,
      because trigger map stores typically have only human labels in data_source.
    """

    def __init__(
        self,
        *,
        document_analysis_runtime: OpenAIDocumentAnalysisRuntime,
        company_profile_mapper: OpenAICompanyProfileMapper,
        quarter_event_store: Optional[QuarterEventStore] = None,
        company_trigger_map_store: Optional[CompanyTriggerMapStore] = None,
        variable_watch_store: Optional[VariableWatchStore] = None,
        assessment_runtime: Optional[AssessmentRuntime] = None,
        assessment_store: Optional[AssessmentStore] = None,
        thesis_runtime: Optional[ThesisRuntime] = None,
        thesis_store: Optional[ThesisStore] = None,
        reference_maintenance_runtime: Optional[ReferenceMaintenanceRuntime] = None,
        # allow auto-loading text from a registered source document
        source_document_store: Optional[SourceDocumentStore] = None,
        document_text_base_dir: Optional[str | Path] = None,
        # master intelligence (repo canonical)
        master_intelligence_base_dir: Optional[str | Path] = None,
        master_variables_version: str = "v1",
        use_master_variables_fallback: bool = True,
        merge_master_variables: bool = True,
    ):
        self.document_analysis_runtime = document_analysis_runtime
        self.company_profile_mapper = company_profile_mapper
        self.quarter_event_store = quarter_event_store
        self.company_trigger_map_store = company_trigger_map_store
        self.variable_watch_store = variable_watch_store
        self.assessment_runtime = assessment_runtime
        self.assessment_store = assessment_store
        self.thesis_runtime = thesis_runtime
        self.thesis_store = thesis_store
        self.reference_maintenance_runtime = reference_maintenance_runtime

        self.source_document_store = source_document_store
        self.document_text_base_dir = Path(document_text_base_dir) if document_text_base_dir else None

        # Default repo canonical master intelligence location:
        # /workspaces/COMDEX/backend/modules/aion_equities/master_intelligence
        if master_intelligence_base_dir is None:
            self.master_intelligence_base_dir = Path(__file__).resolve().parent / "master_intelligence"
        else:
            self.master_intelligence_base_dir = Path(master_intelligence_base_dir)

        self.master_variables_version = str(master_variables_version or "v1").strip() or "v1"
        self.use_master_variables_fallback = bool(use_master_variables_fallback)
        self.merge_master_variables = bool(merge_master_variables)

    # -----------------------------
    # document text autoload
    # -----------------------------
    def _autoload_document_text(self, *, document_ref: str) -> str:
        """
        Best-effort:
        - load source document by id using whatever method the store exposes
        - read parsed text ref from disk (absolute or relative)
        """
        if self.source_document_store is None:
            return ""

        doc: Optional[Dict[str, Any]] = None
        store = self.source_document_store

        for fn_name in (
            "load_source_document",
            "load_source_document_by_id",
            "load_document",
            "load_by_id",
        ):
            fn = getattr(store, fn_name, None)
            if callable(fn):
                try:
                    doc = fn(str(document_ref))
                    if isinstance(doc, dict):
                        break
                except Exception:
                    doc = None

        if not isinstance(doc, dict):
            return ""

        parsed_text_ref = doc.get("parsed_text_ref")
        if not parsed_text_ref and isinstance(doc.get("parsed_text"), dict):
            parsed_text_ref = (
                doc["parsed_text"].get("ref")
                or doc["parsed_text"].get("path")
                or doc["parsed_text"].get("file")
            )
        if not parsed_text_ref:
            parsed_text_ref = doc.get("text_ref") or doc.get("extracted_text_ref")

        if not parsed_text_ref:
            return ""

        ref = str(parsed_text_ref).strip()
        if not ref:
            return ""

        p = Path(ref)
        if not p.is_absolute():
            if self.document_text_base_dir is not None:
                p = (self.document_text_base_dir / ref).resolve()
            else:
                p = p.resolve()

        if not p.exists() or not p.is_file():
            return ""

        return _safe_read_text(p)

    # -----------------------------
    # master intelligence (variables)
    # -----------------------------
    def _master_variables_path(self, *, company_ref: str) -> Path:
        folder = _company_folder_name(company_ref)
        # backend/modules/aion_equities/master_intelligence/company_ULVR.L/v1.variables.json
        return self.master_intelligence_base_dir / folder / f"{self.master_variables_version}.variables.json"

    def _load_master_variables(self, *, company_ref: str) -> List[Dict[str, Any]]:
        p = self._master_variables_path(company_ref=company_ref)
        obj = _safe_read_json(p)
        if isinstance(obj, list):
            out: List[Dict[str, Any]] = []
            for it in obj:
                if isinstance(it, dict):
                    out.append(deepcopy(it))
            return out
        return []

    def _index_master_variables(self, *, master_vars: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        Two indices:
          - by feed_id (strong)
          - by name (for trigger_map variable_name matching)
        """
        out: Dict[str, Dict[str, Any]] = {}
        for v in master_vars or []:
            if not isinstance(v, dict):
                continue

            fid = str(v.get("feed_id") or "").strip()
            if fid:
                out[f"feed_id:{fid}"] = v

            name = _normalize_key(v.get("name"))
            if name:
                out[f"name:{name}"] = v

            vid = str(v.get("variable_id") or "").strip()
            if vid:
                out[f"variable_id:{vid}"] = v

        return out

    def _extract_ai_variables_from_mapped(self, mapped_objects: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Mapper stores:
          mapped_objects["variable_watch_seed"] = {"payload": <seed>}
        where seed ideally contains {"variables":[...]}
        """
        if not isinstance(mapped_objects, dict):
            return []

        vws = mapped_objects.get("variable_watch_seed")
        if not isinstance(vws, dict):
            return []

        payload = vws.get("payload")
        if not isinstance(payload, dict):
            return []

        variables = payload.get("variables")
        if isinstance(variables, list):
            return [deepcopy(v) for v in variables if isinstance(v, dict)]
        return []

    def _merge_variables(
        self,
        *,
        master_vars: List[Dict[str, Any]],
        ai_vars: List[Dict[str, Any]],
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Merge policy:
          - Use master as baseline.
          - Add any AI variables not present in master (by feed_id or variable_id).
          - For collisions: keep master, but fill missing keys from AI if master is missing/empty.
            (Does NOT overwrite good master definitions.)

        Returns: (merged_vars, stats)
        """
        stats: Dict[str, Any] = {
            "master_count": len(master_vars),
            "ai_count": len(ai_vars),
            "merged_count": 0,
            "added_from_ai": 0,
            "filled_from_ai": 0,
            "skipped_ai_missing_key": 0,
        }

        def key(v: Dict[str, Any]) -> str:
            fid = str(v.get("feed_id") or "").strip()
            if fid:
                return f"feed_id:{fid}"
            vid = str(v.get("variable_id") or "").strip()
            if vid:
                return f"variable_id:{vid}"
            return ""

        merged: List[Dict[str, Any]] = []
        index: Dict[str, Dict[str, Any]] = {}

        # load master first
        for v in master_vars:
            if not isinstance(v, dict):
                continue
            k = key(v)
            if not k:
                continue
            vv = deepcopy(v)
            index[k] = vv
            merged.append(vv)

        # merge in AI
        for v in ai_vars:
            if not isinstance(v, dict):
                continue
            k = key(v)
            if not k:
                stats["skipped_ai_missing_key"] += 1
                continue

            if k not in index:
                index[k] = deepcopy(v)
                merged.append(index[k])
                stats["added_from_ai"] += 1
                continue

            # collision: fill missing keys only
            base = index[k]
            filled_any = False
            for kk, vv in v.items():
                if kk not in base:
                    base[kk] = deepcopy(vv)
                    filled_any = True
                    continue

                bv = base.get(kk)
                if bv is None and vv is not None:
                    base[kk] = deepcopy(vv)
                    filled_any = True
                    continue

                if isinstance(bv, str) and not bv.strip() and vv is not None:
                    base[kk] = deepcopy(vv)
                    filled_any = True
                    continue

                if isinstance(bv, list) and len(bv) == 0 and isinstance(vv, list) and len(vv) > 0:
                    base[kk] = deepcopy(vv)
                    filled_any = True
                    continue

                if isinstance(bv, dict) and len(bv) == 0 and isinstance(vv, dict) and len(vv) > 0:
                    base[kk] = deepcopy(vv)
                    filled_any = True
                    continue

            if filled_any:
                stats["filled_from_ai"] += 1

        stats["merged_count"] = len(merged)
        return merged, stats

    def _build_variable_watch_seed(self, *, variables: List[Dict[str, Any]], source: str) -> Dict[str, Any]:
        # VariableWatchStore keeps payload, and extracts variables from multiple shapes.
        return {
            "variables": deepcopy(variables),
            "seed_source": str(source),
        }

    # -----------------------------
    # trigger-map enrichment
    # -----------------------------
    def _enrich_trigger_entries_with_feed_ids(
        self,
        *,
        trigger_entries: Any,
        company_ref: str,
        master_index: Dict[str, Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Ensures each trigger entry has feed_id as a machine routing key.

        Your trigger map payload on disk uses:
          trigger_entries: [{variable_name, data_source, ...}]
        NOT:
          triggers: [...]

        We match:
          trigger["variable_name"]  <-> master_var["name"]
        and then set:
          trigger["feed_id"] = master_var["feed_id"]
          trigger["data_source_id"] = same feed_id (optional alias)
        """
        entries: List[Dict[str, Any]] = []
        if isinstance(trigger_entries, list):
            for t in trigger_entries:
                if isinstance(t, dict):
                    entries.append(deepcopy(t))
        if not entries:
            return []

        for t in entries:
            if str(t.get("feed_id") or "").strip():
                continue

            vname = _normalize_key(t.get("variable_name") or t.get("name"))
            if not vname:
                continue

            mv = master_index.get(f"name:{vname}")
            if not mv:
                # Some stored trigger maps might have slightly different casing/punctuation.
                # Don't do aggressive fuzzy matching here; keep safe.
                continue

            fid = str(mv.get("feed_id") or "").strip()
            if not fid:
                continue

            t["feed_id"] = fid
            t.setdefault("data_source_id", fid)

        return entries

    # -----------------------------
    # fiscal period helpers
    # -----------------------------
    def _derive_fiscal_period_ref(
        self,
        *,
        analysis_out: Dict[str, Any],
        mapped_objects: Dict[str, Any],
        fallback: str = "unknown",
    ) -> str:
        norm = analysis_out.get("normalized_analysis") or {}
        quarter_event = norm.get("quarter_event") or {}
        quarter_summary = norm.get("quarter_summary") or {}

        fiscal = _coalesce(
            quarter_event.get("fiscal_period"),
            quarter_summary.get("fiscal_period"),
            (mapped_objects.get("quarter_event") or {}).get("fiscal_period"),
            (mapped_objects.get("quarter_summary") or {}).get("fiscal_period"),
            (mapped_objects.get("quarter_event") or {}).get("period"),
            default=fallback,
        )
        return str(fiscal)

    def _ensure_quarter_event_seed_minimum(
        self,
        *,
        quarter_event_seed: Dict[str, Any],
        analysis_out: Dict[str, Any],
        mapped_objects: Dict[str, Any],
        document_ref: str,
        fallback_period: str,
    ) -> Dict[str, Any]:
        """
        QuarterEventStore requires fiscal_period/period to exist and be parseable (YYYY-Q#).
        We guarantee fiscal_period and set a couple of useful fallbacks.
        """
        out = deepcopy(quarter_event_seed)

        if not str(out.get("fiscal_period") or "").strip():
            out["fiscal_period"] = self._derive_fiscal_period_ref(
                analysis_out=analysis_out,
                mapped_objects=mapped_objects,
                fallback=fallback_period,
            )

        if not str(out.get("source_document_ref") or "").strip():
            out["source_document_ref"] = str(document_ref)

        if not str(out.get("published_at") or "").strip():
            norm = analysis_out.get("normalized_analysis") or {}
            out["published_at"] = _coalesce(
                (norm.get("quarter_event") or {}).get("published_at"),
                (norm.get("quarter_summary") or {}).get("published_at"),
                (mapped_objects.get("quarter_summary") or {}).get("published_at"),
                default=None,
            )

        return out

    # -----------------------------
    # main entrypoint
    # -----------------------------
    def run_document_intake(
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
        generated_by: str = "aion_equities.openai_document_intake_runtime",
        persist_quarter_event: bool = True,
        persist_trigger_map: bool = True,
        persist_variable_watch: bool = True,
        persist_assessment: bool = True,
        persist_thesis: bool = True,
        trigger_map_fiscal_period_ref: Optional[str] = None,
        update_company_references: bool = True,
        autoload_document_text: bool = True,
        fiscal_period_ref: Optional[str] = None,
    ) -> Dict[str, Any]:
        resolved_document_text = str(document_text or "")
        if autoload_document_text and not resolved_document_text.strip():
            resolved_document_text = self._autoload_document_text(document_ref=document_ref)

        # Prefer caller-provided fiscal_period_ref for anything that must be parseable.
        period_fallback = str(fiscal_period_ref or "").strip() or "unknown"

        # Load master vars once (used for:
        #   - OpenAI context injection
        #   - variable_watch fallback/merge
        #   - trigger_map feed_id enrichment)
        master_vars = self._load_master_variables(company_ref=company_ref)
        master_index = self._index_master_variables(master_vars=master_vars)

        # Inject master context for OpenAI (optional, bounded).
        cip = deepcopy(company_intelligence_pack or {})
        if master_vars:
            cip.setdefault("master", {})
            cip["master"].setdefault("variables_version", self.master_variables_version)
            cip["master"].setdefault("variables_count", len(master_vars))
            cip["master"]["variables"] = deepcopy(master_vars)

        analysis_out = self.document_analysis_runtime.analyze_document(
            company_ref=company_ref,
            document_ref=document_ref,
            document_text=resolved_document_text,
            document_type=document_type,
            thesis_ref=thesis_ref,
            current_business_status=deepcopy(current_business_status or {}),
            company_intelligence_pack=cip,
            operating_brief_id=operating_brief_id,
            operating_brief_version=operating_brief_version,
            generated_by=generated_by,
            fiscal_period_ref=fiscal_period_ref,
        )

        mapped_objects = self.company_profile_mapper.map_analysis_to_company_profile(
            company_ref=company_ref,
            document_ref=document_ref,
            analysis_response=deepcopy(analysis_out),
            thesis_ref=thesis_ref,
            generated_by=generated_by,
        )

        persisted_objects: Dict[str, Any] = {}
        persisted_objects["resolved_document_text_len"] = len(resolved_document_text or "")

        # If caller didn't provide, derive from analysis/mapped
        if period_fallback == "unknown":
            period_fallback = self._derive_fiscal_period_ref(
                analysis_out=analysis_out,
                mapped_objects=mapped_objects,
                fallback="unknown",
            )

        # -----------------------
        # Quarter event persistence
        # -----------------------
        if persist_quarter_event and self.quarter_event_store is not None:
            quarter_event_seed = deepcopy(mapped_objects.get("quarter_event") or {})
            if isinstance(quarter_event_seed, dict) and quarter_event_seed:
                quarter_event_seed = self._ensure_quarter_event_seed_minimum(
                    quarter_event_seed=quarter_event_seed,
                    analysis_out=analysis_out,
                    mapped_objects=mapped_objects,
                    document_ref=document_ref,
                    fallback_period=period_fallback,
                )

                saved_quarter_event = self.quarter_event_store.save_quarter_event(
                    company_ref=company_ref,
                    document_ref=document_ref,
                    thesis_ref=thesis_ref,
                    quarter_event=quarter_event_seed,
                )
                persisted_objects["quarter_event"] = deepcopy(saved_quarter_event)
                persisted_objects["quarter_event_ref"] = saved_quarter_event.get("quarter_event_id")

        # -----------------------
        # Trigger map persistence (now enriched with feed_id)
        # -----------------------
        if persist_trigger_map and self.company_trigger_map_store is not None:
            trigger_map_seed = deepcopy(mapped_objects.get("trigger_map") or {})
            if isinstance(trigger_map_seed, dict):
                triggers = trigger_map_seed.get("trigger_entries")
                if triggers is None:
                    triggers = trigger_map_seed.get("triggers")

                if isinstance(triggers, list) and len(triggers) > 0:
                    fiscal_period = _coalesce(
                        trigger_map_fiscal_period_ref,
                        self._derive_fiscal_period_ref(
                            analysis_out=analysis_out,
                            mapped_objects=mapped_objects,
                            fallback=period_fallback,
                        ),
                        default=period_fallback,
                    )

                    enriched = self._enrich_trigger_entries_with_feed_ids(
                        trigger_entries=triggers,
                        company_ref=company_ref,
                        master_index=master_index,
                    )

                    persisted_objects["trigger_map_enriched_count"] = len(enriched)
                    persisted_objects["trigger_map_enriched_missing_feed_id"] = sum(
                        1 for t in enriched if isinstance(t, dict) and not str(t.get("feed_id") or "").strip()
                    )

                    saved_trigger_map = self.company_trigger_map_store.save_company_trigger_map(
                        company_ref=company_ref,
                        fiscal_period_ref=str(fiscal_period),
                        trigger_entries=deepcopy(enriched),
                        generated_by=generated_by,
                        validate=False,
                        linked_refs_patch={
                            "source_document_ref": str(document_ref),
                            "thesis_ref": thesis_ref,
                        },
                    )
                    persisted_objects["trigger_map"] = deepcopy(saved_trigger_map)
                    persisted_objects["trigger_map_ref"] = saved_trigger_map.get("company_trigger_map_id")

        # -----------------------
        # Variable watch persistence (MASTER SAFE)
        # -----------------------
        if persist_variable_watch and self.variable_watch_store is not None:
            ai_vars = self._extract_ai_variables_from_mapped(mapped_objects)

            variables_to_persist: List[Dict[str, Any]] = []
            vw_seed_source = "openai"

            if ai_vars:
                if self.merge_master_variables and master_vars:
                    merged, stats = self._merge_variables(master_vars=master_vars, ai_vars=ai_vars)
                    variables_to_persist = merged
                    vw_seed_source = "master+openai"
                    persisted_objects["variable_watch_merge_stats"] = stats
                else:
                    variables_to_persist = ai_vars
                    vw_seed_source = "openai"
            else:
                if self.use_master_variables_fallback and master_vars:
                    variables_to_persist = master_vars
                    vw_seed_source = "master_fallback"
                else:
                    variables_to_persist = []
                    vw_seed_source = "empty"

            persisted_objects["variable_watch_source"] = vw_seed_source
            persisted_objects["variable_watch_ai_count"] = len(ai_vars)
            persisted_objects["variable_watch_master_count"] = len(master_vars)
            persisted_objects["variable_watch_persist_count"] = len(variables_to_persist)

            if variables_to_persist:
                vw_seed = self._build_variable_watch_seed(variables=variables_to_persist, source=vw_seed_source)
                saved_vw = self.variable_watch_store.save_variable_watch(
                    company_ref=company_ref,
                    fiscal_period_ref=str(period_fallback),
                    variable_watch_seed=vw_seed,
                    generated_by=generated_by,
                    validate=False,
                )
                persisted_objects["variable_watch"] = deepcopy(saved_vw)
                persisted_objects["variable_watch_ref"] = saved_vw.get("variable_watch_id")
            else:
                persisted_objects["variable_watch_not_saved"] = True

        # -----------------------
        # Assessment persistence (runtime-built from saved quarter_event)
        # -----------------------
        if persist_assessment and self.assessment_runtime is not None and self.assessment_store is not None:
            quarter_event_id = persisted_objects.get("quarter_event_ref")
            if isinstance(quarter_event_id, str) and quarter_event_id:
                assessment_payload = self.assessment_runtime.build_assessment(
                    company_ref=company_ref,
                    quarter_event_id=quarter_event_id,
                    thesis_ref=thesis_ref,
                    write_to_kg=False,
                    write_to_sqi_container=False,
                )
                self.assessment_store.save_assessment_payload(
                    assessment_payload,
                    create_write_event=True,
                    generated_by=generated_by,
                    validate=False,
                )
                persisted_objects["assessment"] = deepcopy(assessment_payload)
                persisted_objects["assessment_ref"] = assessment_payload.get("assessment_id")

        # -----------------------
        # Thesis persistence (built from assessment + optional seed mode/window)
        # -----------------------
        if persist_thesis and self.thesis_runtime is not None:
            assessment_payload = persisted_objects.get("assessment")
            if isinstance(assessment_payload, dict) and assessment_payload:
                seed: Dict[str, Any] = {}
                if isinstance(mapped_objects.get("thesis_seed"), dict):
                    seed = deepcopy((mapped_objects["thesis_seed"] or {}).get("payload") or {})

                mode = str(seed.get("mode") or "long")
                window = str(seed.get("window") or "medium_term")

                thesis_payload = self.thesis_runtime.build_thesis(
                    company_ref=company_ref,
                    assessment=assessment_payload,
                    mode=mode,
                    window=window,
                    trigger_map_ref=persisted_objects.get("trigger_map_ref"),
                    quarter_event_ref=persisted_objects.get("quarter_event_ref"),
                    write_to_store=False,
                    write_to_kg=False,
                    write_to_sqi_container=False,
                )

                if self.thesis_store is not None:
                    if hasattr(self.thesis_store, "save_thesis"):
                        self.thesis_store.save_thesis(
                            thesis_payload,
                            create_write_event=True,
                            generated_by=generated_by,
                            validate=False,
                        )
                    else:
                        self.thesis_store.save_thesis_state(
                            thesis_id=thesis_payload.get("thesis_id"),
                            ticker=thesis_payload.get("ticker") or company_ref.split("/")[-1],
                            mode=thesis_payload.get("mode", "long"),
                            window=thesis_payload.get("window", "medium_term"),
                            as_of=thesis_payload.get("as_of"),
                            assessment_refs=list(
                                (thesis_payload.get("linked_refs") or {}).get("assessment_refs") or []
                            ),
                            status=thesis_payload.get("status", "candidate"),
                            generated_by=generated_by,
                            create_write_event=True,
                            validate=False,
                        )

                persisted_objects["thesis"] = deepcopy(thesis_payload)
                persisted_objects["thesis_ref"] = thesis_payload.get("thesis_id")

        # -----------------------
        # Reference maintenance (company pointers)
        # -----------------------
        if update_company_references and self.reference_maintenance_runtime is not None:
            try:
                self.reference_maintenance_runtime.refresh_from_runtime_objects(
                    company_ref=company_ref,
                    assessment=persisted_objects.get("assessment"),
                    thesis=persisted_objects.get("thesis"),
                    quarter_event=persisted_objects.get("quarter_event"),
                    catalyst_event_ref=None,
                    trigger_map_ref=persisted_objects.get("trigger_map_ref"),
                    variable_watch_ref=persisted_objects.get("variable_watch_ref"),
                )
            except TypeError:
                self.reference_maintenance_runtime.refresh_from_runtime_objects(
                    company_ref=company_ref,
                    assessment=persisted_objects.get("assessment"),
                    thesis=persisted_objects.get("thesis"),
                    quarter_event=persisted_objects.get("quarter_event"),
                    catalyst_event_ref=None,
                )

            persisted_objects["company_ref_update_applied"] = True

        return {
            "company_ref": str(company_ref),
            "document_ref": str(document_ref),
            "document_type": str(document_type),
            "thesis_ref": thesis_ref,
            "analysis_packet": deepcopy(analysis_out.get("analysis_packet")),
            "analysis_response": deepcopy(analysis_out.get("analysis_response")),
            "normalized_analysis": deepcopy(analysis_out.get("normalized_analysis")),
            "mapped_objects": deepcopy(mapped_objects),
            "persisted_objects": deepcopy(persisted_objects),
        }

    def intake_document(self, **kwargs: Any) -> Dict[str, Any]:
        return self.run_document_intake(**kwargs)


__all__ = ["OpenAIDocumentIntakeRuntime"]