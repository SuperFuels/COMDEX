from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.modules.aion_equities.constants import SCHEMA_PACK_VERSION
from backend.modules.aion_equities.investing_ids import make_company_id, make_quarter_event_id
from backend.modules.aion_equities.schema_validate import validate_payload


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _iso_z(value: Any) -> str:
    if isinstance(value, datetime):
        dt = value
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if isinstance(value, str):
        return value
    raise ValueError(f"Unsupported datetime value: {value!r}")


def _date_str(value: Any) -> str:
    if isinstance(value, datetime):
        dt = value
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%d")
    if isinstance(value, str):
        return value
    raise ValueError(f"Unsupported date value: {value!r}")


def _safe_segment(value: str) -> str:
    return str(value).replace("/", "_").replace("\\", "_").replace(":", "-").strip()


def _default_storage_dir() -> Path:
    return Path(__file__).resolve().parent / "data" / "quarter_events"


def _deep_merge(base: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any]:
    out = deepcopy(base)
    for k, v in patch.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = deepcopy(v)
    return out


def quarter_event_storage_path(
    quarter_event_id: str,
    *,
    base_dir: Optional[Path] = None,
) -> Path:
    root = Path(base_dir) if base_dir is not None else _default_storage_dir()
    return root / f"{_safe_segment(quarter_event_id)}.json"


def build_quarter_event_payload(
    *,
    ticker: str,
    fiscal_year: int,
    fiscal_quarter: int,
    as_reported_date: Any,
    document_refs: List[str],
    source_hashes: List[str],
    created_by: str = "aion_equities.quarter_event_store",
    event_type: str = "quarterly_results",
    provider: Optional[str] = None,
    period_start: Optional[Any] = None,
    period_end: Optional[Any] = None,
    earnings_call_date: Optional[Any] = None,
    financials: Optional[Dict[str, Any]] = None,
    narrative_summary: str = "",
    guidance_text_excerpt_refs: Optional[List[str]] = None,
    management_claim_refs: Optional[List[str]] = None,
    ast_applied: bool = False,
    ast_result_ref: Optional[str] = None,
    deltas_vs_prior: Optional[Dict[str, Any]] = None,
    flags: Optional[List[str]] = None,
    assessment_refs: Optional[List[str]] = None,
    pattern_match_refs: Optional[List[str]] = None,
    sqi_trace_refs: Optional[List[str]] = None,
    updated_by: Optional[str] = None,
    created_at: Optional[Any] = None,
    updated_at: Optional[Any] = None,
    validate: bool = True,
) -> Dict[str, Any]:
    created_at_s = _iso_z(created_at) if created_at is not None else _utc_now_iso()
    updated_at_s = _iso_z(updated_at) if updated_at is not None else created_at_s

    quarter_event_id = make_quarter_event_id(ticker, fiscal_year, fiscal_quarter)
    company_ref = make_company_id(ticker)

    period: Dict[str, Any] = {
        "fiscal_year": int(fiscal_year),
        "fiscal_quarter": int(fiscal_quarter),
    }
    if period_start is not None:
        period["period_start"] = _date_str(period_start)
    if period_end is not None:
        period["period_end"] = _date_str(period_end)

    source: Dict[str, Any] = {
        "document_refs": list(document_refs),
        "source_hashes": list(source_hashes),
    }
    if provider:
        source["provider"] = provider

    narrative: Dict[str, Any] = {
        "summary": narrative_summary or "",
    }
    if guidance_text_excerpt_refs is not None:
        narrative["guidance_text_excerpt_refs"] = list(guidance_text_excerpt_refs)
    if management_claim_refs is not None:
        narrative["management_claim_refs"] = list(management_claim_refs)
    narrative["ast_applied"] = bool(ast_applied)
    if ast_result_ref:
        narrative["ast_result_ref"] = ast_result_ref

    extraction: Dict[str, Any] = {
        "financials": dict(financials or {}),
        "narrative": narrative,
    }

    analysis: Dict[str, Any] = {
        "deltas_vs_prior": dict(deltas_vs_prior or {}),
        "flags": list(flags or []),
        "assessment_refs": list(assessment_refs or []),
    }
    if pattern_match_refs is not None:
        analysis["pattern_match_refs"] = list(pattern_match_refs)
    if sqi_trace_refs is not None:
        analysis["sqi_trace_refs"] = list(sqi_trace_refs)

    payload: Dict[str, Any] = {
        "quarter_event_id": quarter_event_id,
        "company_ref": company_ref,
        "period": period,
        "event_type": event_type,
        "as_reported_date": _date_str(as_reported_date),
        "source": source,
        "extraction": extraction,
        "analysis": analysis,
        "audit": {
            "created_at": created_at_s,
            "updated_at": updated_at_s,
            "created_by": created_by,
        },
    }

    if earnings_call_date is not None:
        payload["earnings_call_date"] = _date_str(earnings_call_date)

    if updated_by:
        payload["audit"]["updated_by"] = updated_by

    if validate:
        validate_payload("quarter_event", payload, version=SCHEMA_PACK_VERSION)

    return payload


