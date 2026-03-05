from __future__ import annotations

import json
import re
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from backend.modules.aion_equities.constants import SCHEMA_PACK_VERSION
from backend.modules.aion_equities.investing_ids import make_company_id, make_quarter_event_id
from backend.modules.aion_equities.schema_validate import validate_payload


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _utc_today_date() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


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


def _parse_fiscal_period(value: Any) -> Tuple[int, int]:
    if isinstance(value, dict):
        fy = value.get("fiscal_year")
        fq = value.get("fiscal_quarter")
        if fy is not None and fq is not None:
            return int(fy), int(fq)

    s = str(value or "").strip()
    m = re.search(r"(\d{4})\s*[-_/]?\s*Q\s*([1-4])", s, flags=re.IGNORECASE)
    if not m:
        m = re.search(r"(\d{4})\s*Q\s*([1-4])", s, flags=re.IGNORECASE)
    if not m:
        raise ValueError(f"Unsupported fiscal_period format: {value!r}")
    return int(m.group(1)), int(m.group(2))


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

    def _save_simple_quarter_event(
        self,
        *,
        company_ref: str,
        quarter_event: Dict[str, Any],
        document_ref: Optional[str] = None,
        thesis_ref: Optional[str] = None,
        created_by: str = "aion_equities.quarter_event_store",
        payload_patch: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        fiscal_period = quarter_event.get("fiscal_period") or quarter_event.get("period")
        if not fiscal_period:
            raise TypeError("_save_simple_quarter_event() requires fiscal_period/period")

        # Keep the ID shape your tests expect
        quarter_event_id = f"quarter_event/{company_ref}/{fiscal_period}"

        # Derive canonical-ish fields needed by AssessmentRuntime
        fiscal_year, fiscal_quarter = _parse_fiscal_period(fiscal_period)

        published_at = quarter_event.get("published_at")
        as_reported_date = (
            published_at
            or quarter_event.get("as_reported_date")
            or quarter_event.get("date")
            or _utc_today_date()
        )

        doc_ref = (
            document_ref
            or quarter_event.get("document_ref")
            or quarter_event.get("source_document_ref")
        )

        document_refs = []
        if doc_ref:
            document_refs.append(str(doc_ref))
        if isinstance(quarter_event.get("document_refs"), list):
            document_refs.extend([str(x) for x in quarter_event["document_refs"] if x])
        if not document_refs:
            document_refs = ["document:unknown"]

        source_hashes = quarter_event.get("source_hashes")
        if not isinstance(source_hashes, list) or len(source_hashes) == 0:
            prov = quarter_event.get("provenance_hash") or quarter_event.get("source_hash") or "sha256:unknown"
            source_hashes = [str(prov)]

        # Map key_numbers -> extraction.financials
        financials: Dict[str, Any] = {}
        if isinstance(quarter_event.get("key_numbers"), dict):
            financials = deepcopy(quarter_event["key_numbers"])

        narrative_summary = str(quarter_event.get("summary") or "").strip()

        canonical_like: Dict[str, Any] = {
            "quarter_event_id": quarter_event_id,
            "company_ref": str(company_ref),
            "period": {
                "fiscal_year": int(fiscal_year),
                "fiscal_quarter": int(fiscal_quarter),
            },
            "event_type": "quarterly_results",
            "as_reported_date": _date_str(as_reported_date),
            "source": {
                "document_refs": list(document_refs),
                "source_hashes": list(source_hashes),
            },
            "extraction": {
                "financials": deepcopy(financials),
                "narrative": {
                    "summary": narrative_summary,
                    "headline": quarter_event.get("headline"),
                    "ast_applied": bool(quarter_event.get("ast_applied", False)),
                },
            },
            "analysis": {
                "deltas_vs_prior": deepcopy(quarter_event.get("deltas_vs_prior", {})) if isinstance(quarter_event.get("deltas_vs_prior"), dict) else {},
                "flags": list(quarter_event.get("flags") or []) if isinstance(quarter_event.get("flags"), list) else [],
                "assessment_refs": list(quarter_event.get("assessment_refs") or []) if isinstance(quarter_event.get("assessment_refs"), list) else [],
            },
            "audit": {
                "created_at": _utc_now_iso(),
                "updated_at": _utc_now_iso(),
                "created_by": str(created_by),
            },
            # Keep compatibility top-level fields for existing tests + quick reading
            "document_ref": doc_ref,
            "thesis_ref": thesis_ref or quarter_event.get("thesis_ref"),
            "fiscal_period": fiscal_period,
            "published_at": published_at,
            "headline": quarter_event.get("headline"),
            "summary": quarter_event.get("summary"),
            "key_numbers": deepcopy(quarter_event.get("key_numbers", {})),
            "source_document_ref": quarter_event.get("source_document_ref") or doc_ref,
            "payload": deepcopy(quarter_event),
        }

        if payload_patch:
            canonical_like = _deep_merge(canonical_like, payload_patch)

        path = self.storage_path(quarter_event_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(canonical_like, ensure_ascii=False, indent=2), encoding="utf-8")
        return canonical_like

    def save_quarter_event(
        self,
        *,
        ticker: Optional[str] = None,
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
        """
        Dual-mode save:

        Legacy canonical mode:
          save_quarter_event(
            ticker=...,
            fiscal_year=...,
            fiscal_quarter=...,
            as_reported_date=...,
            ...
          )

        Intake/simple mode:
          save_quarter_event(
            company_ref="company/AHT.L",
            document_ref="document/AHT.L/2026-Q1",
            thesis_ref="thesis/...",
            quarter_event={...},
          )

        Also accepts payload=... as alias for quarter_event in simple mode.
        """
        company_ref = kwargs.pop("company_ref", None)
        document_ref = kwargs.pop("document_ref", None)
        thesis_ref = kwargs.pop("thesis_ref", None)
        quarter_event = kwargs.pop("quarter_event", None)
        payload_alias = kwargs.pop("payload", None)

        # New/simple intake mode
        if ticker is None and company_ref is not None and (quarter_event is not None or payload_alias is not None):
            seed = deepcopy(quarter_event or payload_alias or {})
            if not isinstance(seed, dict):
                raise TypeError("quarter_event/payload must be a dict in simple intake mode")

            payload_patch = quarter_event_payload_patch or kwargs.pop("payload_patch", None)

            return self._save_simple_quarter_event(
                company_ref=str(company_ref),
                quarter_event=seed,
                document_ref=document_ref,
                thesis_ref=thesis_ref,
                created_by=created_by,
                payload_patch=payload_patch,
            )

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

        if ticker is None or fiscal_year is None or fiscal_quarter is None or as_reported_date is None:
            raise TypeError(
                "save_quarter_event() requires either "
                "(ticker, fiscal_year, fiscal_quarter, as_reported_date) "
                "or (company_ref plus quarter_event/payload)"
            )

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

    def save_quarter_event_from_seed(
        self,
        *,
        company_ref: str,
        quarter_event_seed: Dict[str, Any],
        document_ref: Optional[str] = None,
        created_by: str = "aion_equities.quarter_event_store",
        quarter_event_payload_patch: Optional[Dict[str, Any]] = None,
        validate: bool = True,
        **aliases: Any,
    ) -> Dict[str, Any]:
        seed = deepcopy(quarter_event_seed or aliases.get("payload") or {})
        if not isinstance(seed, dict):
            raise TypeError("quarter_event_seed must be a dict")

        company_ref = str(company_ref or seed.get("company_ref") or "")
        if not company_ref:
            raise TypeError("save_quarter_event_from_seed() requires company_ref")

        if "/" in company_ref:
            _, ticker = company_ref.split("/", 1)
        else:
            ticker = company_ref

        document_ref = (
            document_ref
            or seed.get("document_ref")
            or seed.get("source_document_ref")
            or seed.get("ref")
        )

        fiscal_period = seed.get("fiscal_period") or seed.get("period")
        if fiscal_period is None:
            raise TypeError("save_quarter_event_from_seed() requires fiscal_period in seed")

        fiscal_year, fiscal_quarter = _parse_fiscal_period(fiscal_period)

        as_reported_date = (
            seed.get("published_at")
            or seed.get("as_reported_date")
            or seed.get("date")
            or _utc_today_date()
        )

        document_refs = []
        if document_ref:
            document_refs.append(str(document_ref))
        if isinstance(seed.get("document_refs"), list):
            document_refs.extend([str(x) for x in seed["document_refs"] if x])
        if not document_refs:
            document_refs = ["document:unknown"]

        source_hashes = seed.get("source_hashes")
        if not isinstance(source_hashes, list) or len(source_hashes) == 0:
            prov = seed.get("provenance_hash") or seed.get("source_hash") or "sha256:unknown"
            source_hashes = [str(prov)]

        narrative_summary = seed.get("summary") or ""

        financials: Dict[str, Any] = {}
        if isinstance(seed.get("key_numbers"), dict):
            financials = deepcopy(seed["key_numbers"])

        payload = build_quarter_event_payload(
            ticker=str(ticker),
            fiscal_year=int(fiscal_year),
            fiscal_quarter=int(fiscal_quarter),
            as_reported_date=as_reported_date,
            document_refs=list(document_refs),
            source_hashes=list(source_hashes),
            created_by=created_by,
            financials=financials,
            narrative_summary=str(narrative_summary),
            validate=False,
        )

        patch: Dict[str, Any] = {
            "extraction": {
                "narrative": {
                    "headline": seed.get("headline"),
                }
            }
        }

        if quarter_event_payload_patch:
            patch = _deep_merge(patch, quarter_event_payload_patch)

        payload = _deep_merge(payload, patch)

        if validate:
            validate_payload("quarter_event", payload, version=SCHEMA_PACK_VERSION)

        save_quarter_event_payload(payload, base_dir=self.events_dir, validate=False)
        return payload

    def load_quarter_event(self, quarter_event_id: str, *, validate: bool = False) -> Dict[str, Any]:
        path = self.storage_path(quarter_event_id)
        if not path.exists():
            raise FileNotFoundError(f"Quarter event payload not found: {path}")

        payload = json.loads(path.read_text(encoding="utf-8"))

        # If it's the intake/simple shape, return as-is
        if "headline" in payload or "key_numbers" in payload or "payload" in payload:
            return payload

        if validate:
            validate_payload("quarter_event", payload, version=SCHEMA_PACK_VERSION)
        return payload

    def quarter_event_exists(self, quarter_event_id: str) -> bool:
        return self.storage_path(quarter_event_id).exists()

    def list_quarter_events(self, company_ref: Optional[str] = None) -> List[str]:
        if not self.events_dir.exists():
            return []

        out: List[str] = []
        for path in sorted(self.events_dir.glob("*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue

            if company_ref is not None and payload.get("company_ref") != company_ref:
                continue

            qid = payload.get("quarter_event_id")
            if isinstance(qid, str):
                out.append(qid)

        return out