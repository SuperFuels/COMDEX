from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


VALID_SOURCE_TYPES = {
    "quarterly_report",
    "trading_update",
    "annual_report",
    "presentation",
    "board_pack",
    "investor_call",
    "other",
}

VALID_INGESTION_STATUSES = {
    "registered",
    "parsed",
    "mapped",
    "failed",
}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _safe_segment(value: str) -> str:
    return str(value).replace("/", "_").replace("\\", "_").replace(":", "-").strip()


def _default_storage_dir() -> Path:
    return Path(__file__).resolve().parent / "data" / "source_documents"


def source_document_storage_path(
    company_ref: str,
    document_id: str,
    *,
    base_dir: Optional[Path] = None,
) -> Path:
    root = Path(base_dir) if base_dir is not None else _default_storage_dir()
    return root / _safe_segment(company_ref) / f"{_safe_segment(document_id)}.json"


def _normalize_source_type(value: Any) -> str:
    s = str(value or "other").strip().lower()
    return s if s in VALID_SOURCE_TYPES else "other"


def _normalize_ingestion_status(value: Any) -> str:
    s = str(value or "registered").strip().lower()
    return s if s in VALID_INGESTION_STATUSES else "registered"


def build_source_document_payload(
    *,
    company_ref: str,
    source_type: str,
    fiscal_period_ref: str,
    published_at: Optional[str] = None,
    source_file_ref: str,
    parsed_text_ref: Optional[str] = None,
    tables_ref: Optional[str] = None,
    ingestion_status: str = "registered",
    provenance_hash: Optional[str] = None,
    generated_by: str = "aion_equities.source_document_store",
    document_id: Optional[str] = None,
    payload_patch: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    source_type_n = _normalize_source_type(source_type)
    ingestion_status_n = _normalize_ingestion_status(ingestion_status)
    published_at_s = str(published_at or _utc_now_iso()).strip()

    doc_id = str(document_id or f"{company_ref}/source_document/{fiscal_period_ref}/{source_type_n}").strip()

    payload: Dict[str, Any] = {
        "document_id": doc_id,
        "company_ref": company_ref,
        "source_type": source_type_n,
        "fiscal_period_ref": fiscal_period_ref,
        "published_at": published_at_s,
        "source_file_ref": str(source_file_ref).strip(),
        "parsed_text_ref": str(parsed_text_ref).strip() if parsed_text_ref else "",
        "tables_ref": str(tables_ref).strip() if tables_ref else "",
        "ingestion_status": ingestion_status_n,
        "provenance_hash": str(provenance_hash or "").strip(),
        "audit": {
            "created_at": _utc_now_iso(),
            "updated_at": _utc_now_iso(),
            "created_by": generated_by,
        },
    }

    if payload_patch:
        payload.update(deepcopy(payload_patch))
        payload["document_id"] = doc_id
        payload["company_ref"] = company_ref
        payload["source_type"] = source_type_n
        payload["fiscal_period_ref"] = fiscal_period_ref
        payload["source_file_ref"] = str(source_file_ref).strip()
        payload["ingestion_status"] = _normalize_ingestion_status(payload.get("ingestion_status"))

    return payload


class SourceDocumentStore:
    def __init__(self, base_dir: str | Path):
        self.base_dir = Path(base_dir) / "source_documents"
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def storage_path(self, company_ref: str, document_id: str) -> Path:
        return source_document_storage_path(
            company_ref,
            document_id,
            base_dir=self.base_dir,
        )

    def save_source_document(
        self,
        *,
        company_ref: str,
        source_type: str,
        fiscal_period_ref: str,
        published_at: Optional[str] = None,
        source_file_ref: str,
        parsed_text_ref: Optional[str] = None,
        tables_ref: Optional[str] = None,
        ingestion_status: str = "registered",
        provenance_hash: Optional[str] = None,
        generated_by: str = "aion_equities.source_document_store",
        document_id: Optional[str] = None,
        payload_patch: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        payload = build_source_document_payload(
            company_ref=company_ref,
            source_type=source_type,
            fiscal_period_ref=fiscal_period_ref,
            published_at=published_at,
            source_file_ref=source_file_ref,
            parsed_text_ref=parsed_text_ref,
            tables_ref=tables_ref,
            ingestion_status=ingestion_status,
            provenance_hash=provenance_hash,
            generated_by=generated_by,
            document_id=document_id,
            payload_patch=payload_patch,
        )
        path = self.storage_path(company_ref, payload["document_id"])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return payload

    def load_source_document(self, company_ref: str, document_id: str) -> Dict[str, Any]:
        path = self.storage_path(company_ref, document_id)
        if not path.exists():
            raise FileNotFoundError(f"Source document not found: {path}")
        return json.loads(path.read_text(encoding="utf-8"))

    def load_source_document_by_id(self, document_id: str) -> Dict[str, Any]:
        company_ref = self._company_ref_from_document_id(document_id)
        return self.load_source_document(company_ref, document_id)

    def source_document_exists(self, company_ref: str, document_id: str) -> bool:
        return self.storage_path(company_ref, document_id).exists()

    def list_source_documents(self, company_ref: str) -> List[str]:
        company_dir = self.base_dir / _safe_segment(company_ref)
        if not company_dir.exists():
            return []
        out: List[str] = []
        for path in sorted(company_dir.glob("*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            out.append(payload["document_id"])
        return out

    def list_source_documents_for_period(self, company_ref: str, fiscal_period_ref: str) -> List[Dict[str, Any]]:
        company_dir = self.base_dir / _safe_segment(company_ref)
        if not company_dir.exists():
            return []
        out: List[Dict[str, Any]] = []
        for path in sorted(company_dir.glob("*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            if str(payload.get("fiscal_period_ref")) == str(fiscal_period_ref):
                out.append(payload)
        return out

    def _company_ref_from_document_id(self, document_id: str) -> str:
        parts = str(document_id).split("/source_document/")
        if len(parts) != 2:
            raise ValueError(f"Invalid source document id: {document_id!r}")
        return parts[0]


__all__ = [
    "build_source_document_payload",
    "SourceDocumentStore",
]