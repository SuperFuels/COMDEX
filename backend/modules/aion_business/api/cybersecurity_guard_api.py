from __future__ import annotations

import base64
import ssl
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from backend.modules.aion_business.runtime.aion_flow_session_authority import AionFlowSessionAuthority, VerifiedAionFlowSession
from backend.modules.aion_business.runtime.cybersecurity_guard_service import CybersecurityGuardService


router = APIRouter(prefix="/api/aion/business/cybersecurity", tags=["aion-cybersecurity"])
_authority = AionFlowSessionAuthority()


async def require_session(request: Request) -> VerifiedAionFlowSession:
    try:
        body = await request.body()
        target = request.url.path + (f"?{request.url.query}" if request.url.query else "")
        return _authority.verify(method=request.method, target=target, body=body, headers=request.headers)
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def service() -> CybersecurityGuardService:
    return CybersecurityGuardService()


class QuestionInput(BaseModel):
    question: str = Field(min_length=1, max_length=4000)


class ActionInput(BaseModel):
    action_type: str = Field(min_length=1, max_length=80)
    target: str = Field(min_length=1, max_length=500)
    reason: str = Field(min_length=1, max_length=2000)


class ApprovalInput(BaseModel):
    confirmation: str = Field(min_length=1, max_length=200)


class IncidentInput(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    severity: str = Field(default="MEDIUM", max_length=20)
    summary: str = Field(default="", max_length=5000)


class FeedInput(BaseModel):
    feed: dict
    signature_base64: str = Field(min_length=20, max_length=1000)


class SecretScanInput(BaseModel):
    scope: str = Field(min_length=1, max_length=2000)
    maximum_files: int = Field(default=2000, ge=1, le=10_000)


class AttachmentInput(BaseModel):
    filename: str = Field(min_length=1, max_length=240)
    media_type: str = Field(default="application/octet-stream", max_length=160)
    data_base64: str = Field(min_length=1, max_length=36_000_000)


class DomainInput(BaseModel):
    hostname: str = Field(min_length=1, max_length=253)
    port: int = Field(default=443, ge=1, le=65535)


class RestoreTestInput(BaseModel):
    backup_system: str = Field(min_length=1, max_length=160)
    tested_at: str = Field(min_length=1, max_length=80)
    result: str = Field(min_length=1, max_length=20)
    evidence_reference: str = Field(min_length=1, max_length=500)
    notes: str = Field(default="", max_length=2000)


@router.post("/status")
def status(session: VerifiedAionFlowSession = Depends(require_session)) -> dict:
    return {"ok": True, "state": service().load(session.workspace_id)}


@router.post("/sentinel/status")
def sentinel_status(session: VerifiedAionFlowSession = Depends(require_session)) -> dict:
    return {"ok": True, "sentinel": service().sentinel_status()}


@router.post("/sentinel/review-complete")
def sentinel_review_complete(session: VerifiedAionFlowSession = Depends(require_session)) -> dict:
    return {"ok": True, "sentinel": service().set_sentinel_state("verified", actor_id=session.person_id, seconds=120)}


@router.post("/scan/safe")
def safe_scan(session: VerifiedAionFlowSession = Depends(require_session)) -> dict:
    return {"ok": True, **service().run_safe_scan(session.workspace_id, actor_id=session.person_id)}


@router.post("/investigate")
def investigate(payload: QuestionInput, session: VerifiedAionFlowSession = Depends(require_session)) -> dict:
    return {"ok": True, "investigation": service().investigate(session.workspace_id, question=payload.question)}


@router.post("/actions/propose")
def propose(payload: ActionInput, session: VerifiedAionFlowSession = Depends(require_session)) -> dict:
    try:
        value = service().propose_action(session.workspace_id, actor_id=session.person_id, **payload.model_dump())
        return {"ok": True, "proposal": value}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/actions/{proposal_id}/approve")
def approve(proposal_id: str, payload: ApprovalInput, session: VerifiedAionFlowSession = Depends(require_session)) -> dict:
    try:
        value = service().approve_action(session.workspace_id, proposal_id, actor_id=session.person_id, confirmation=payload.confirmation)
        return {"ok": True, "proposal": value}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/actions/{proposal_id}/execute")
def execute(proposal_id: str, payload: ApprovalInput, session: VerifiedAionFlowSession = Depends(require_session)) -> dict:
    try:
        value = service().execute_approved_action(
            session.workspace_id, proposal_id, actor_id=session.person_id, confirmation=payload.confirmation,
        )
        return {"ok": True, "proposal": value}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/incidents")
def create_incident(payload: IncidentInput, session: VerifiedAionFlowSession = Depends(require_session)) -> dict:
    try:
        value = service().create_incident(session.workspace_id, actor_id=session.person_id, **payload.model_dump())
        return {"ok": True, "incident": value}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/vulnerability-feed/import")
def import_feed(payload: FeedInput, session: VerifiedAionFlowSession = Depends(require_session)) -> dict:
    try:
        value = service().import_vulnerability_feed(session.workspace_id, actor_id=session.person_id, **payload.model_dump())
        return {"ok": True, "feed": value}
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/updates/check")
def check_updates(session: VerifiedAionFlowSession = Depends(require_session)) -> dict:
    return {"ok": True, "update_check": service().check_updates(session.workspace_id, actor_id=session.person_id)}


@router.post("/vulnerabilities/assess")
def assess_vulnerabilities(session: VerifiedAionFlowSession = Depends(require_session)) -> dict:
    try:
        return {"ok": True, "assessment": service().assess_vulnerabilities(session.workspace_id, actor_id=session.person_id)}
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/secrets/scan")
def scan_secrets(payload: SecretScanInput, session: VerifiedAionFlowSession = Depends(require_session)) -> dict:
    try:
        value = service().scan_secrets(session.workspace_id, actor_id=session.person_id, **payload.model_dump())
        return {"ok": True, "secret_scan": value}
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/attachments/analyse")
def analyse_attachment(payload: AttachmentInput, session: VerifiedAionFlowSession = Depends(require_session)) -> dict:
    try:
        data = base64.b64decode(payload.data_base64, validate=True)
        value = service().analyse_attachment(
            session.workspace_id, actor_id=session.person_id, filename=payload.filename,
            media_type=payload.media_type, data=data,
        )
        return {"ok": True, "analysis": value}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/domains/check")
def check_domain(payload: DomainInput, session: VerifiedAionFlowSession = Depends(require_session)) -> dict:
    try:
        return {"ok": True, "domain_check": service().check_domain(session.workspace_id, actor_id=session.person_id, **payload.model_dump())}
    except (ValueError, OSError, ssl.SSLError) as exc:
        raise HTTPException(status_code=400, detail=f"domain_security_check_failed: {exc}") from exc


@router.post("/backups/restore-tests")
def record_restore_test(payload: RestoreTestInput, session: VerifiedAionFlowSession = Depends(require_session)) -> dict:
    try:
        return {"ok": True, "restore_test": service().record_restore_test(session.workspace_id, actor_id=session.person_id, **payload.model_dump())}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
