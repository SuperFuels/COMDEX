from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from backend.modules.aion_equities.company_trigger_map_store import CompanyTriggerMapStore
from backend.modules.aion_equities.source_document_store import SourceDocumentStore


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class DocumentIngestionRuntime:
    """
    Formal document ingestion bridge for AION equities.

    Current MVP responsibilities:
    - register uploaded source documents
    - map filing metadata into a quarter-event-like payload
    - build a lightweight assessment-ready ingestion result
    - optionally create / update a trigger-map shell for the period

    This keeps reports as first-class source objects rather than chat-only context.
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
            ingestion_status="registered",
            generated_by=generated_by,
            document_id=document_id,
        )

    def ingest_document(
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
        narrative_summary: Optional[Dict[str, Any]] = None,
        structured_financials: Optional[Dict[str, Any]] = None,
        trigger_entries: Optional[list[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        source_document = self.register_source_document(
            company_ref=company_ref,
            source_type=source_type,
            fiscal_period_ref=fiscal_period_ref,
            source_file_ref=source_file_ref,
            published_at=published_at,
            parsed_text_ref=parsed_text_ref,
            tables_ref=tables_ref,
            provenance_hash=provenance_hash,
            generated_by=generated_by,
        )

        quarter_event_payload = {
            "quarter_event_id": f"{company_ref}/quarter_event/{fiscal_period_ref}",
            "company_ref": company_ref,
            "fiscal_period_ref": fiscal_period_ref,
            "source_document_ref": source_document["document_id"],
            "source_type": source_document["source_type"],
            "published_at": source_document["published_at"],
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

        updated_source_document = self.source_document_store.save_source_document(
            company_ref=company_ref,
            source_type=source_type,
            fiscal_period_ref=fiscal_period_ref,
            source_file_ref=source_file_ref,
            published_at=published_at,
            parsed_text_ref=parsed_text_ref,
            tables_ref=tables_ref,
            provenance_hash=provenance_hash,
            ingestion_status="mapped",
            generated_by=generated_by,
            document_id=source_document["document_id"],
            payload_patch={
                "linked_refs": {
                    "quarter_event_ref": quarter_event_payload["quarter_event_id"],
                    "trigger_map_ref": (
                        trigger_map_payload["company_trigger_map_id"]
                        if trigger_map_payload is not None
                        else None
                    ),
                }
            },
        )

        return {
            "source_document": updated_source_document,
            "quarter_event_payload": quarter_event_payload,
            "assessment_input_payload": assessment_input_payload,
            "trigger_map_payload": trigger_map_payload,
        }