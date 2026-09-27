from __future__ import annotations

import json
import base64
import os
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel, Field

from backend.modules.aion_business.runtime.aion_flow_session_authority import (
    AionFlowSessionAuthority,
    VerifiedAionFlowSession,
)
from backend.modules.aion_business.runtime.legal_signing_service import LegalSigningError, LegalSigningService
from backend.modules.aion_business.runtime.legal_matter_service import LegalMatterError, LegalMatterService
from backend.modules.aion_business.runtime.legal_document_service import LegalDocumentError, LegalDocumentService
from backend.modules.aion_business.runtime.legal_template_service import LegalTemplateError, LegalTemplateService
from backend.modules.aion_business.runtime.legal_secure_storage import LegalKeyStore
from backend.modules.aion_business.runtime.public_signer_rate_limit import PublicSignerRateLimiter
from backend.modules.aion_business.runtime.paths import AIONBusinessPaths


router = APIRouter(prefix="/api/aion/business/legal-signing", tags=["aion-legal-signing"])
public_router = APIRouter(tags=["aion-legal-signing-public"])
_authority = AionFlowSessionAuthority()
_public_signer_limiter = PublicSignerRateLimiter()


async def require_legal_session(request: Request) -> VerifiedAionFlowSession:
    try:
        body = await request.body()
        target = request.url.path + (f"?{request.url.query}" if request.url.query else "")
        return _authority.verify(method=request.method, target=target, body=body, headers=request.headers)
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def service() -> LegalSigningService:
    return LegalSigningService()


def matter_service() -> LegalMatterService:
    return LegalMatterService()


def document_service() -> LegalDocumentService:
    return LegalDocumentService()


def template_service() -> LegalTemplateService:
    return LegalTemplateService()