def save_quarter_event_payload(
    payload: Dict[str, Any],
    *,
    base_dir: Optional[Path] = None,
    validate: bool = True,
) -> Path:
    if validate:
        validate_payload("quarter_event", payload, version=SCHEMA_PACK_VERSION)

    path = quarter_event_storage_path(payload["quarter_event_id"], base_dir=base_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_quarter_event_payload(
    quarter_event_id: str,
    *,
    base_dir: Optional[Path] = None,
    validate: bool = True,
) -> Dict[str, Any]:
    path = quarter_event_storage_path(quarter_event_id, base_dir=base_dir)
    if not path.exists():
        raise FileNotFoundError(f"Quarter event payload not found: {path}")

    payload = json.loads(path.read_text(encoding="utf-8"))
    if validate:
        validate_payload("quarter_event", payload, version=SCHEMA_PACK_VERSION)
    return payload


class QuarterEventStore:
    def __init__(self, base_dir: str | Path):
        self.base_dir = Path(base_dir)
        self.events_dir = self.base_dir / "quarter_events"
        self.events_dir.mkdir(parents=True, exist_ok=True)

    def storage_path(self, quarter_event_id: str) -> Path:
        return quarter_event_storage_path(quarter_event_id, base_dir=self.events_dir)

    def save_quarter_event(
        self,
        *,
        ticker: str,
        fiscal_year: Optional[int] = None,
        fiscal_quarter: Optional[int] = None,
        as_reported_date: Optional[Any] = None,
        document_refs: Optional[List[str]] = None,
        source_hashes: Optional[List[str]] = None,
        created_by: str = "aion_equities.quarter_event_store",
        quarter_event_payload_patch: Optional[Dict[str, Any]] = None,
        validate: bool = True,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        # Legacy aliases from older tests/runtime
        if fiscal_year is None:
            fiscal_year = kwargs.pop("year", None)
        if fiscal_quarter is None:
            fiscal_quarter = kwargs.pop("quarter", None)
        if as_reported_date is None:
            as_reported_date = kwargs.pop("filing_date", None)

        period_end = kwargs.pop("period_end_date", None)
        period_start = kwargs.pop("period_start_date", None)

        if document_refs is None:
            document_refs = kwargs.pop("source_document_refs", None)
        if source_hashes is None:
            source_hashes = kwargs.pop("source_hashes", None)

        filing_kind = kwargs.pop("filing_kind", None)
        if filing_kind and "event_type" not in kwargs:
            mapping = {
                "quarterly_results": "quarterly_results",
                "interim_report": "interim_report",
                "annual_report_snapshot": "annual_report_snapshot",
                "trading_update": "trading_update",
            }
            kwargs["event_type"] = mapping.get(filing_kind, "quarterly_results")

        # legacy / extra args from tests or older callers
        kwargs.pop("company_ref", None)
        kwargs.pop("quarter_event_id", None)

        assessment_ref = kwargs.pop("assessment_ref", None)
        assessment_refs = kwargs.pop("assessment_refs", None)
        if assessment_refs is None:
            assessment_refs = [assessment_ref] if assessment_ref else []

        extracted_table_refs = kwargs.pop("extracted_table_refs", None)
        narrative_ref = kwargs.pop("narrative_ref", None)

        if "financials" not in kwargs:
            kwargs["financials"] = {}

        if extracted_table_refs and "pattern_match_refs" not in kwargs:
            kwargs["pattern_match_refs"] = list(extracted_table_refs)

        if "narrative_summary" not in kwargs:
            kwargs["narrative_summary"] = ""

        if narrative_ref and "management_claim_refs" not in kwargs:
            kwargs["management_claim_refs"] = [narrative_ref]

        if period_start is not None:
            kwargs["period_start"] = period_start
        if period_end is not None:
            kwargs["period_end"] = period_end

        kwargs["assessment_refs"] = assessment_refs

        if fiscal_year is None or fiscal_quarter is None or as_reported_date is None:
            raise TypeError(
                "save_quarter_event() requires fiscal_year/fiscal_quarter/as_reported_date "
                "(legacy aliases year/quarter/filing_date are also accepted)"
            )

        # be permissive for bootstrap tests
        if not document_refs:
            document_refs = ["document:unknown"]

        if source_hashes is None or len(source_hashes) == 0:
            source_hashes = ["sha256:unknown"]

        payload = build_quarter_event_payload(
            ticker=ticker,
            fiscal_year=int(fiscal_year),
            fiscal_quarter=int(fiscal_quarter),
            as_reported_date=as_reported_date,
            document_refs=list(document_refs),
            source_hashes=list(source_hashes),
            created_by=created_by,
            validate=False,
            **kwargs,
        )

        if quarter_event_payload_patch:
            payload = _deep_merge(payload, quarter_event_payload_patch)

        if validate:
            validate_payload("quarter_event", payload, version=SCHEMA_PACK_VERSION)

        save_quarter_event_payload(payload, base_dir=self.events_dir, validate=False)
        return payload

    def load_quarter_event(self, quarter_event_id: str, *, validate: bool = True) -> Dict[str, Any]:
        return load_quarter_event_payload(quarter_event_id, base_dir=self.events_dir, validate=validate)

    def quarter_event_exists(self, quarter_event_id: str) -> bool:
        return self.storage_path(quarter_event_id).exists()

    def list_quarter_events(self, company_ref: str) -> List[str]:
        if not self.events_dir.exists():
            return []

        out: List[str] = []
        for path in sorted(self.events_dir.glob("*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            if payload.get("company_ref") == company_ref:
                qid = payload.get("quarter_event_id")
                if isinstance(qid, str):
                    out.append(qid)
        return out