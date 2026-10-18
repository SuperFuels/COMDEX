"""Authenticated discovery-only journey 27 endpoint."""

from __future__ import annotations

import hmac
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from backend.modules.aion_business.runtime.business_vault_runtime import configured_business_vault_runtime
from backend.modules.aion_business.runtime.diagnostic_support_handoff import DiagnosticSupportHandoffService


class DiagnosticSupportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    workspace_id: str = Field(min_length=1, max_length=120)
    handoff_id: str = Field(default="journey27", min_length=1, max_length=120)
    customer_approved: bool = False
    approved_by: str = Field(default="", max_length=120)


def create_diagnostic_support_qualification_router(
    *, staging_root: str | Path, access_token: str
) -> APIRouter:
    expected = str(access_token or "")
    if len(expected) < 32:
        raise ValueError("diagnostic_support_qualification_token_invalid")
    root = Path(staging_root).resolve(strict=False)
    router = APIRouter(
        prefix="/api/aion/business/discovery-runtime/logs-diagnostics-support",
        tags=["aion-business-discovery-logs-diagnostics-support"],
    )

    @router.post("/qualify")
    def qualify(
        request: DiagnosticSupportRequest,
        x_tessaris_discovery_token: str | None = Header(default=None),
    ) -> dict[str, Any]:
        if not hmac.compare_digest(str(x_tessaris_discovery_token or ""), expected):
            raise HTTPException(status_code=403, detail="discovery_access_denied")
        service = DiagnosticSupportHandoffService(
            configured_business_vault_runtime(),
            diagnostics_root=root / "node-diagnostics",
            export_root=root / "customer-exports",
        )
        failure = service.exercise_failure(failure_id=request.handoff_id)
        result = service.prepare(
            workspace_id=request.workspace_id,
            handoff_id=request.handoff_id,
            failure=failure,
            customer_approved=request.customer_approved,
            approved_by=request.approved_by,
        )
        return {
            "ok": True,
            "handoff": result,
            "customer_content_in_response": False,
            "release_scope": "discovery_qualification_only",
        }

    return router