class SignerInput(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    email: str = Field(min_length=3, max_length=254)
    role: str = Field(default="Signer", max_length=100)
    verification_method: str = Field(default="typed_name_email", max_length=40)


class EnvelopeCreate(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    document_content: str = Field(min_length=1, max_length=1_000_000)
    signers: list[SignerInput] = Field(min_length=1, max_length=20)
    expires_in_days: int = Field(default=14, ge=1, le=90)
    supersedes_envelope_id: str | None = Field(default=None, max_length=120)


class ApprovalInput(BaseModel):
    review_hash: str = Field(min_length=64, max_length=64)


class ReasonInput(BaseModel):
    reason: str = Field(default="", max_length=500)


class ReminderInput(BaseModel):
    signer_id: str = Field(min_length=1, max_length=120)


class SignInput(BaseModel):
    typed_name: str = Field(min_length=1, max_length=160)
    identity_email: str = Field(min_length=3, max_length=254)
    identity_code: str = Field(default="", max_length=200)


class CopyDeliveryInput(BaseModel):
    signer_id: str = Field(min_length=1, max_length=120)
    delivery_reference: str = Field(min_length=1, max_length=240)


class ProofVerifyInput(BaseModel):
    document_content: str | None = Field(default=None, max_length=1_000_000)
    trusted_validator_set_root: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")


class ProofRetryInput(BaseModel):
    limit: int = Field(default=25, ge=1, le=250)


class LifecycleNoticeInput(BaseModel):
    notice_type: str = Field(min_length=1, max_length=40)
    reason: str = Field(min_length=1, max_length=1000)
    effective_at: str = Field(min_length=1, max_length=40)
    reference: str = Field(default="", max_length=240)
    acknowledge_preserved_evidence: bool = False


class JurisdictionInput(BaseModel):
    country_code: str = Field(min_length=2, max_length=2)
    region: str = Field(default="", max_length=160)
    governing_law: str = Field(min_length=1, max_length=240)
    forum: str = Field(default="", max_length=240)
    owner_confirmed: bool = False


class MatterCreateInput(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    counterparty: str = Field(default="", max_length=240)
    matter_type: str = Field(default="GENERAL_ADVICE", max_length=40)
    risk: str = Field(default="NORMAL", max_length=20)
    summary: str = Field(default="", max_length=5000)
    jurisdiction: JurisdictionInput


class MatterTriageInput(BaseModel):
    risk: str | None = Field(default=None, max_length=20)
    status: str | None = Field(default=None, max_length=20)
    summary: str | None = Field(default=None, max_length=5000)
    jurisdiction: JurisdictionInput | None = None


class MatterLinkInput(BaseModel):
    record_type: str = Field(min_length=1, max_length=40)
    reference_id: str = Field(min_length=1, max_length=180)
    label: str = Field(default="", max_length=240)
    content_sha256: str = Field(default="", max_length=64)


class MatterObligationInput(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    obligation_type: str = Field(default="ACTION", max_length=40)
    due_at: str = Field(min_length=1, max_length=40)
    remind_at: list[str] = Field(default_factory=list, max_length=20)
    owner_id: str = Field(default="", max_length=160)
    source_reference_id: str = Field(default="", max_length=180)


class MatterObligationStatusInput(BaseModel):
    status: str = Field(min_length=1, max_length=20)


class MatterEscalationInput(BaseModel):
    reason: str = Field(min_length=1, max_length=2000)
    urgency: str = Field(default="NORMAL", max_length=20)
    requested_professional: str = Field(default="", max_length=240)


class MatterDueObligationsInput(BaseModel):
    as_of: str | None = Field(default=None, max_length=40)


class LegalDocumentIngestInput(BaseModel):
    filename: str = Field(min_length=1, max_length=240)
    media_type: str = Field(min_length=1, max_length=160)
    data_base64: str = Field(min_length=1, max_length=36_000_000)
    matter_id: str = Field(default="", max_length=180)


class LegalDocumentClassificationInput(BaseModel):
    category: str = Field(min_length=1, max_length=80)


class LegalDocumentComparisonInput(BaseModel):
    base_document_id: str = Field(min_length=1, max_length=180)


class LegalDocumentRedlineInput(BaseModel):
    finding_id: str = Field(default="", max_length=180)
    original_text: str = Field(min_length=1, max_length=20_000)
    proposed_text: str = Field(min_length=1, max_length=20_000)
    rationale: str = Field(default="", max_length=5000)


class LegalNegotiationPositionInput(BaseModel):
    issue: str = Field(min_length=1, max_length=500)
    business_position: str = Field(min_length=1, max_length=5000)
    counterparty_position: str = Field(default="", max_length=5000)


class LegalRecoveryInput(BaseModel):
    password: str = Field(min_length=12, max_length=1024)


class LegalRecoveryImportInput(LegalRecoveryInput):
    recovery_bundle: dict[str, Any]
    acknowledge_key_restore: bool = False


class LegalKeyRotationInput(LegalRecoveryInput):
    rotate_signing_key: bool = True
    rotate_signing_storage: bool = True
    rotate_matter_storage: bool = True
    rotate_document_storage: bool = True
    rotate_template_storage: bool = True


class LegalTemplateCreateInput(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    template_type: str = Field(min_length=1, max_length=80)
    jurisdiction: JurisdictionInput
    content: str = Field(min_length=1, max_length=500_000)
    intended_use: str = Field(default="", max_length=2000)
    source_template_id: str = Field(default="", max_length=180)


class LegalTemplateApprovalInput(BaseModel):
    expected_content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    reviewer_name: str = Field(min_length=1, max_length=240)
    reviewer_qualification: str = Field(min_length=1, max_length=500)
    review_scope: str = Field(min_length=1, max_length=5000)
    approved_jurisdiction: str = Field(min_length=1, max_length=500)
    acknowledge_qualified_review: bool = False
    review_interval_days: int = Field(default=365, ge=1, le=1825)


class LegalTemplateWithdrawalInput(BaseModel):
    reason: str = Field(min_length=1, max_length=2000)
    legal_change_reference: str = Field(min_length=1, max_length=1000)
    acknowledge_withdrawal: bool = False


class LegalTemplateReviewScheduleInput(BaseModel):
    as_of: str | None = Field(default=None, max_length=40)


class LegalTemplateInstantiateInput(BaseModel):
    values: dict[str, str] = Field(default_factory=dict, max_length=128)
    filename: str = Field(min_length=1, max_length=240)
    matter_id: str = Field(default="", max_length=180)


class RecordsGovernanceInput(BaseModel):
    retain_until: str | None = Field(default=None, max_length=40)
    legal_hold: bool | None = None
    legal_hold_reason: str = Field(default="", max_length=1000)


class RecordDeletionInput(BaseModel):
    confirmation: str = Field(min_length=1, max_length=180)


class SignedCopyDeliveryQueueInput(BaseModel):
    provider: str = Field(min_length=1, max_length=40)
    acknowledge_external_send: bool = False


class SignedCopyDeliveryRunInput(BaseModel):
    acknowledge_external_send: bool = False
    limit: int = Field(default=25, ge=1, le=250)
    force: bool = False


class SignedCopyDeliveryConfirmationInput(BaseModel):
    outcome: str = Field(min_length=1, max_length=40)
    provider_reference: str = Field(min_length=1, max_length=500)


class SignedCopyDeliveryRetryInput(BaseModel):
    reason: str = Field(min_length=1, max_length=500)
    acknowledge_external_send: bool = False


class SignedCopyDeliveryReceiptRefreshInput(BaseModel):
    limit: int = Field(default=25, ge=1, le=250)


@public_router.post("/api/aion/business/legal-signing/webhooks/resend", status_code=202)
async def resend_signed_copy_delivery_webhook(request: Request) -> dict[str, Any]:
    """Receive authenticated Resend outcomes without exposing workspace identity."""

    configured = str(os.getenv("RESEND_WEBHOOK_SIGNING_SECRETS") or os.getenv("RESEND_WEBHOOK_SIGNING_SECRET") or "")
    secrets = [item.strip() for item in configured.split(",") if item.strip()]
    if not secrets:
        raise HTTPException(status_code=503, detail="resend_webhook_signing_secret_not_configured")
    raw_body = await request.body()
    try:
        result = service().ingest_resend_delivery_webhook(
            raw_body,
            {str(key): str(value) for key, value in request.headers.items()},
            webhook_secrets=secrets,
        )
    except LegalSigningError as exc:
        detail = str(exc)
        if detail in {
            "resend_webhook_signature_headers_required",
            "resend_webhook_signature_invalid",
            "resend_webhook_timestamp_invalid",
            "resend_webhook_timestamp_outside_tolerance",
        }:
            status = 401
        elif detail in {"resend_webhook_event_id_conflict", "resend_webhook_provider_reference_mismatch"}:
            status = 409
        else:
            status = 400
        raise HTTPException(status_code=status, detail=detail) from exc
    return {
        "ok": True,
        "accepted": bool(result.get("accepted")),
        "ignored": bool(result.get("ignored")),
        "duplicate": bool(result.get("duplicate")),
        "outcome": result.get("outcome"),
        "conflict": bool(result.get("conflict")),
    }


def _call(operation):
    try:
        return operation()
    except LegalSigningError as exc:
        detail = str(exc)
        status = 404 if detail in {"envelope_not_found", "secure_signing_link_invalid"} else 409 if detail.startswith("invalid_envelope_state") else 422
        raise HTTPException(status_code=status, detail=detail) from exc


def _require_public_signer_access(request: Request, token: str, *, write: bool) -> None:
    if not LegalSigningService.SIGNER_TOKEN_PATTERN.fullmatch(str(token or "")):
        raise HTTPException(status_code=404, detail="secure_signing_link_invalid")
    source = request.client.host if request.client is not None else "unknown"
    allowed, retry_after = _public_signer_limiter.allow(
        source=source, token=token, write=write,
    )
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="secure_signing_rate_limit_exceeded",
            headers={"Retry-After": str(retry_after), "Cache-Control": "no-store"},
        )


def _matter_call(operation):
    try:
        return operation()
    except LegalMatterError as exc:
        detail = str(exc)
        raise HTTPException(status_code=404 if detail == "matter_not_found" else 422, detail=detail) from exc


def _document_call(operation):
    try:
        return operation()
    except LegalDocumentError as exc:
        detail = str(exc)
        raise HTTPException(status_code=404 if detail == "document_not_found" else 422, detail=detail) from exc


def _template_call(operation):
    try:
        return operation()
    except LegalTemplateError as exc:
        detail = str(exc)
        raise HTTPException(status_code=404 if detail == "template_not_found" else 422, detail=detail) from exc


def _legal_key_stores() -> tuple[LegalKeyStore, LegalKeyStore, LegalKeyStore, LegalKeyStore]:
    return (
        LegalKeyStore(AIONBusinessPaths.LEGAL_SIGNING),
        LegalKeyStore(AIONBusinessPaths.LEGAL_MATTERS),
        LegalKeyStore(AIONBusinessPaths.LEGAL_DOCUMENTS),
        LegalKeyStore(AIONBusinessPaths.LEGAL_TEMPLATES),
    )


@router.post("/security/status")
def legal_security_status(session: VerifiedAionFlowSession = Depends(require_legal_session)) -> dict[str, Any]:
    signing, matters, documents, templates = _legal_key_stores()
    return {
        "ok": True,
        "workspace_id": session.workspace_id,
        "signing": signing.status(),
        "matters": matters.status(),
        "documents": documents.status(),
        "templates": templates.status(),
        "encrypted_at_rest": True,
        "production_key_policy": "platform_keychain_required",
    }


@router.post("/security/recovery/export")
def export_legal_recovery_bundle(
    payload: LegalRecoveryInput,
    session: VerifiedAionFlowSession = Depends(require_legal_session),
) -> dict[str, Any]:
    signing, matters, documents, templates = _legal_key_stores()
    return {
        "ok": True,
        "recovery_bundle": {
            "schema_version": "tessaris.legal-combined-key-recovery.v3",
            "workspace_id": session.workspace_id,
            "signing": signing.export_recovery_bundle(payload.password),
            "matters": matters.export_recovery_bundle(payload.password),
            "documents": documents.export_recovery_bundle(payload.password),
            "templates": templates.export_recovery_bundle(payload.password),
        },
        "raw_keys_exposed": False,
    }


@router.post("/security/recovery/import")
def import_legal_recovery_bundle(
    payload: LegalRecoveryImportInput,
    session: VerifiedAionFlowSession = Depends(require_legal_session),
) -> dict[str, Any]:
    if not payload.acknowledge_key_restore:
        raise HTTPException(status_code=422, detail="acknowledge_key_restore_required")
    bundle = dict(payload.recovery_bundle or {})
    if bundle.get("schema_version") not in {"tessaris.legal-combined-key-recovery.v1", "tessaris.legal-combined-key-recovery.v2", "tessaris.legal-combined-key-recovery.v3"}:
        raise HTTPException(status_code=422, detail="legal_combined_recovery_bundle_invalid")
    if bundle.get("workspace_id") != session.workspace_id:
        raise HTTPException(status_code=403, detail="legal_recovery_workspace_mismatch")
    signing, matters, documents, templates = _legal_key_stores()
    result = {
        "ok": True,
        "signing": signing.import_recovery_bundle(dict(bundle.get("signing") or {}), payload.password),
        "matters": matters.import_recovery_bundle(dict(bundle.get("matters") or {}), payload.password),
    }
    if bundle.get("schema_version") in {"tessaris.legal-combined-key-recovery.v2", "tessaris.legal-combined-key-recovery.v3"}:
        result["documents"] = documents.import_recovery_bundle(dict(bundle.get("documents") or {}), payload.password)
    else:
        result["documents"] = {"restored": False, "reason": "legacy_bundle_has_no_document_keys"}
    if bundle.get("schema_version") == "tessaris.legal-combined-key-recovery.v3":
        result["templates"] = templates.import_recovery_bundle(dict(bundle.get("templates") or {}), payload.password)
    else:
        result["templates"] = {"restored": False, "reason": "legacy_bundle_has_no_template_keys"}
    return result


@router.post("/security/rotate")
def rotate_legal_keys(
    payload: LegalKeyRotationInput,
    session: VerifiedAionFlowSession = Depends(require_legal_session),
) -> dict[str, Any]:
    signing_service = service()
    signing, matters, documents, templates = (
        signing_service.key_store,
        LegalKeyStore(AIONBusinessPaths.LEGAL_MATTERS),
        LegalKeyStore(AIONBusinessPaths.LEGAL_DOCUMENTS),
        LegalKeyStore(AIONBusinessPaths.LEGAL_TEMPLATES),
    )
    # Preserve an existing legacy proof identity as retired v1 before rotating.
    signing_service.proof_service._private_key(1)
    recovery = {
        "schema_version": "tessaris.legal-combined-key-recovery.v3",
        "workspace_id": session.workspace_id,
        "signing": signing.export_recovery_bundle(payload.password),
        "matters": matters.export_recovery_bundle(payload.password),
        "documents": documents.export_recovery_bundle(payload.password),
        "templates": templates.export_recovery_bundle(payload.password),
    }
    rotations = []
    if payload.rotate_signing_key:
        rotations.append(signing.rotate_signing_key())
    if payload.rotate_signing_storage:
        rotations.append(signing.rotate_encryption_key(session.workspace_id, "signing_records"))
    if payload.rotate_matter_storage:
        rotations.append(matters.rotate_encryption_key(session.workspace_id, "matter_records"))
    if payload.rotate_document_storage:
        rotations.append(documents.rotate_encryption_key(session.workspace_id, "document_records"))
    if payload.rotate_template_storage:
        rotations.append(templates.rotate_encryption_key(session.workspace_id, "template_records"))
    if not rotations:
        raise HTTPException(status_code=422, detail="at_least_one_legal_key_rotation_required")
    return {"ok": True, "rotations": rotations, "pre_rotation_recovery_bundle": recovery}


@router.post("/matters/list")
def list_matters(session: VerifiedAionFlowSession = Depends(require_legal_session)) -> dict[str, Any]:
    return {"ok": True, "matters": _matter_call(lambda: matter_service().list_matters(session.workspace_id))}


@router.post("/matters")
def create_matter(
    payload: MatterCreateInput,
    session: VerifiedAionFlowSession = Depends(require_legal_session),
) -> dict[str, Any]:
    return {"ok": True, "matter": _matter_call(lambda: matter_service().create_matter(
        session.workspace_id,
        title=payload.title,
        counterparty=payload.counterparty,
        matter_type=payload.matter_type,
        risk=payload.risk,
        summary=payload.summary,
        jurisdiction=payload.jurisdiction.model_dump(),
        actor_id=session.person_id,
    ))}


@router.post("/matters/{matter_id}/triage")
def triage_matter(
    matter_id: str,
    payload: MatterTriageInput,
    session: VerifiedAionFlowSession = Depends(require_legal_session),
) -> dict[str, Any]:
    return {"ok": True, "matter": _matter_call(lambda: matter_service().triage_matter(
        session.workspace_id,
        matter_id,
        actor_id=session.person_id,
        risk=payload.risk,
        status=payload.status,
        summary=payload.summary,
        jurisdiction=payload.jurisdiction.model_dump() if payload.jurisdiction else None,
    ))}


@router.post("/matters/{matter_id}/records-governance")
def update_matter_records_governance(
    matter_id: str,
    payload: RecordsGovernanceInput,
    session: VerifiedAionFlowSession = Depends(require_legal_session),
) -> dict[str, Any]:
    return {"ok": True, "matter": _matter_call(lambda: matter_service().update_records_governance(
        session.workspace_id, matter_id, actor_id=session.person_id,
        retain_until=payload.retain_until, legal_hold=payload.legal_hold,
        legal_hold_reason=payload.legal_hold_reason,
    ))}


@router.post("/matters/{matter_id}/links")
def link_matter_record(
    matter_id: str,
    payload: MatterLinkInput,
    session: VerifiedAionFlowSession = Depends(require_legal_session),
) -> dict[str, Any]:
    return {"ok": True, "matter": _matter_call(lambda: matter_service().link_record(
        session.workspace_id, matter_id, actor_id=session.person_id,
        record_type=payload.record_type, reference_id=payload.reference_id,
        label=payload.label, content_sha256=payload.content_sha256,
    ))}


@router.post("/matters/{matter_id}/obligations")
def create_matter_obligation(
    matter_id: str,
    payload: MatterObligationInput,
    session: VerifiedAionFlowSession = Depends(require_legal_session),
) -> dict[str, Any]:
    return {"ok": True, "matter": _matter_call(lambda: matter_service().add_obligation(
        session.workspace_id, matter_id, actor_id=session.person_id,
        title=payload.title, obligation_type=payload.obligation_type,
        due_at=payload.due_at, remind_at=payload.remind_at,
        owner_id=payload.owner_id, source_reference_id=payload.source_reference_id,
    ))}


@router.post("/matters/{matter_id}/obligations/{obligation_id}/status")
def update_matter_obligation(
    matter_id: str,
    obligation_id: str,
    payload: MatterObligationStatusInput,
    session: VerifiedAionFlowSession = Depends(require_legal_session),
) -> dict[str, Any]:
    return {"ok": True, "matter": _matter_call(lambda: matter_service().update_obligation(
        session.workspace_id, matter_id, obligation_id,
        actor_id=session.person_id, status=payload.status,
    ))}


@router.post("/matters/obligations/due")
def list_due_matter_obligations(
    payload: MatterDueObligationsInput,
    session: VerifiedAionFlowSession = Depends(require_legal_session),
) -> dict[str, Any]:
    return {"ok": True, "obligations": _matter_call(lambda: matter_service().due_obligations(
        session.workspace_id, as_of=payload.as_of,
    ))}


@router.post("/matters/{matter_id}/professional-escalations")
def create_matter_professional_escalation(
    matter_id: str,
    payload: MatterEscalationInput,
    session: VerifiedAionFlowSession = Depends(require_legal_session),
) -> dict[str, Any]:
    return {"ok": True, "matter": _matter_call(lambda: matter_service().create_professional_escalation(
        session.workspace_id, matter_id, actor_id=session.person_id,
        reason=payload.reason, urgency=payload.urgency,
        requested_professional=payload.requested_professional,
    ))}


@router.post("/matters/{matter_id}/export")
def export_matter(
    matter_id: str,
    session: VerifiedAionFlowSession = Depends(require_legal_session),
) -> Response:
    filename, body = _matter_call(lambda: matter_service().export_matter(
        session.workspace_id, matter_id, session.person_id,
    ))
    return Response(
        content=body, media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/matters/{matter_id}/delete")
def delete_matter(
    matter_id: str,
    payload: RecordDeletionInput,
    session: VerifiedAionFlowSession = Depends(require_legal_session),
) -> dict[str, Any]:
    return {"ok": True, "destruction_receipt": _matter_call(lambda: matter_service().destroy_matter(
        session.workspace_id, matter_id, actor_id=session.person_id,
        confirmation=payload.confirmation,
    ))}


@router.post("/documents/list")
def list_legal_documents(
    session: VerifiedAionFlowSession = Depends(require_legal_session),
) -> dict[str, Any]:
    return {"ok": True, "documents": _document_call(lambda: document_service().list_documents(session.workspace_id))}


@router.post("/documents")
def ingest_legal_document(
    payload: LegalDocumentIngestInput,
    session: VerifiedAionFlowSession = Depends(require_legal_session),
) -> dict[str, Any]:
    try:
        content = base64.b64decode(payload.data_base64, validate=True)
    except Exception:
        raise HTTPException(status_code=422, detail="document_base64_invalid") from None
    if payload.matter_id:
        _matter_call(lambda: matter_service().get_matter(session.workspace_id, payload.matter_id))
    document = _document_call(lambda: document_service().ingest(
        session.workspace_id, filename=payload.filename, media_type=payload.media_type,
        content=content, actor_id=session.person_id, matter_id=payload.matter_id,
    ))
    if payload.matter_id:
        _matter_call(lambda: matter_service().link_record(
            session.workspace_id, payload.matter_id, actor_id=session.person_id,
            record_type="DOCUMENT", reference_id=document["document_id"],
            label=document["filename"], content_sha256=document["content_sha256"],
        ))
    return {"ok": True, "document": document}


@router.post("/documents/{document_id}")
def get_legal_document(
    document_id: str,
    session: VerifiedAionFlowSession = Depends(require_legal_session),
) -> dict[str, Any]:
    return {"ok": True, "document": _document_call(
        lambda: document_service().get_document(session.workspace_id, document_id)
    )}


@router.post("/documents/{document_id}/classification")
def confirm_legal_document_classification(
    document_id: str,
    payload: LegalDocumentClassificationInput,
    session: VerifiedAionFlowSession = Depends(require_legal_session),
) -> dict[str, Any]:
    return {"ok": True, "document": _document_call(lambda: document_service().confirm_classification(
        session.workspace_id, document_id, actor_id=session.person_id, category=payload.category,
    ))}


@router.post("/documents/{document_id}/contract-review")
def review_legal_contract(
    document_id: str,
    session: VerifiedAionFlowSession = Depends(require_legal_session),
) -> dict[str, Any]:
    return {"ok": True, "review": _document_call(lambda: document_service().review_contract(
        session.workspace_id, document_id, actor_id=session.person_id,
    ))}


@router.post("/documents/{document_id}/compare")
def compare_legal_document_versions(
    document_id: str,
    payload: LegalDocumentComparisonInput,
    session: VerifiedAionFlowSession = Depends(require_legal_session),
) -> dict[str, Any]:
    return {"ok": True, "comparison": _document_call(lambda: document_service().compare_versions(
        session.workspace_id, payload.base_document_id, document_id, actor_id=session.person_id,
    ))}


@router.post("/documents/{document_id}/redlines")
def create_legal_document_redline(
    document_id: str,
    payload: LegalDocumentRedlineInput,
    session: VerifiedAionFlowSession = Depends(require_legal_session),
) -> dict[str, Any]:
    return {"ok": True, "redline": _document_call(lambda: document_service().create_redline(
        session.workspace_id, document_id, actor_id=session.person_id,
        finding_id=payload.finding_id, original_text=payload.original_text,
        proposed_text=payload.proposed_text, rationale=payload.rationale,
    ))}


@router.post("/documents/{document_id}/negotiation-positions")
def record_legal_negotiation_position(
    document_id: str,
    payload: LegalNegotiationPositionInput,
    session: VerifiedAionFlowSession = Depends(require_legal_session),
) -> dict[str, Any]:
    return {"ok": True, "position": _document_call(lambda: document_service().record_negotiation_position(
        session.workspace_id, document_id, actor_id=session.person_id,
        issue=payload.issue, business_position=payload.business_position,
        counterparty_position=payload.counterparty_position,
    ))}


@router.post("/documents/{document_id}/download")
def download_legal_document(
    document_id: str,
    session: VerifiedAionFlowSession = Depends(require_legal_session),
) -> Response:
    filename, media_type, content = _document_call(
        lambda: document_service().original(session.workspace_id, document_id)
    )
    safe_name = filename.replace('"', "_").replace("\r", "_").replace("\n", "_")
    return Response(
        content=content, media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{safe_name}"'},
    )


@router.post("/templates/list")
def list_legal_templates(
    session: VerifiedAionFlowSession = Depends(require_legal_session),
) -> dict[str, Any]:
    return {"ok": True, "templates": _template_call(
        lambda: template_service().list_templates(session.workspace_id)
    )}


@router.post("/templates")
def create_legal_template_draft(
    payload: LegalTemplateCreateInput,
    session: VerifiedAionFlowSession = Depends(require_legal_session),
) -> dict[str, Any]:
    return {"ok": True, "template": _template_call(lambda: template_service().create_draft(
        session.workspace_id, title=payload.title, template_type=payload.template_type,
        jurisdiction=payload.jurisdiction.model_dump(), content=payload.content,
        intended_use=payload.intended_use, actor_id=session.person_id,
        source_template_id=payload.source_template_id,
    ))}


@router.post("/templates/review-schedule")
def enforce_legal_template_review_schedule(
    payload: LegalTemplateReviewScheduleInput,
    session: VerifiedAionFlowSession = Depends(require_legal_session),
) -> dict[str, Any]:
    as_of = None
    if payload.as_of:
        try:
            as_of = datetime.fromisoformat(payload.as_of.replace("Z", "+00:00"))
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="template_review_as_of_invalid") from exc
        if as_of.tzinfo is None:
            raise HTTPException(status_code=422, detail="template_review_as_of_timezone_required")
    return {"ok": True, "review_schedule": _template_call(
        lambda: template_service().enforce_review_schedule(
            session.workspace_id, as_of=as_of, actor_id=session.person_id,
        )
    )}


@router.post("/templates/{template_id}")
def get_legal_template(
    template_id: str,
    session: VerifiedAionFlowSession = Depends(require_legal_session),
) -> dict[str, Any]:
    return {"ok": True, "template": _template_call(
        lambda: template_service().get_template(session.workspace_id, template_id)
    )}


@router.post("/templates/{template_id}/approve")
def approve_legal_template(
    template_id: str,
    payload: LegalTemplateApprovalInput,
    session: VerifiedAionFlowSession = Depends(require_legal_session),
) -> dict[str, Any]:
    return {"ok": True, "template": _template_call(lambda: template_service().approve(
        session.workspace_id, template_id, actor_id=session.person_id,
        expected_content_sha256=payload.expected_content_sha256,
        reviewer_name=payload.reviewer_name,
        reviewer_qualification=payload.reviewer_qualification,
        review_scope=payload.review_scope,
        approved_jurisdiction=payload.approved_jurisdiction,
        acknowledge_qualified_review=payload.acknowledge_qualified_review,
        review_interval_days=payload.review_interval_days,
    ))}


@router.post("/templates/{template_id}/renew-review")
def renew_legal_template_review(
    template_id: str,
    payload: LegalTemplateApprovalInput,
    session: VerifiedAionFlowSession = Depends(require_legal_session),
) -> dict[str, Any]:
    return {"ok": True, "template": _template_call(lambda: template_service().renew_review(
        session.workspace_id, template_id, actor_id=session.person_id,
        expected_content_sha256=payload.expected_content_sha256,
        reviewer_name=payload.reviewer_name,
        reviewer_qualification=payload.reviewer_qualification,
        review_scope=payload.review_scope,
        approved_jurisdiction=payload.approved_jurisdiction,
        acknowledge_qualified_review=payload.acknowledge_qualified_review,
        review_interval_days=payload.review_interval_days,
    ))}


@router.post("/templates/{template_id}/withdraw")
def withdraw_legal_template_for_change(
    template_id: str,
    payload: LegalTemplateWithdrawalInput,
    session: VerifiedAionFlowSession = Depends(require_legal_session),
) -> dict[str, Any]:
    return {"ok": True, "template": _template_call(
        lambda: template_service().withdraw_for_legal_change(
            session.workspace_id, template_id, actor_id=session.person_id,
            reason=payload.reason, legal_change_reference=payload.legal_change_reference,
            acknowledge_withdrawal=payload.acknowledge_withdrawal,
        )
    )}


@router.post("/templates/{template_id}/instantiate")
def instantiate_legal_template(
    template_id: str,
    payload: LegalTemplateInstantiateInput,
    session: VerifiedAionFlowSession = Depends(require_legal_session),
) -> dict[str, Any]:
    if payload.matter_id:
        _matter_call(lambda: matter_service().get_matter(session.workspace_id, payload.matter_id))
    instance = _template_call(lambda: template_service().instantiate(
        session.workspace_id, template_id, actor_id=session.person_id, values=payload.values,
    ))
    document = _document_call(lambda: document_service().ingest(
        session.workspace_id, filename=payload.filename, media_type="text/plain",
        content=instance["rendered_content"].encode("utf-8"), actor_id=session.person_id,
        matter_id=payload.matter_id,
    ))
    if payload.matter_id:
        _matter_call(lambda: matter_service().link_record(
            session.workspace_id, payload.matter_id, actor_id=session.person_id,
            record_type="DOCUMENT", reference_id=document["document_id"],
            label=document["filename"], content_sha256=document["content_sha256"],
        ))
    public_instance = {key: value for key, value in instance.items() if key != "rendered_content"}
    return {"ok": True, "instance": public_instance, "document": document}


@router.post("/list")
def list_envelopes(session: VerifiedAionFlowSession = Depends(require_legal_session)) -> dict[str, Any]:
    return {"ok": True, "envelopes": service().list_envelopes(session.workspace_id)}


@router.post("/envelopes")
def create_envelope(payload: EnvelopeCreate, session: VerifiedAionFlowSession = Depends(require_legal_session)) -> dict[str, Any]:
    envelope = _call(lambda: service().create_envelope(
        session.workspace_id, title=payload.title, document_content=payload.document_content,
        signers=[item.model_dump() for item in payload.signers], actor_id=session.person_id,
        expires_in_days=payload.expires_in_days,
        supersedes_envelope_id=payload.supersedes_envelope_id,
    ))
    return {"ok": True, "envelope": envelope}


@router.post("/envelopes/{envelope_id}/submit-approval")
def submit_approval(envelope_id: str, session: VerifiedAionFlowSession = Depends(require_legal_session)) -> dict[str, Any]:
    return {"ok": True, "envelope": _call(lambda: service().submit_for_approval(session.workspace_id, envelope_id, session.person_id))}


@router.post("/envelopes/{envelope_id}/approve")
def approve(envelope_id: str, payload: ApprovalInput, session: VerifiedAionFlowSession = Depends(require_legal_session)) -> dict[str, Any]:
    return {"ok": True, "envelope": _call(lambda: service().approve(session.workspace_id, envelope_id, session.person_id, payload.review_hash))}


@router.post("/envelopes/{envelope_id}/issue")
def issue(envelope_id: str, session: VerifiedAionFlowSession = Depends(require_legal_session)) -> dict[str, Any]:
    return {"ok": True, "envelope": _call(lambda: service().issue(session.workspace_id, envelope_id, session.person_id))}


@router.post("/envelopes/{envelope_id}/reminders")
def reminder(envelope_id: str, payload: ReminderInput, session: VerifiedAionFlowSession = Depends(require_legal_session)) -> dict[str, Any]:
    return {"ok": True, "envelope": _call(lambda: service().record_reminder(session.workspace_id, envelope_id, session.person_id, payload.signer_id))}


@router.post("/envelopes/{envelope_id}/void")
def void(envelope_id: str, payload: ReasonInput, session: VerifiedAionFlowSession = Depends(require_legal_session)) -> dict[str, Any]:
    return {"ok": True, "envelope": _call(lambda: service().void(session.workspace_id, envelope_id, session.person_id, payload.reason))}


@router.post("/envelopes/{envelope_id}/signed-copy-delivery")
def record_signed_copy_delivery(envelope_id: str, payload: CopyDeliveryInput, session: VerifiedAionFlowSession = Depends(require_legal_session)) -> dict[str, Any]:
    return {"ok": True, "envelope": _call(lambda: service().record_signed_copy_delivery(
        session.workspace_id, envelope_id, session.person_id, payload.signer_id, payload.delivery_reference,
    ))}


@router.post("/envelopes/{envelope_id}/delivery-outbox/queue")
def queue_signed_copy_deliveries(
    envelope_id: str,
    payload: SignedCopyDeliveryQueueInput,
    session: VerifiedAionFlowSession = Depends(require_legal_session),
) -> dict[str, Any]:
    return {"ok": True, "outbox": _call(lambda: service().queue_signed_copy_deliveries(
        session.workspace_id, envelope_id, actor_id=session.person_id,
        provider=payload.provider,
        acknowledge_external_send=payload.acknowledge_external_send,
    ))}


@router.post("/delivery-outbox/status")
def signed_copy_delivery_outbox_status(
    session: VerifiedAionFlowSession = Depends(require_legal_session),
) -> dict[str, Any]:
    return {"ok": True, "outbox": service().signed_copy_delivery_status(session.workspace_id)}


@router.post("/delivery-outbox/send")
def send_queued_signed_copies(
    payload: SignedCopyDeliveryRunInput,
    session: VerifiedAionFlowSession = Depends(require_legal_session),
) -> dict[str, Any]:
    return {"ok": True, "outbox": _call(lambda: service().send_queued_signed_copies(
        session.workspace_id, actor_id=session.person_id,
        acknowledge_external_send=payload.acknowledge_external_send,
        limit=payload.limit, force=payload.force,
    ))}


@router.post("/delivery-outbox/{delivery_id}/confirm")
def confirm_signed_copy_delivery(
    delivery_id: str,
    payload: SignedCopyDeliveryConfirmationInput,
    session: VerifiedAionFlowSession = Depends(require_legal_session),
) -> dict[str, Any]:
    return {"ok": True, **_call(lambda: service().confirm_signed_copy_delivery(
        session.workspace_id, delivery_id, actor_id=session.person_id,
        outcome=payload.outcome, provider_reference=payload.provider_reference,
    ))}


@router.post("/delivery-outbox/{delivery_id}/retry")
def retry_signed_copy_delivery(
    delivery_id: str,
    payload: SignedCopyDeliveryRetryInput,
    session: VerifiedAionFlowSession = Depends(require_legal_session),
) -> dict[str, Any]:
    return {"ok": True, "delivery": _call(lambda: service().retry_signed_copy_delivery(
        session.workspace_id, delivery_id, actor_id=session.person_id,
        reason=payload.reason,
        acknowledge_external_send=payload.acknowledge_external_send,
    ))}


@router.post("/delivery-outbox/refresh-microsoft-graph")
def refresh_microsoft_graph_delivery_receipts(
    payload: SignedCopyDeliveryReceiptRefreshInput,
    session: VerifiedAionFlowSession = Depends(require_legal_session),
) -> dict[str, Any]:
    return {"ok": True, "outbox": _call(lambda: service().refresh_microsoft_graph_delivery_receipts(
        session.workspace_id,
        actor_id=session.person_id,
        limit=payload.limit,
    ))}


@router.post("/envelopes/{envelope_id}/proof")
def document_proof(envelope_id: str, session: VerifiedAionFlowSession = Depends(require_legal_session)) -> dict[str, Any]:
    return {"ok": True, "proof": _call(lambda: service().document_proof(session.workspace_id, envelope_id))}


@router.post("/envelopes/{envelope_id}/proof/download")
def download_document_proof(
    envelope_id: str,
    session: VerifiedAionFlowSession = Depends(require_legal_session),
) -> Response:
    proof = _call(lambda: service().document_proof(session.workspace_id, envelope_id))
    body = json.dumps(proof, indent=2, sort_keys=True, ensure_ascii=False)
    safe_name = "".join(char for char in envelope_id if char.isalnum() or char in "-_")[:120]
    return Response(
        content=body,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}.tessaris-proof"'},
    )


@router.post("/envelopes/{envelope_id}/evidence-package/download")
def download_evidence_package(
    envelope_id: str,
    session: VerifiedAionFlowSession = Depends(require_legal_session),
) -> Response:
    filename, body = _call(lambda: service().build_evidence_package(
        session.workspace_id, envelope_id, session.person_id,
    ))
    return Response(
        content=body,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/envelopes/{envelope_id}/records-governance")
def update_envelope_records_governance(
    envelope_id: str,
    payload: RecordsGovernanceInput,
    session: VerifiedAionFlowSession = Depends(require_legal_session),
) -> dict[str, Any]:
    return {"ok": True, "envelope": _call(lambda: service().update_records_governance(
        session.workspace_id, envelope_id, actor_id=session.person_id,
        retain_until=payload.retain_until, legal_hold=payload.legal_hold,
        legal_hold_reason=payload.legal_hold_reason,
    ))}


@router.post("/envelopes/{envelope_id}/delete")
def delete_envelope(
    envelope_id: str,
    payload: RecordDeletionInput,
    session: VerifiedAionFlowSession = Depends(require_legal_session),
) -> dict[str, Any]:
    return {"ok": True, "destruction_receipt": _call(lambda: service().destroy_envelope(
        session.workspace_id, envelope_id, actor_id=session.person_id,
        confirmation=payload.confirmation,
    ))}


@router.post("/envelopes/{envelope_id}/history")
def document_history(
    envelope_id: str,
    session: VerifiedAionFlowSession = Depends(require_legal_session),
) -> dict[str, Any]:
    return {"ok": True, "history": _call(lambda: service().document_history(
        session.workspace_id, envelope_id,
    ))}


@router.post("/envelopes/{envelope_id}/lifecycle-notices")
def record_lifecycle_notice(
    envelope_id: str,
    payload: LifecycleNoticeInput,
    session: VerifiedAionFlowSession = Depends(require_legal_session),
) -> dict[str, Any]:
    return {"ok": True, "envelope": _call(lambda: service().record_lifecycle_notice(
        session.workspace_id,
        envelope_id,
        session.person_id,
        notice_type=payload.notice_type,
        reason=payload.reason,
        effective_at=payload.effective_at,
        reference=payload.reference,
        acknowledge_preserved_evidence=payload.acknowledge_preserved_evidence,
    ))}


@router.post("/envelopes/{envelope_id}/proof/submit")
def submit_document_proof(envelope_id: str, session: VerifiedAionFlowSession = Depends(require_legal_session)) -> dict[str, Any]:
    return {"ok": True, "proof": _call(lambda: service().submit_document_proof(session.workspace_id, envelope_id))}


@router.post("/envelopes/{envelope_id}/proof/verify")
def verify_document_proof(
    envelope_id: str,
    payload: ProofVerifyInput,
    session: VerifiedAionFlowSession = Depends(require_legal_session),
) -> dict[str, Any]:
    return {"ok": True, "verification": _call(lambda: service().verify_document_proof(
        session.workspace_id,
        envelope_id,
        payload.document_content,
        payload.trusted_validator_set_root,
    ))}


@router.post("/proof-outbox/status")
def proof_outbox_status(session: VerifiedAionFlowSession = Depends(require_legal_session)) -> dict[str, Any]:
    return {"ok": True, "outbox": service().proof_outbox_status(session.workspace_id)}


@router.post("/proof-outbox/retry")
def retry_document_proofs(
    payload: ProofRetryInput,
    session: VerifiedAionFlowSession = Depends(require_legal_session),
) -> dict[str, Any]:
    return {"ok": True, "outbox": _call(lambda: service().retry_document_proofs(
        session.workspace_id, limit=payload.limit,
    ))}


@router.get("/sign/{token}")
def signer_view(token: str, request: Request) -> dict[str, Any]:
    _require_public_signer_access(request, token, write=False)
    return {"ok": True, "signing": _call(lambda: service().signer_view(token))}


@router.post("/sign/{token}")
def sign(token: str, payload: SignInput, request: Request) -> dict[str, Any]:
    _require_public_signer_access(request, token, write=True)
    return {"ok": True, "envelope": _call(lambda: service().sign(
        token, payload.typed_name, payload.identity_email, payload.identity_code,
    ))}


@router.post("/sign/{token}/decline")
def decline(token: str, payload: ReasonInput, request: Request) -> dict[str, Any]:
    _require_public_signer_access(request, token, write=True)
    return {"ok": True, "envelope": _call(lambda: service().decline(token, payload.reason))}


@public_router.get("/legal-sign/{token}", response_class=HTMLResponse)
def signing_page(token: str) -> HTMLResponse:
    # The token remains in the path fragment used by this local signer surface;
    # the HTML never embeds document or signer data into executable markup.
    return HTMLResponse("""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Tessaris secure signing</title><style>body{margin:0;background:#f3f5f8;color:#172033;font:15px Inter,system-ui,sans-serif}.shell{max-width:860px;margin:42px auto;padding:0 20px}.card{background:#fff;border:1px solid #d8e0e8;border-top:5px solid #7c3f63;padding:28px;box-shadow:0 18px 45px rgba(20,30,45,.08)}.eyebrow{color:#7c3f63;font-size:11px;font-weight:900;letter-spacing:.16em}.meta{display:flex;gap:18px;flex-wrap:wrap;color:#64748b;font-size:12px}.document{white-space:pre-wrap;border:1px solid #dce3ea;background:#fafbfc;padding:24px;margin:22px 0;max-height:48vh;overflow:auto;line-height:1.6}.form{display:grid;gap:12px}.field{display:grid;gap:5px;font-size:12px;font-weight:800}.field input,.field textarea{padding:12px;border:1px solid #aeb9c5;font:inherit}.actions{display:flex;gap:8px;justify-content:flex-end}.button{padding:11px 16px;border:1px solid #7c3f63;background:#fff;color:#6b3154;font-weight:850;cursor:pointer}.primary{background:#7c3f63;color:#fff}.notice{border:1px solid #e5c56c;background:#fff9e8;padding:12px;margin:18px 0;font-size:12px}.done{padding:22px;background:#edf9f1;color:#216e39;border:1px solid #a9dfbb}body.busy button{opacity:.55;pointer-events:none}</style></head><body><main class="shell"><div class="card"><div class="eyebrow">TESSARIS · SECURE SIGNING</div><h1 id="title">Loading document…</h1><div class="meta"><span id="signer"></span><span id="expiry"></span><span id="hash"></span></div><div class="notice">Review the complete document before signing. Your signature is bound to the exact document hash shown here.</div><article class="document" id="document"></article><form class="form" id="form"><label class="field">Type your full name exactly<input id="name" required autocomplete="name"></label><label class="field">Confirm your email<input id="email" required type="email" autocomplete="email"></label><label class="field" id="code-field" hidden>Enter the code delivered through the separate channel<input id="code" autocomplete="one-time-code"></label><div class="actions"><button class="button" type="button" id="decline">Decline</button><button class="button primary">Sign this exact version</button></div></form><div id="result"></div></div></main><script>const token=location.pathname.split('/').pop();const api='/api/aion/business/legal-signing/sign/'+encodeURIComponent(token);const text=(id,value)=>document.getElementById(id).textContent=value;async function load(){const r=await fetch(api);const v=await r.json();if(!r.ok)throw Error(v.detail||'This signing link is unavailable.');const s=v.signing;text('title',s.title);text('signer','Signer: '+s.signer.name+' · '+s.signer.role);text('expiry','Expires: '+new Date(s.expires_at).toLocaleString());text('hash','Document hash: '+s.document.content_hash.slice(0,16)+'…');text('document',s.document.content);document.getElementById('name').value=s.signer.name;document.getElementById('email').value=s.signer.email;if(s.signer.verification_method==='separate_channel_code'){document.getElementById('code-field').hidden=false;document.getElementById('code').required=true}if(!s.can_sign){document.getElementById('form').remove();text('result','This signer is waiting for an earlier signer or has already completed their action.')}}async function act(path,body){document.body.classList.add('busy');try{const r=await fetch(api+path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});const v=await r.json();if(!r.ok)throw Error(v.detail||'Action failed');document.getElementById('form')?.remove();document.getElementById('result').className='done';text('result',v.envelope.status==='COMPLETED'?'Signed. The completed copy and evidence manifest are now sealed.':'Your action was recorded in the tamper-evident history.')}catch(e){alert(e.message)}finally{document.body.classList.remove('busy')}}document.getElementById('form').addEventListener('submit',e=>{e.preventDefault();act('',{typed_name:document.getElementById('name').value,identity_email:document.getElementById('email').value,identity_code:document.getElementById('code').value})});document.getElementById('decline').addEventListener('click',()=>{const reason=prompt('Reason for declining (optional)')||'';act('/decline',{reason})});load().catch(e=>{text('title','Signing link unavailable');text('document',e.message);document.getElementById('form').remove()});</script></body></html>""")


@public_router.get("/legal-proof-verifier", response_class=HTMLResponse)
def legal_proof_verifier() -> HTMLResponse:
    from pathlib import Path

    path = Path(__file__).resolve().parents[1] / "static" / "tessaris-proof-verifier.html"
    return HTMLResponse(path.read_text(encoding="utf-8"))
