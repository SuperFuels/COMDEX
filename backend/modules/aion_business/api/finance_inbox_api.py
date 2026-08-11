"""HTTP surface for the provider-neutral Finance Inbox."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from backend.modules.aion_business.runtime.canonical_business_identity import canonical_business_id
from backend.modules.aion_business.runtime.finance_inbox_service import (
    FinanceInboxService,
    MAX_DOCUMENT_BYTES,
)


router = APIRouter(prefix="/api/aion/business/finance-inbox", tags=["aion-business-finance-inbox"])


class FinanceDocumentReviewRequest(BaseModel):
    fields: dict[str, Any] = Field(default_factory=dict)
    ownership: dict[str, Any] = Field(default_factory=dict)
    allocation: dict[str, Any] = Field(default_factory=dict)
    destination: str | None = None
    reviewed_by_person_id: str | None = None
    expected_revision: int | None = None


class FinanceDocumentDecisionRequest(BaseModel):
    decision: str
    decided_by_person_id: str
    note: str | None = None
    expected_revision: int | None = None


class FinanceDocumentExtractionRequest(BaseModel):
    provider: str | None = None
    expected_revision: int | None = None


class FinanceExpensePolicyRequest(BaseModel):
    policy: dict[str, Any] = Field(default_factory=dict)
    expected_revision: int | None = None


def _workspace(value: str) -> str:
    try:
        return canonical_business_id(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _http_error(error: Exception) -> HTTPException:
    code = str(error)
    if isinstance(error, PermissionError):
        return HTTPException(status_code=403, detail=code)
    if isinstance(error, KeyError) or isinstance(error, FileNotFoundError):
        return HTTPException(status_code=404, detail=code.strip("'"))
    if code == "finance_inbox_revision_conflict":
        return HTTPException(status_code=409, detail=code)
    if code == "finance_document_too_large":
        return HTTPException(status_code=413, detail=code)
    return HTTPException(status_code=422, detail=code)


@router.get("/channels")
def get_finance_inbox_channels() -> dict[str, Any]:
    model = FinanceInboxService().empty("template")
    return {
        "ok": True,
        "channels": model["intake_channels"],
        "accounting_destinations": model["accounting_destinations"],
        "max_document_bytes": MAX_DOCUMENT_BYTES,
    }


@router.get("/{workspace_id}")
def get_finance_inbox(workspace_id: str) -> dict[str, Any]:
    key = _workspace(workspace_id)
    from backend.modules.aion_business.runtime.finance_receipt_vision import FinanceReceiptVisionReader

    return {
        "ok": True, "workspace_id": key, "inbox": FinanceInboxService().get(key),
        "reader_providers": FinanceReceiptVisionReader.provider_status(),
    }


@router.put("/{workspace_id}/expense-policy")
def update_finance_expense_policy(
    workspace_id: str, request: FinanceExpensePolicyRequest,
) -> dict[str, Any]:
    key = _workspace(workspace_id)
    try:
        policy = FinanceInboxService().update_expense_policy(
            key, request.policy, expected_revision=request.expected_revision,
        )
    except (ValueError, PermissionError, KeyError) as error:
        raise _http_error(error) from error
    return {"ok": True, "workspace_id": key, "expense_policy": policy}


@router.post("/{workspace_id}/documents")
async def upload_finance_document(
    workspace_id: str,
    file: UploadFile = File(...),
    channel: str = Form("desktop_upload"),
    document_type: str = Form("receipt"),
    submitted_by_person_id: str | None = Form(None),
    department_id: str | None = Form(None),
    project_id: str | None = Form(None),
    card_asset_id: str | None = Form(None),
    sender_address: str | None = Form(None),
    source_reference: str | None = Form(None),
) -> dict[str, Any]:
    key = _workspace(workspace_id)
    content = await file.read(MAX_DOCUMENT_BYTES + 1)
    try:
        document, duplicate = FinanceInboxService().ingest(
            key, filename=file.filename or "document", content=content,
            mime_type=file.content_type, channel=channel, document_type=document_type,
            submitted_by_person_id=submitted_by_person_id or None,
            department_id=department_id or None, project_id=project_id or None,
            card_asset_id=card_asset_id or None, sender_address=sender_address or None,
            source_reference=source_reference or None,
        )
    except (ValueError, PermissionError, KeyError) as error:
        raise _http_error(error) from error
    return {"ok": True, "workspace_id": key, "document": document, "duplicate": duplicate}


@router.get("/{workspace_id}/documents/{document_id}/file")
def get_finance_document_file(workspace_id: str, document_id: str) -> FileResponse:
    key = _workspace(workspace_id)
    try:
        path, document = FinanceInboxService().file_path(key, document_id)
    except (ValueError, FileNotFoundError, KeyError) as error:
        raise _http_error(error) from error
    return FileResponse(
        path, media_type=document.get("source", {}).get("mime_type") or "application/octet-stream",
        filename=document.get("source", {}).get("filename") or path.name,
    )


@router.post("/{workspace_id}/documents/{document_id}/extract")
def extract_finance_document(
    workspace_id: str, document_id: str, request: FinanceDocumentExtractionRequest,
) -> dict[str, Any]:
    key = _workspace(workspace_id)
    try:
        document = FinanceInboxService().extract(
            key, document_id, provider=request.provider,
            expected_revision=request.expected_revision,
        )
    except (ValueError, RuntimeError, PermissionError, KeyError, OSError) as error:
        raise _http_error(error) from error
    return {"ok": True, "workspace_id": key, "document": document}


@router.put("/{workspace_id}/documents/{document_id}/review")
def review_finance_document(
    workspace_id: str, document_id: str, request: FinanceDocumentReviewRequest,
) -> dict[str, Any]:
    key = _workspace(workspace_id)
    try:
        document = FinanceInboxService().review(
            key, document_id, fields=request.fields, ownership=request.ownership,
            allocation=request.allocation, destination=request.destination,
            reviewed_by_person_id=request.reviewed_by_person_id,
            expected_revision=request.expected_revision,
        )
    except (ValueError, PermissionError, KeyError) as error:
        raise _http_error(error) from error
    return {"ok": True, "workspace_id": key, "document": document}


@router.post("/{workspace_id}/documents/{document_id}/decision")
def decide_finance_document(
    workspace_id: str, document_id: str, request: FinanceDocumentDecisionRequest,
) -> dict[str, Any]:
    key = _workspace(workspace_id)
    try:
        document = FinanceInboxService().decide(
            key, document_id, decision=request.decision,
            decided_by_person_id=request.decided_by_person_id, note=request.note,
            expected_revision=request.expected_revision,
        )
    except (ValueError, PermissionError, KeyError) as error:
        raise _http_error(error) from error
    return {"ok": True, "workspace_id": key, "document": document}
