from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.modules.aion_business.runtime.canonical_business_identity import canonical_business_id
from backend.modules.aion_business.runtime.finance_bookkeeping_service import FinanceBookkeepingService


router = APIRouter(prefix="/api/aion/finance-bookkeeping", tags=["aion-finance-bookkeeping"])
service = FinanceBookkeepingService()


class PrepareRequest(BaseModel):
    prepared_by_person_id: str


class ApprovalRequest(BaseModel):
    approved_by_person_id: str
    approved_draft_hash: str


class PostRequest(BaseModel):
    posted_by_person_id: str


def _workspace(value: str) -> str:
    return canonical_business_id(value)


def _call(method, *args, **kwargs) -> Any:
    try:
        return method(*args, **kwargs)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/{workspace_id}/providers")
def providers(workspace_id: str) -> dict[str, Any]:
    return service.provider_catalog(_workspace(workspace_id))


@router.get("/{workspace_id}/drafts")
def drafts(workspace_id: str) -> dict[str, Any]:
    return {"drafts": _call(service.list, _workspace(workspace_id))}


@router.get("/{workspace_id}/ledger-summary")
def ledger_summary(workspace_id: str) -> dict[str, Any]:
    return _call(service.ledger_summary, _workspace(workspace_id))


@router.post("/{workspace_id}/documents/{document_id}/prepare")
def prepare(workspace_id: str, document_id: str, request: PrepareRequest) -> dict[str, Any]:
    return {"draft": _call(service.prepare_document, _workspace(workspace_id), document_id,
                            prepared_by_person_id=request.prepared_by_person_id)}


@router.post("/{workspace_id}/drafts/{draft_id}/approve")
def approve(workspace_id: str, draft_id: str, request: ApprovalRequest) -> dict[str, Any]:
    return {"draft": _call(service.approve, _workspace(workspace_id), draft_id,
                            approved_by_person_id=request.approved_by_person_id,
                            approved_draft_hash=request.approved_draft_hash)}


@router.post("/{workspace_id}/drafts/{draft_id}/post-internal")
def post_internal(workspace_id: str, draft_id: str, request: PostRequest) -> dict[str, Any]:
    return {"draft": _call(service.post_internal, _workspace(workspace_id), draft_id,
                            posted_by_person_id=request.posted_by_person_id)}
