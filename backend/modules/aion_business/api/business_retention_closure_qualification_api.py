"""Authenticated discovery-only journey 28 endpoint."""

from __future__ import annotations

import hmac
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from backend.modules.aion_business.runtime.business_retention_closure import BusinessRetentionClosureService
from backend.modules.aion_business.runtime.business_vault_runtime import configured_business_vault_runtime


class RetentionClosureRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    workspace_id: str = Field(min_length=1, max_length=120)
    closure_id: str = Field(default="journey28", min_length=1, max_length=120)
    reauthentication_verified: bool
    confirmation_phrase: str = Field(min_length=1, max_length=256)


def create_business_retention_closure_qualification_router(
    *, customer_export_path: str | Path, backup_snapshot_path: str | Path, access_token: str
) -> APIRouter:
    expected = str(access_token or "")
    if len(expected) < 32:
        raise ValueError("retention_closure_qualification_token_invalid")
    router = APIRouter(
        prefix="/api/aion/business/discovery-runtime/retention-closure",
        tags=["aion-business-discovery-retention-closure"],
    )

    @router.post("/qualify")
    def qualify(
        request: RetentionClosureRequest,
        x_tessaris_discovery_token: str | None = Header(default=None),
    ) -> dict[str, Any]:
        if not hmac.compare_digest(str(x_tessaris_discovery_token or ""), expected):
            raise HTTPException(status_code=403, detail="discovery_access_denied")
        try:
            result = BusinessRetentionClosureService(
                configured_business_vault_runtime()
            ).preview(
                workspace_id=request.workspace_id,
                closure_id=request.closure_id,
                customer_export_path=customer_export_path,
                backup_snapshot_path=backup_snapshot_path,
                reauthentication_verified=request.reauthentication_verified,
                confirmation_phrase=request.confirmation_phrase,
            )
            return {
                "ok": True,
                "closure": result,
                "customer_content_in_response": False,
                "release_scope": "discovery_qualification_only",
            }
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except (ValueError, RuntimeError, FileNotFoundError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return router
