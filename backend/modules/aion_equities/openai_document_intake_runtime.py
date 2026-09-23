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
    Conservative normalization only (no lossy tokenization).
    """
    txt = str(s or "").strip().lower()
    txt = re.sub(r"\s+", " ", txt)
    return txt


def _safe_float(x: Any) -> Optional[float]:
    try:
        if x is None:
            return None
        if isinstance(x, bool):
            return None
        if isinstance(x, (int, float)):
            v = float(x)
            if v != v:
                return None
            return v
        s = str(x).strip()
        if not s:
            return None
        s = s.replace(",", "")
        v = float(s)
        if v != v:
            return None
        return v
    except Exception:
        return None


def _find_first_number(text: str, patterns: List[re.Pattern]) -> Optional[float]:
    for pat in patterns:
        m = pat.search(text)
        if not m:
            continue
        num = m.group("num") if "num" in m.groupdict() else None
        if num is None:
            try:
                num = m.group(1)
            except Exception:
                num = None
        v = _safe_float(num)
        if v is not None:
            return v
    return None


# -----------------------------------------------------------------------------
# Generic parsing helpers (NOT company-specific)
# -----------------------------------------------------------------------------

def _parse_amount_to_bn(
    text: str,
    *,
    currency_symbols: Tuple[str, ...],
    currency_codes: Tuple[str, ...],
) -> Optional[float]:
    """
    Best-effort parse of money amounts to "bn" of that currency.

    Examples (any of the allowed symbols/codes):
      - "£5.9bn" / "GBP 5.9 billion" -> 5.9
      - "£5,900 million" / "GBP 5900m" -> 5.9
      - "€670 million" / "EUR 0.67bn" -> 0.67
    """
    t = text or ""
    sym = "|".join(re.escape(s) for s in currency_symbols if s)
    code = "|".join(re.escape(c) for c in currency_codes if c)

    pats = [
        re.compile(
            rf"(?:{sym})\s*(?P<num>\d+(?:\.\d+)?)\s*(?P<unit>bn|billion)\b",
            re.IGNORECASE,
        ),
        re.compile(
            rf"(?:{sym})\s*(?P<num>\d+(?:\.\d+)?)\s*(?P<unit>m|mm|million)\b",
            re.IGNORECASE,
        ),
        re.compile(
            rf"\b(?:{code})\s*(?P<num>\d+(?:\.\d+)?)\s*(?P<unit>bn|billion)\b",
            re.IGNORECASE,
        ),
        re.compile(
            rf"\b(?:{code})\s*(?P<num>\d+(?:\.\d+)?)\s*(?P<unit>m|mm|million)\b",
            re.IGNORECASE,
        ),
    ]

    for pat in pats:
        m = pat.search(t)
        if not m:
            continue
        num = _safe_float(m.group("num"))
        if num is None:
            continue
        unit = (m.group("unit") or "").lower()
        if unit in {"bn", "billion"}:
            return round(num, 6)
        if unit in {"m", "mm", "million"}:
            return round(num / 1000.0, 6)

    return None


def _parse_eur_savings_to_billion(text: str) -> Optional[float]:
    # Kept for backward compatibility (calls the generic parser)
    return _parse_amount_to_bn(text, currency_symbols=("€",), currency_codes=("EUR",))


def _parse_gbp_amount_to_bn(text: str) -> Optional[float]:
    # Kept for backward compatibility (calls the generic parser)
    return _parse_amount_to_bn(text, currency_symbols=("£",), currency_codes=("GBP",))


# -----------------------------------------------------------------------------
# ULVR-only extractors (explicitly gated later; safe to keep here)
# -----------------------------------------------------------------------------

def _extract_unilever_reported_metrics(document_text: str) -> Dict[str, Optional[float]]:
    """
    ULVR-only: Extracts current (reported) values from ULVR-style docs.

    Returns:
      - ulvr_group_usg: %
      - ulvr_group_uvg: %
      - ulvr_uom: %
      - ulvr_productivity_savings: €bn (cumulative)
    """
    t = document_text or ""

    usg_pats = [
        re.compile(r"\bUnderlying\s+sales\s+growth\s*\(USG\)\s*(?P<num>-?\d+(?:\.\d+)?)\s*%", re.IGNORECASE),
        re.compile(r"\bUSG\b[^\d\-]{0,20}(?P<num>-?\d+(?:\.\d+)?)\s*%", re.IGNORECASE),
    ]
    uvg_pats = [
        re.compile(r"\bwith\s*(?P<num>-?\d+(?:\.\d+)?)\s*%\s*volume\s+growth\b", re.IGNORECASE),
        re.compile(r"\bUnderlying\s+volume\s+growth\s*\(UVG\)\s*(?P<num>-?\d+(?:\.\d+)?)\s*%", re.IGNORECASE),
        re.compile(r"\bUVG\b[^\d\-]{0,20}(?P<num>-?\d+(?:\.\d+)?)\s*%", re.IGNORECASE),
    ]
    uom_pats = [
        re.compile(r"\bUnderlying\s+operating\s+margin\b[^\d\-]{0,30}(?P<num>-?\d+(?:\.\d+)?)\s*%", re.IGNORECASE),
        re.compile(r"\bUOM\b[^\d\-]{0,20}(?P<num>-?\d+(?:\.\d+)?)\s*%", re.IGNORECASE),
    ]

    usg = _find_first_number(t, usg_pats)
    uvg = _find_first_number(t, uvg_pats)
    uom = _find_first_number(t, uom_pats)

    savings = None
    for m in re.finditer(r"productivity\s+programme.{0,200}", t, flags=re.IGNORECASE | re.DOTALL):
        window = m.group(0)
        savings = _parse_eur_savings_to_billion(window)
        if savings is not None:
            break
    if savings is None:
        savings = _parse_eur_savings_to_billion(t)

    return {
        "ulvr_group_usg": usg,
        "ulvr_group_uvg": uvg,
        "ulvr_uom": uom,
        "ulvr_productivity_savings": savings,
    }


def _extract_unilever_financial_metrics(document_text: str) -> Dict[str, Optional[float]]:
    """
    ULVR-only: best-effort extraction for:
      - ulvr_fcf_gbp_bn: £bn
      - ulvr_cash_conversion_pct: %
      - ulvr_net_debt_leverage_x: x
      - ulvr_buyback_gbp_bn: £bn
      - ulvr_dividend_gbp_bn: £bn
    """
    t = document_text or ""

    # FCF (£bn)
    fcf = None
    for m in re.finditer(r"(free\s+cash\s+flow|\bFCF\b).{0,120}", t, flags=re.IGNORECASE | re.DOTALL):
        window = m.group(0)
        v = _parse_gbp_amount_to_bn(window)
        if v is not None:
            fcf = v
            break

    # Cash conversion (%)
    cash_conv_pats = [
        re.compile(r"\bcash\s+conversion\b[^\d]{0,40}(?P<num>-?\d+(?:\.\d+)?)\s*%", re.IGNORECASE),
        re.compile(r"\bfcf\s+conversion\b[^\d]{0,40}(?P<num>-?\d+(?:\.\d+)?)\s*%", re.IGNORECASE),
        re.compile(r"\bfree\s+cash\s+flow\s+conversion\b[^\d]{0,40}(?P<num>-?\d+(?:\.\d+)?)\s*%", re.IGNORECASE),
    ]
    cash_conv = _find_first_number(t, cash_conv_pats)

    # Net debt leverage (x)
    lev_pats = [
        re.compile(r"\bnet\s+debt\b.{0,80}?(?P<num>\d+(?:\.\d+)?)\s*x\b", re.IGNORECASE | re.DOTALL),
        re.compile(r"\bnet\s+debt\s+leverage\b.{0,80}?(?P<num>\d+(?:\.\d+)?)\s*x\b", re.IGNORECASE | re.DOTALL),
        re.compile(r"\bnet\s+debt\b.{0,80}?\bEBITDA\b.{0,40}?(?P<num>\d+(?:\.\d+)?)\s*x\b", re.IGNORECASE | re.DOTALL),
        re.compile(r"\bnet\s+debt\b.{0,80}?/\s*\bEBITDA\b.{0,40}?(?P<num>\d+(?:\.\d+)?)\s*x\b", re.IGNORECASE | re.DOTALL),
    ]
    leverage = _find_first_number(t, lev_pats)

    # Buyback / dividend totals (£bn)
    buyback = None
    for m in re.finditer(r"(share\s+buyback|buyback|repurchase).{0,160}", t, flags=re.IGNORECASE | re.DOTALL):
        window = m.group(0)
        v = _parse_gbp_amount_to_bn(window)
        if v is not None:
            buyback = v
            break

    dividend = None
    for m in re.finditer(r"(dividend).{0,160}", t, flags=re.IGNORECASE | re.DOTALL):
        window = m.group(0)
        v = _parse_gbp_amount_to_bn(window)
        if v is not None:
            dividend = v
            break

    return {
        "ulvr_fcf_gbp_bn": fcf,
        "ulvr_cash_conversion_pct": cash_conv,
        "ulvr_net_debt_leverage_x": leverage,
        "ulvr_buyback_gbp_bn": buyback,
        "ulvr_dividend_gbp_bn": dividend,
    }


def _is_unilever_company_ref(company_ref: str) -> bool:
    # Keep simple and safe.
    s = str(company_ref or "").upper()
    return "ULVR" in s


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

    Master intelligence:
    - Load master variables from:
        backend/modules/aion_equities/master_intelligence/company_<TICKER>/<version>.variables.json
      where <version> defaults to "v1" (configurable via master_variables_version).
    - Variable persistence rules:
        * If OpenAI yields 0 variables AND master variables exist -> persist master variables (never persist empty).
        * If OpenAI yields variables AND merge_master_variables is enabled -> persist merged(master + openai),
          where master is the baseline and OpenAI can only fill missing fields or add genuinely new variables.
        * If OpenAI yields variables AND merge_master_variables is disabled -> persist OpenAI variables as-is.
        * If no master variables exist -> persist OpenAI variables if present; otherwise do not write variable_watch.

    Live monitoring hardening:
    - Enrich trigger entries with feed_id (machine routing key) using master variables.
      Matching is conservative: trigger.variable_name <-> master_var.name.

    Optional company-specific hardening:
    - Some companies may have additional extractor/backfill logic (e.g. stamping reported metrics into trigger maps).
      This MUST:
        * be strictly gated by company_ref checks,
        * never run for other companies,
        * never mutate global/shared state,
        * fail open (must not break intake).
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
        # reported metrics -> trigger map (company-specific hardening may use this)
        enable_reported_metric_backfill: bool = True,
        reported_metric_overwrite_existing: bool = False,
        # append-only history output root (defaults to runtime/equities if not provided)
        history_base_dir: Optional[str | Path] = None,
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
        # backend/modules/aion_equities/master_intelligence
        if master_intelligence_base_dir is None:
            self.master_intelligence_base_dir = Path(__file__).resolve().parent / "master_intelligence"
        else:
            self.master_intelligence_base_dir = Path(master_intelligence_base_dir)

        self.master_variables_version = str(master_variables_version or "v1").strip() or "v1"
        self.use_master_variables_fallback = bool(use_master_variables_fallback)
        self.merge_master_variables = bool(merge_master_variables)

        self.enable_reported_metric_backfill = bool(enable_reported_metric_backfill)
        self.reported_metric_overwrite_existing = bool(reported_metric_overwrite_existing)

        # History output root:
        # If not provided, we try to infer from the trigger map store base_dir so this works
        # with scripts that pass --base-dir .runtime/equities.
        inferred: Optional[Path] = None
        if history_base_dir:
            inferred = Path(history_base_dir)
        else:
            store = company_trigger_map_store
            base_dir = getattr(store, "base_dir", None) or getattr(store, "_base_dir", None)
            if base_dir:
                inferred = Path(str(base_dir))
        self.history_base_dir = inferred

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
        # backend/modules/aion_equities/master_intelligence/company_<TICKER>/<version>.variables.json
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

    def _history_dir(self) -> Path:
        """
        History always lives at the equities base dir (same root as company_trigger_maps/variable_watch/etc).

        Priority:
          1) explicit history_base_dir
          2) infer from store.base_dir but normalize if it accidentally points at ".../company_trigger_maps"
          3) fallback: ".runtime/equities"
        """
        if self.history_base_dir is not None:
            p = Path(self.history_base_dir)
        else:
            store = self.company_trigger_map_store
            base_dir = getattr(store, "base_dir", None) or getattr(store, "_base_dir", None)
            p = Path(str(base_dir)) if base_dir else Path(".runtime/equities")

        # normalize bad inference
        if p.name == "company_trigger_maps":
            p = p.parent

        return p

    def _append_jsonl(self, path: Path, obj: Dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(obj, ensure_ascii=False)
        with path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    def _read_last_jsonl(self, path: Path) -> Optional[Dict[str, Any]]:
        if not path.exists():
            return None
        try:
            with path.open("r", encoding="utf-8", errors="ignore") as f:
                lines = [ln.strip() for ln in f.readlines() if ln.strip()]
            if not lines:
                return None
            return json.loads(lines[-1])
        except Exception:
            return None

    def _extract_bqs_from_analysis(self, analysis_out: Dict[str, Any], mapped_objects: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Returns dict like:
          {"composite": 70.8, "components":[...], ...}
        Accepts:
          - dict already
          - plain number -> wraps into {"composite": <float>, "components": []}
        """
        def _wrap(v: Any) -> Optional[Dict[str, Any]]:
            if isinstance(v, dict):
                return deepcopy(v)
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                return {"composite": float(v), "components": []}
            return None

        norm = (analysis_out or {}).get("normalized_analysis") or {}
        ar = (analysis_out or {}).get("analysis_response") or {}
        mo = mapped_objects or {}

        for src in (norm, ar, mo):
            for k in ("bqs", "business_quality_score", "bqs_score", "business_quality_score_value"):
                out = _wrap(src.get(k))
                if out is not None:
                    return out
        return None

    def _extract_acs_predicted_from_analysis(self, analysis_out: Dict[str, Any], mapped_objects: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Returns dict like:
          {"fx_drag_pct": -5.85, "usg_dir": "...", "volume_dir": "..."}
        Accepts:
          - dict already
          - plain number -> wraps into {"acs": <float>}
        """
        def _wrap(v: Any) -> Optional[Dict[str, Any]]:
            if isinstance(v, dict):
                return deepcopy(v)
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                return {"acs": float(v)}
            return None

        norm = (analysis_out or {}).get("normalized_analysis") or {}
        ar = (analysis_out or {}).get("analysis_response") or {}
        mo = mapped_objects or {}

        for src in (norm, ar, mo):
            for k in ("acs_predicted", "predicted", "acs", "analytical_confidence_score", "acs_score"):
                out = _wrap(src.get(k))
                if out is not None:
                    return out
        return None

    def _append_bqs_history(
        self,
        *,
        company_ref: str,
        fiscal_period_ref: str,
        as_of: str,
        source_document_ref: str,
        analysis_out: Dict[str, Any],
        mapped_objects: Dict[str, Any],
    ) -> None:
        base = self._history_dir()
        folder = _company_folder_name(company_ref)   # e.g. "company_ULVR.L"
        path = base / "bqs_history" / f"{folder}.jsonl"

        bqs = self._extract_bqs_from_analysis(analysis_out, mapped_objects)

        # If missing from analysis, still log a placeholder row (so history exists)
        if not isinstance(bqs, dict):
            bqs = {
                "composite": None,
                "components": [],
                "notes": "missing_from_analysis",
            }

        prev = self._read_last_jsonl(path)
        prev_comp = _safe_float(((prev or {}).get("bqs") or {}).get("composite"))
        comp = _safe_float(bqs.get("composite"))

        delta = None
        trend = "N/A"
        if comp is not None and prev_comp is not None:
            delta = comp - prev_comp
            if delta > 0.25:
                trend = "improving"
            elif delta < -0.25:
                trend = "declining"
            else:
                trend = "stable"

        rec = {
            "schema_version": "aion.equities.bqs_history.v1",
            "company_ref": company_ref,
            "fiscal_period_ref": fiscal_period_ref,
            "as_of": as_of,
            "source_document_ref": source_document_ref,
            "bqs": bqs,
            "delta_vs_prev": delta,
            "trend": trend,
        }
        self._append_jsonl(path, rec)

    def _append_acs_predicted_log(
        self,
        *,
        company_ref: str,
        fiscal_period_ref: str,
        as_of: str,
        source_document_ref: str,
        analysis_out: Dict[str, Any],
        mapped_objects: Dict[str, Any],
    ) -> None:
        base = self._history_dir()
        folder = _company_folder_name(company_ref)   # e.g. "company_ULVR.L"
        path = base / "acs_history" / f"{folder}.jsonl"

        predicted = self._extract_acs_predicted_from_analysis(analysis_out, mapped_objects)

        # If missing from analysis, still log a placeholder row
        if not isinstance(predicted, dict):
            predicted = {
                "fx_drag_pct": None,
                "usg_dir": None,
                "volume_dir": None,
                "notes": "missing_from_analysis",
            }

        rec = {
            "schema_version": "aion.equities.acs_log.v1",
            "company_ref": company_ref,
            "fiscal_period_ref": fiscal_period_ref,
            "as_of": as_of,
            "source_document_ref": source_document_ref,
            "event_type": "predicted",
            "predicted": predicted,
            "actual": None,
            "accuracy": None,
            "acs_adjustment": "pending",
        }
        self._append_jsonl(path, rec)

    def _index_master_variables(self, *, master_vars: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        Two indices:
          - by feed_id (strong)
          - by name (for trigger_map variable_name matching)
          - by variable_id (fallback)
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
        """
        Build the persistence seed for VariableWatchStore.

        Contract:
          - MUST be a dict
          - MUST contain "variables" as a list of dicts
          - MUST contain "seed_source" as a string label
        """
        cleaned: List[Dict[str, Any]] = []
        for v in variables or []:
            if isinstance(v, dict):
                cleaned.append(deepcopy(v))
        return {
            "variables": cleaned,
            "seed_source": str(source or "").strip() or "unknown",
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
        Ensure each trigger entry has a machine routing key: feed_id.

        Matching policy (conservative):
          1) If trigger already has feed_id -> keep it.
          2) Else match by normalized variable name:
                trigger["variable_name"] or trigger["name"]
             to:
                master_var["name"]
             and set feed_id from master.

        Also sets:
          - data_source_id (alias) to feed_id if missing
        """
        entries: List[Dict[str, Any]] = []
        if isinstance(trigger_entries, list):
            for t in trigger_entries:
                if isinstance(t, dict):
                    entries.append(deepcopy(t))
        if not entries:
            return []

        for t in entries:
            # already routed
            if str(t.get("feed_id") or "").strip():
                t.setdefault("data_source_id", str(t.get("feed_id") or "").strip())
                continue

            vname_raw = t.get("variable_name") or t.get("name")
            vname = _normalize_key(vname_raw)
            if not vname:
                continue

            mv = master_index.get(f"name:{vname}")
            if not isinstance(mv, dict):
                continue

            fid = str(mv.get("feed_id") or "").strip()
            if not fid:
                continue

            t["feed_id"] = fid
            t.setdefault("data_source_id", fid)

        return entries

    def _is_garbage_trigger_map(self, entries: List[Dict[str, Any]]) -> bool:
        """
        Detect placeholder/low-signal trigger maps that should be rebuilt from master variables.

        Heuristic (fail-safe):
          - empty entries -> garbage
          - too few feed_ids -> garbage
          - too few non-zero impact_weight -> garbage
        """
        if not entries:
            return True

        n = len(entries)

        feed_ids = 0
        nonzero_w = 0
        for t in entries:
            if not isinstance(t, dict):
                continue
            if str(t.get("feed_id") or "").strip():
                feed_ids += 1
            w = _safe_float(t.get("impact_weight"))
            if w is not None and float(w) > 0:
                nonzero_w += 1

        # require at least ~1/3 entries to be routable + weighted (min 2)
        return (feed_ids < max(2, n // 3)) or (nonzero_w < max(2, n // 3))

    def _build_trigger_entries_from_master(
        self,
        *,
        company_ref: str,
        fiscal_period_ref: str,
        master_vars: List[Dict[str, Any]],
        existing_entries: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Build a trigger_entries list from master variables.

        HARD RULE (UI/tick contract):
          Every trigger entry MUST include:
            trigger_id, feed_id, variable_name, category, data_source,
            current_state, threshold_rule, lag_expectation,
            impact_direction, impact_weight, confidence, thesis_action,
            latest_value, last_updated_at

        Preserve (by feed_id) from existing_entries when present:
          latest_value, current_state, confidence, last_updated_at, threshold_rule, lag_expectation, thesis_action
        """
        existing_entries = existing_entries or []
        by_fid: Dict[str, Dict[str, Any]] = {
            str(t.get("feed_id") or "").strip(): t
            for t in existing_entries
            if isinstance(t, dict) and str(t.get("feed_id") or "").strip()
        }

        def _norm_dir(d: Any) -> str:
            s = str(d or "").strip().lower()
            if s in {"neg", "negative", "-", "down", "inverse", "inv"}:
                return "neg"
            if s in {"pos", "positive", "+", "up"}:
                return "pos"
            return "pos"

        def _derive_threshold_rule(v: Dict[str, Any], impact_direction: str) -> str:
            # prefer explicit rule if present
            rule = str(v.get("threshold_rule") or v.get("rule") or "").strip()
            if rule:
                return rule

            # otherwise try to derive from threshold_confirm if numeric-ish
            tc = v.get("threshold_confirm")
            fv = _safe_float(tc)
            if fv is None:
                return ""
            return f"cross_below:{fv}" if impact_direction == "neg" else f"cross_above:{fv}"

        out: List[Dict[str, Any]] = []

        for v in master_vars or []:
            if not isinstance(v, dict):
                continue

            fid = str(v.get("feed_id") or "").strip()
            if not fid:
                continue

            prev = by_fid.get(fid, {}) if isinstance(by_fid.get(fid), dict) else {}

            impact_direction = _norm_dir(v.get("direction") or prev.get("impact_direction"))

            variable_name = str(v.get("name") or prev.get("variable_name") or fid).strip() or fid
            category = str(v.get("category") or prev.get("category") or "unknown").strip() or "unknown"
            data_source = str(v.get("data_source") or prev.get("data_source") or "").strip()

            impact_weight = _safe_float(v.get("impact_weight"))
            if impact_weight is None:
                impact_weight = _safe_float(prev.get("impact_weight"))
            if impact_weight is None:
                impact_weight = 0.10

            latest_value = prev.get("latest_value", None)
            current_state = str(prev.get("current_state") or "inactive").strip() or "inactive"

            confidence = _safe_float(prev.get("confidence"))
            if confidence is None:
                confidence = 0.0

            threshold_rule = str(prev.get("threshold_rule") or "").strip()
            if not threshold_rule:
                threshold_rule = _derive_threshold_rule(v, impact_direction)

            lag_expectation = str(prev.get("lag_expectation") or v.get("lag_expectation") or "").strip()

            thesis_action = str(
                prev.get("thesis_action")
                or v.get("thesis_action")
                or v.get("thesis_action_on_confirm")
                or ""
            ).strip()

            last_updated_at = prev.get("last_updated_at", None)

            out.append(
                {
                    "trigger_id": f"{company_ref}/trigger/{fiscal_period_ref}/{fid}",
                    "feed_id": fid,
                    "variable_name": variable_name,
                    "category": category,
                    "data_source": data_source,
                    "current_state": current_state,
                    "threshold_rule": threshold_rule,
                    "lag_expectation": lag_expectation,
                    "impact_direction": impact_direction,
                    "impact_weight": float(impact_weight),
                    "confidence": float(confidence),
                    "thesis_action": thesis_action,
                    "latest_value": latest_value,
                    "last_updated_at": last_updated_at,
                }
            )

        return out

    def _load_trigger_map_payload_any(
        self,
        *,
        company_ref: str,
        fiscal_period_ref: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Compatibility loader:
          1) store.load_trigger_map(company_ref=..., fiscal_period_ref=...)
          2) store.load_company_trigger_map(company_ref=..., fiscal_period_ref=...)
          3) direct read from runtime path if store exposes base_dir

        HARDEN:
          - store.base_dir may already be ".../company_trigger_maps" (CompanyTriggerMapStore does this)
            so don't double-append the folder.
        """
        store = self.company_trigger_map_store
        if store is None:
            return None

        for fn_name in ("load_trigger_map", "load_company_trigger_map"):
            fn = getattr(store, fn_name, None)
            if callable(fn):
                try:
                    payload = fn(company_ref=company_ref, fiscal_period_ref=fiscal_period_ref)
                    if isinstance(payload, dict):
                        return payload
                except Exception:
                    pass

        base_dir = getattr(store, "base_dir", None) or getattr(store, "_base_dir", None)
        if not base_dir:
            return None

        base = Path(str(base_dir))
        if base.name != "company_trigger_maps":
            base = base / "company_trigger_maps"

        p = base / _company_folder_name(company_ref) / f"{fiscal_period_ref}.json"
        if not p.exists():
            return None

        obj = _safe_read_json(p)
        return obj if isinstance(obj, dict) else None

    def _save_trigger_map_payload_any(self, payload: Dict[str, Any]) -> bool:
        """
        Compatibility saver:
          1) store.save_trigger_map_payload(payload, validate=...)
          2) direct write to runtime path if store exposes base_dir and payload has company_ref+fiscal_period_ref

        HARDEN:
          - store.base_dir may already be ".../company_trigger_maps" (CompanyTriggerMapStore does this)
            so don't double-append the folder.
          - atomic write (tmp + replace)
        """
        store = self.company_trigger_map_store
        if store is None:
            return False

        fn = getattr(store, "save_trigger_map_payload", None)
        if callable(fn):
            try:
                fn(payload, validate=False)
                return True
            except Exception:
                pass

        base_dir = getattr(store, "base_dir", None) or getattr(store, "_base_dir", None)
        company_ref = str(payload.get("company_ref") or "").strip()
        fiscal_period_ref = str(payload.get("fiscal_period_ref") or "").strip()
        if not (base_dir and company_ref and fiscal_period_ref):
            return False

        base = Path(str(base_dir))
        if base.name != "company_trigger_maps":
            base = base / "company_trigger_maps"

        p = base / _company_folder_name(company_ref) / f"{fiscal_period_ref}.json"

        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            data = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
            tmp = p.with_suffix(p.suffix + ".tmp")
            tmp.write_text(data, encoding="utf-8")
            tmp.replace(p)
            return True
        except Exception:
            return False

    def _backfill_reported_metrics_into_trigger_map(
        self,
        *,
        company_ref: str,
        fiscal_period_ref: str,
        trigger_map_id: Optional[str],
        resolved_document_text: str,
        persisted_objects: Dict[str, Any],
        generated_by: str,
        master_index: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> None:
        """
        Optional company-specific hook.

        Rules:
          - MUST be gated by company_ref checks.
          - MUST fail-open (never breaks intake).
          - MUST NOT affect other companies.

        Current implementation: ULVR-only backfill (kept isolated by _is_unilever_company_ref()).
        """
        if self.company_trigger_map_store is None:
            return
        if not self.enable_reported_metric_backfill:
            return
        if not trigger_map_id:
            return
        if not resolved_document_text or not resolved_document_text.strip():
            return
        if not _is_unilever_company_ref(company_ref):
            return

        metrics: Dict[str, Optional[float]] = {}
        metrics.update(_extract_unilever_reported_metrics(resolved_document_text) or {})
        metrics.update(_extract_unilever_financial_metrics(resolved_document_text) or {})

        wanted = {
            "ulvr_group_usg",
            "ulvr_group_uvg",
            "ulvr_uom",
            "ulvr_productivity_savings",
            "ulvr_fcf_gbp_bn",
            "ulvr_cash_conversion_pct",
            "ulvr_net_debt_leverage_x",
            "ulvr_buyback_gbp_bn",
            "ulvr_dividend_gbp_bn",
        }

        found: Dict[str, float] = {}
        for k, v in (metrics or {}).items():
            if k in wanted:
                fv = _safe_float(v)
                if fv is not None:
                    found[k] = float(fv)

        persisted_objects["reported_metrics_extracted"] = deepcopy(metrics)
        persisted_objects["reported_metrics_found"] = deepcopy(found)

        if not found:
            persisted_objects["reported_metrics_applied"] = 0
            persisted_objects["reported_metrics_reason"] = "no_extractable_values_found"
            return

        payload = self._load_trigger_map_payload_any(company_ref=company_ref, fiscal_period_ref=fiscal_period_ref)
        if not isinstance(payload, dict):
            persisted_objects["reported_metrics_applied"] = 0
            persisted_objects["reported_metrics_reason"] = "trigger_map_load_failed"
            return

        triggers_any = payload.get("trigger_entries")
        if not isinstance(triggers_any, list):
            triggers_any = payload.get("triggers")
        if not isinstance(triggers_any, list):
            triggers_any = []

        triggers: List[Dict[str, Any]] = [deepcopy(t) for t in triggers_any if isinstance(t, dict)]
        by_fid: Dict[str, Dict[str, Any]] = {
            str(t.get("feed_id") or "").strip(): t
            for t in triggers
            if str(t.get("feed_id") or "").strip()
        }

        applied = 0
        skipped_existing = 0
        created_missing = 0

        for feed_id, value in found.items():
            t = by_fid.get(feed_id)

            if t is None:
                mv = (master_index or {}).get(f"feed_id:{feed_id}") if master_index else None
                direction = str((mv or {}).get("direction") or "").strip().lower()
                impact_direction = "pos" if direction in {"positive", "pos", "+", "up"} else "neg"

                t = {
                    "trigger_id": f"{company_ref}/trigger/{fiscal_period_ref}/{feed_id}",
                    "feed_id": feed_id,
                    "variable_name": (mv or {}).get("name") or feed_id,
                    "category": (mv or {}).get("category") or "company_reported",
                    "data_source": "board_pack_extract",
                    "impact_direction": impact_direction,
                    "impact_weight": float(_safe_float((mv or {}).get("impact_weight")) or 0.10),
                    "current_state": "inactive",
                    "threshold_rule": "",
                    "lag_expectation": "",
                    "confidence": 1.0,
                    "thesis_action": str((mv or {}).get("thesis_action_on_confirm") or ""),
                    "latest_value": None,
                    "last_updated_at": None,
                }
                triggers.append(t)
                by_fid[feed_id] = t
                created_missing += 1

            prev = t.get("latest_value", None)
            if prev is not None and not self.reported_metric_overwrite_existing:
                skipped_existing += 1
                continue

            t["latest_value"] = float(value)
            t["current_state"] = "confirmed"

            try:
                from datetime import datetime, timezone

                t["last_updated_at"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
            except Exception:
                pass

            applied += 1

        payload["trigger_entries"] = triggers
        payload.pop("triggers", None)

        ok = self._save_trigger_map_payload_any(payload)
        if ok:
            persisted_objects["reported_metrics_applied"] = applied
            persisted_objects["reported_metrics_skipped_existing"] = skipped_existing
            persisted_objects["reported_metrics_created_missing"] = created_missing
            persisted_objects["reported_metrics_trigger_map_ref"] = trigger_map_id
        else:
            persisted_objects["reported_metrics_applied"] = 0
            persisted_objects["reported_metrics_reason"] = "trigger_map_save_failed"

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
        QuarterEventStore requires fiscal_period to exist and be parseable (YYYY-Q#).
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

    def _load_saved_trigger_entries(self, *, company_ref: str, fiscal_period_ref: str) -> List[Dict[str, Any]]:
        payload = self._load_trigger_map_payload_any(company_ref=company_ref, fiscal_period_ref=fiscal_period_ref)
        if not isinstance(payload, dict):
            return []

        entries = payload.get("trigger_entries")
        if not isinstance(entries, list):
            entries = payload.get("triggers")
        if not isinstance(entries, list):
            return []

        return [deepcopy(t) for t in entries if isinstance(t, dict)]

    def _build_bqs_from_trigger_map(self, *, company_ref: str, fiscal_period_ref: str) -> Dict[str, Any]:
        """
        Generic, deterministic BQS seed from trigger_map (no OpenAI dependency).

        Goal:
          - Produce stable, non-null BQS output for ANY company as soon as a trigger map exists.
          - Evidence is derived from generic trigger fields (coverage, confidence, states, weights).

        Output shape:
          {"composite": <0-100 float>, "components":[{key,label,score,evidence},...], "notes": "..."}
        """
        entries = self._load_saved_trigger_entries(company_ref=company_ref, fiscal_period_ref=fiscal_period_ref)
        if not entries:
            return {
                "composite": 0.0,
                "components": [
                    {"key": "data_coverage", "label": "Data coverage", "score": 0, "evidence": "No trigger entries"},
                ],
                "notes": "computed_from_trigger_map",
            }

        n = len(entries)

        with_value = 0
        with_feed = 0
        confirmed = 0
        broken = 0
        active = 0
        conf_sum = 0.0
        conf_n = 0
        w_sum = 0.0
        w_nonzero = 0

        for t in entries:
            if not isinstance(t, dict):
                continue
            if str(t.get("feed_id") or "").strip():
                with_feed += 1
            if t.get("latest_value", None) is not None:
                with_value += 1

            st = str(t.get("current_state") or "").strip().lower()
            if st == "confirmed":
                confirmed += 1
            elif st == "broken":
                broken += 1
            elif st in {"early_watch", "building", "active"}:
                active += 1

            c = _safe_float(t.get("confidence"))
            if c is not None:
                conf_sum += float(c)
                conf_n += 1

            w = _safe_float(t.get("impact_weight"))
            if w is not None:
                w_sum += float(w)
                if float(w) > 0:
                    w_nonzero += 1

        coverage = with_value / max(1, n)
        routable = with_feed / max(1, n)
        avg_conf = (conf_sum / conf_n) if conf_n else 0.0

        def score_0_10(x: float) -> int:
            # clamp to [0,10]
            try:
                return max(0, min(10, int(round(x))))
            except Exception:
                return 0

        # Components (generic)
        data_cov_score = score_0_10(coverage * 10.0)
        routing_score = score_0_10(routable * 10.0)
        signal_score = score_0_10(avg_conf * 10.0)
        state_score = score_0_10(((confirmed + active) / max(1, n)) * 10.0)
        risk_score = score_0_10((1.0 - (broken / max(1, n))) * 10.0)
        weight_score = score_0_10((w_nonzero / max(1, n)) * 10.0)

        # “Stability” proxy: if coverage exists and broken is low, we call it stable
        stability_score = score_0_10(min(1.0, coverage * 0.7 + (1.0 - broken / max(1, n)) * 0.3) * 10.0)

        components = [
            {
                "key": "data_coverage",
                "label": "Data coverage",
                "score": data_cov_score,
                "evidence": f"{with_value}/{n} triggers have latest_value",
            },
            {
                "key": "routing_integrity",
                "label": "Routing integrity",
                "score": routing_score,
                "evidence": f"{with_feed}/{n} triggers have feed_id",
            },
            {
                "key": "signal_confidence",
                "label": "Signal confidence",
                "score": signal_score,
                "evidence": f"avg confidence {avg_conf:.2f} across {conf_n}/{n} triggers",
            },
            {
                "key": "state_activity",
                "label": "State activity",
                "score": state_score,
                "evidence": f"confirmed={confirmed}, active={active}, inactive={n - confirmed - broken - active}, broken={broken}",
            },
            {
                "key": "risk_flags",
                "label": "Risk flags",
                "score": risk_score,
                "evidence": f"broken={broken}/{n}",
            },
            {
                "key": "weight_quality",
                "label": "Weight quality",
                "score": weight_score,
                "evidence": f"nonzero impact_weight={w_nonzero}/{n}, sum≈{w_sum:.2f}",
            },
            {
                "key": "stability",
                "label": "Stability",
                "score": stability_score,
                "evidence": "coverage + low broken rate",
            },
        ]

        total = sum(int(c["score"]) for c in components)
        composite = round((total / 70.0) * 100.0, 2)

        return {
            "composite": composite,
            "components": components,
            "notes": "computed_from_trigger_map",
        }

    def _build_acs_predicted_from_trigger_map(self, *, company_ref: str, fiscal_period_ref: str) -> Dict[str, Any]:
        """
        Generic, deterministic ACS "predicted" payload for calibration history.

        Goal:
          - Produce stable, non-null ACS output for ANY company as soon as a trigger map exists.
          - Do NOT rely on company-specific feed_ids (no ULVR coupling).
          - Use only generic trigger fields: latest_value, current_state, confidence.

        Output shape (kept compatible with existing logs):
          {
            "fx_drag_pct": <float|None>,   # reserved; generic runtime doesn't infer FX
            "usg_dir": <"pos"|"neg"|"flat"|None>,     # generic direction proxy (signal)
            "volume_dir": <"pos"|"neg"|"flat"|None>,  # generic direction proxy (activity)
            "notes": "computed_from_trigger_map"
          }
        """
        entries = self._load_saved_trigger_entries(company_ref=company_ref, fiscal_period_ref=fiscal_period_ref)
        if not entries:
            return {
                "fx_drag_pct": None,
                "usg_dir": None,
                "volume_dir": None,
                "notes": "computed_from_trigger_map",
            }

        n = len(entries)

        confirmed = 0
        broken = 0
        active = 0
        with_value = 0

        conf_sum = 0.0
        conf_n = 0

        for t in entries:
            if not isinstance(t, dict):
                continue

            if t.get("latest_value", None) is not None:
                with_value += 1

            st = str(t.get("current_state") or "").strip().lower()
            if st == "confirmed":
                confirmed += 1
            elif st == "broken":
                broken += 1
            elif st in {"early_watch", "building", "active"}:
                active += 1

            c = _safe_float(t.get("confidence"))
            if c is not None:
                conf_sum += float(c)
                conf_n += 1

        coverage = with_value / max(1, n)
        avg_conf = (conf_sum / conf_n) if conf_n else 0.0

        # Generic "signal direction" proxies:
        # - usg_dir: net signal balance (confirmed+active vs broken) weighted by confidence
        # - volume_dir: data coverage proxy (whether we have enough values to be actionable)
        net = (confirmed + active) - broken
        net_norm = net / max(1, n)  # [-1, +1] roughly

        # confidence-adjusted net
        net_adj = net_norm * (0.5 + 0.5 * max(0.0, min(1.0, avg_conf)))

        def dir_from(x: float) -> str:
            # Conservative bands to avoid flip-flopping
            if x > 0.15:
                return "pos"
            if x < -0.15:
                return "neg"
            return "flat"

        usg_dir = dir_from(net_adj)
        volume_dir = dir_from(coverage - 0.5)  # above 50% coverage => "pos", below => "neg"

        return {
            "fx_drag_pct": None,
            "usg_dir": usg_dir,
            "volume_dir": volume_dir,
            "notes": "computed_from_trigger_map",
        }

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

        period_fallback = str(fiscal_period_ref or "").strip() or "unknown"

        master_vars = self._load_master_variables(company_ref=company_ref)
        master_index = self._index_master_variables(master_vars=master_vars)

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
        # Trigger map persistence
        # -----------------------
        saved_trigger_map: Optional[Dict[str, Any]] = None
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

                    if master_vars and self._is_garbage_trigger_map(enriched):
                        enriched = self._build_trigger_entries_from_master(
                            company_ref=company_ref,
                            fiscal_period_ref=str(fiscal_period),
                            master_vars=master_vars,
                            existing_entries=enriched,
                        )
                        persisted_objects["trigger_map_rebuilt_from_master"] = True
                    else:
                        persisted_objects["trigger_map_rebuilt_from_master"] = False

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
                    persisted_objects["trigger_map_fiscal_period_ref"] = str(fiscal_period)

        # -----------------------
        # Backfill reported metrics
        # -----------------------
        if (
            persist_trigger_map
            and self.company_trigger_map_store is not None
            and saved_trigger_map is not None
            and self.enable_reported_metric_backfill
        ):
            fiscal_period_for_backfill = str(
                _coalesce(
                    persisted_objects.get("trigger_map_fiscal_period_ref"),
                    trigger_map_fiscal_period_ref,
                    period_fallback,
                    default=period_fallback,
                )
            )
            self._backfill_reported_metrics_into_trigger_map(
                company_ref=company_ref,
                fiscal_period_ref=fiscal_period_for_backfill,
                trigger_map_id=str(persisted_objects.get("trigger_map_ref") or ""),
                resolved_document_text=resolved_document_text,
                persisted_objects=persisted_objects,
                generated_by=generated_by,
                master_index=master_index,
            )

        # -----------------------
        # Variable watch persistence
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
        # Assessment
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
        # Thesis
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
                            assessment_refs=list((thesis_payload.get("linked_refs") or {}).get("assessment_refs") or []),
                            status=thesis_payload.get("status", "candidate"),
                            generated_by=generated_by,
                            create_write_event=True,
                            validate=False,
                        )

                persisted_objects["thesis"] = deepcopy(thesis_payload)
                persisted_objects["thesis_ref"] = thesis_payload.get("thesis_id")

        # -----------------------
        # Reference maintenance
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

        # -----------------------
        # Ensure BQS/ACS exist for history logging (computed from saved trigger map)
        # -----------------------
        try:
            fp_for_scores = str(
                _coalesce(
                    persisted_objects.get("trigger_map_fiscal_period_ref"),
                    trigger_map_fiscal_period_ref,
                    fiscal_period_ref,
                    period_fallback,
                    default=period_fallback,
                )
            ).strip() or str(period_fallback)

            # ONLY compute if trigger map exists (we need saved entries on disk)
            if persist_trigger_map and self.company_trigger_map_store is not None:
                ar = analysis_out.setdefault("analysis_response", {})
                na = analysis_out.setdefault("normalized_analysis", {})

                if "bqs" not in ar and "business_quality_score" not in ar:
                    ar["bqs"] = self._build_bqs_from_trigger_map(
                        company_ref=company_ref,
                        fiscal_period_ref=fp_for_scores,
                    )
                if "bqs" not in na and "business_quality_score" not in na:
                    na["bqs"] = deepcopy(ar.get("bqs"))

                if "acs_predicted" not in ar and "acs" not in ar and "analytical_confidence_score" not in ar:
                    ar["acs_predicted"] = self._build_acs_predicted_from_trigger_map(
                        company_ref=company_ref,
                        fiscal_period_ref=fp_for_scores,
                    )
                if "acs_predicted" not in na and "acs" not in na and "analytical_confidence_score" not in na:
                    na["acs_predicted"] = deepcopy(ar.get("acs_predicted"))
        except Exception:
            # never break intake for scoring
            pass

        # -----------------------
        # BQS/ACS history (append-only)
        # -----------------------
        persisted_objects["history_write_ok"] = False  # default (visible in debug JSON)

        # precompute these so they exist even if the try fails
        fp = str(
            _coalesce(
                persisted_objects.get("trigger_map_fiscal_period_ref"),
                trigger_map_fiscal_period_ref,
                fiscal_period_ref,
                period_fallback,
                default=period_fallback,
            )
        ).strip() or str(period_fallback)

        src_doc = str(
            _coalesce(
                persisted_objects.get("source_document_id"),
                (persisted_objects.get("quarter_event") or {}).get("source_document_ref"),
                document_ref,
                default=document_ref,
            )
        )

        try:
            from datetime import datetime, timezone
            as_of = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

            base = self._history_dir()
            persisted_objects["history_base_dir"] = str(base)

            # ✅ MUST match writer funcs (they use _company_folder_name)
            folder = _company_folder_name(company_ref)  # e.g. "company_ULVR.L"
            bqs_path = base / "bqs_history" / f"{folder}.jsonl"
            acs_path = base / "acs_history" / f"{folder}.jsonl"

            persisted_objects["bqs_history_path"] = str(bqs_path)
            persisted_objects["acs_history_path"] = str(acs_path)

            # write rows
            self._append_bqs_history(
                company_ref=str(company_ref),
                fiscal_period_ref=fp,
                as_of=as_of,
                source_document_ref=src_doc,
                analysis_out=analysis_out,
                mapped_objects=mapped_objects,
            )

            self._append_acs_predicted_log(
                company_ref=str(company_ref),
                fiscal_period_ref=fp,
                as_of=as_of,
                source_document_ref=src_doc,
                analysis_out=analysis_out,
                mapped_objects=mapped_objects,
            )

            persisted_objects["history_write_ok"] = True

        except Exception as e:
            # never break intake for history logging
            persisted_objects["history_write_error"] = repr(e)

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