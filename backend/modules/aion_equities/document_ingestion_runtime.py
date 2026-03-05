# /workspaces/COMDEX/backend/modules/aion_equities/document_ingestion_runtime.py
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from backend.modules.aion_equities.company_trigger_map_store import CompanyTriggerMapStore
from backend.modules.aion_equities.source_document_store import SourceDocumentStore


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _first_non_empty(*values: Any, default: Optional[str] = None) -> Optional[str]:
    for v in values:
        if v is None:
            continue
        s = str(v).strip()
        if s:
            return s
    return default


class DocumentIngestionRuntime:
    """
    Formal document ingestion bridge for AION equities.

    Current MVP responsibilities:
    - register uploaded source documents
    - map filing metadata into a quarter-event-like payload (legacy: quarter_event_payload)
    - build a lightweight assessment-ready ingestion result
    - optionally create / update a trigger-map shell for the period
    - return stable, alias-friendly output for downstream pipelines
    """

    def __init__(
        self,
        *,
        source_document_store: SourceDocumentStore,
        trigger_map_store: Optional[CompanyTriggerMapStore] = None,
    ):
        self.source_document_store = source_document_store
        self.trigger_map_store = trigger_map_store

    def register_source_document(
        self,
        *,
        company_ref: str,
        source_type: str,
        fiscal_period_ref: str,
        source_file_ref: str,
        published_at: Optional[str] = None,
        parsed_text_ref: Optional[str] = None,
        tables_ref: Optional[str] = None,
        provenance_hash: Optional[str] = None,
        generated_by: str = "aion_equities.document_ingestion_runtime",
        document_id: Optional[str] = None,
        ingestion_status: str = "registered",
        payload_patch: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return self.source_document_store.save_source_document(
            company_ref=company_ref,
            source_type=source_type,
            fiscal_period_ref=fiscal_period_ref,
            source_file_ref=source_file_ref,
            published_at=published_at,
            parsed_text_ref=parsed_text_ref,
            tables_ref=tables_ref,
            provenance_hash=provenance_hash,
            ingestion_status=ingestion_status,
            generated_by=generated_by,
            document_id=document_id,
            payload_patch=payload_patch,
        )

    def ingest_document(
        self,
        *,
        company_ref: str,
        source_type: str,
        fiscal_period_ref: str,
        source_file_ref: Optional[str] = None,
        published_at: Optional[str] = None,
        parsed_text_ref: Optional[str] = None,
        tables_ref: Optional[str] = None,
        provenance_hash: Optional[str] = None,
        generated_by: str = "aion_equities.document_ingestion_runtime",
        narrative_summary: Optional[Dict[str, Any]] = None,
        structured_financials: Optional[Dict[str, Any]] = None,
        trigger_entries: Optional[list[Dict[str, Any]]] = None,
        # aliases
        document_ref: Optional[str] = None,
        file_ref: Optional[str] = None,
        pdf_ref: Optional[str] = None,
        text_ref: Optional[str] = None,
        extracted_text_ref: Optional[str] = None,
        **_: Any,
    ) -> Dict[str, Any]:
        resolved_source_file_ref = _first_non_empty(
            source_file_ref,
            file_ref,
            pdf_ref,
            document_ref,
            default="file:unknown",
        )

        resolved_parsed_text_ref = _first_non_empty(
            parsed_text_ref,
            text_ref,
            extracted_text_ref,
            default=None,
        )

        source_document = self.register_source_document(
            company_ref=company_ref,
            source_type=source_type,
            fiscal_period_ref=fiscal_period_ref,
            source_file_ref=resolved_source_file_ref,
            published_at=published_at,
            parsed_text_ref=resolved_parsed_text_ref,
            tables_ref=tables_ref,
            provenance_hash=provenance_hash,
            generated_by=generated_by,
            ingestion_status="registered",
        )

        # ---- LEGACY: quarter_event_payload (tests rely on this) ----
        quarter_event_payload = {
            "quarter_event_id": f"{company_ref}/quarter_event/{fiscal_period_ref}",
            "company_ref": company_ref,
            "fiscal_period_ref": fiscal_period_ref,
            "source_document_ref": source_document["document_id"],
            "source_type": source_document["source_type"],
            "published_at": source_document.get("published_at") or published_at,
            "structured_financials": deepcopy(structured_financials or {}),
            "narrative_summary": deepcopy(narrative_summary or {}),
        }

        assessment_input_payload = {
            "company_ref": company_ref,
            "fiscal_period_ref": fiscal_period_ref,
            "source_document_ref": source_document["document_id"],
            "quarter_event_ref": quarter_event_payload["quarter_event_id"],
            "structured_financials": deepcopy(structured_financials or {}),
            "narrative_summary": deepcopy(narrative_summary or {}),
            "ingested_at": _utc_now_iso(),
        }

        trigger_map_payload = None
        if self.trigger_map_store is not None:
            trigger_map_payload = self.trigger_map_store.save_trigger_map(
                company_ref=company_ref,
                fiscal_period_ref=fiscal_period_ref,
                generated_by=generated_by,
                triggers=trigger_entries or [],
                validate=False,
            )

        # ---- linked_refs MUST match tests ----
        updated_source_document = self.register_source_document(
            company_ref=company_ref,
            source_type=source_type,
            fiscal_period_ref=fiscal_period_ref,
            source_file_ref=resolved_source_file_ref,
            published_at=published_at,
            parsed_text_ref=resolved_parsed_text_ref,
            tables_ref=tables_ref,
            provenance_hash=provenance_hash,
            generated_by=generated_by,
            document_id=source_document["document_id"],
            ingestion_status="mapped",
            payload_patch={
                "linked_refs": {
                    # tests expect these exact keys + id shapes
                    "quarter_event_ref": quarter_event_payload["quarter_event_id"],
                    "trigger_map_ref": (
                        trigger_map_payload["company_trigger_map_id"]
                        if isinstance(trigger_map_payload, dict)
                        else None
                    ),
                }
            },
        )

        # ---- NEW stable keys (for downstream pipeline wiring) ----
        normalized_inputs = {
            "source_type": str(source_type),
            "source_file_ref": str(resolved_source_file_ref),
            "parsed_text_ref": resolved_parsed_text_ref,
            "tables_ref": tables_ref,
            "published_at": published_at,
            "provenance_hash": provenance_hash,
        }

        ingestion_packet = {
            "packet_type": "aion_equities.document_ingestion",
            "generated_by": str(generated_by),
            "timestamp": _utc_now_iso(),
            "company_ref": str(company_ref),
            "fiscal_period_ref": str(fiscal_period_ref),
            "source_document_id": updated_source_document.get("document_id"),
        }

        return {
            # stable top-level
            "company_ref": str(company_ref),
            "fiscal_period_ref": str(fiscal_period_ref),
            "source_document": deepcopy(updated_source_document),
            "assessment_input_payload": deepcopy(assessment_input_payload),
            "trigger_map_payload": deepcopy(trigger_map_payload),
            "normalized_inputs": deepcopy(normalized_inputs),
            "ingestion_packet": deepcopy(ingestion_packet),

            # legacy keys (tests rely on these)
            "quarter_event_payload": deepcopy(quarter_event_payload),

            # forward-compat alias (optional)
            "quarter_event_seed": deepcopy(
                {
                    "fiscal_period": str(fiscal_period_ref),
                    "published_at": quarter_event_payload.get("published_at"),
                    "headline": (deepcopy(narrative_summary or {}).get("headline") if isinstance(narrative_summary, dict) else None),
                    "summary": (deepcopy(narrative_summary or {}).get("summary") if isinstance(narrative_summary, dict) else None),
                    "key_numbers": deepcopy(structured_financials or {}),
                    "source_document_ref": source_document.get("document_id"),
                    "document_ref": source_document.get("document_id"),
                }
            ),
        }


__all__ = [
    "DocumentIngestionRuntime",
]