"""Authenticated discovery-only journey 26 recovery endpoint."""

from __future__ import annotations

import base64
import hmac
import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from backend.modules.aion_business.runtime.business_vault_recovery_qualification import (
    BusinessVaultRecoveryQualificationService,
)
from backend.modules.aion_business.runtime.business_vault_runtime import configured_business_vault_runtime


class RecoveryQualificationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    workspace_id: str = Field(min_length=1, max_length=120)
    snapshot_id: str = Field(default="journey26", min_length=1, max_length=120)


def _key(value: str, error: str) -> bytes:
    try:
        decoded = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    except (TypeError, ValueError) as exc:
        raise ValueError(error) from exc
    if len(decoded) != 32:
        raise ValueError(error)
    return decoded


def create_business_vault_recovery_qualification_router(
    *, staging_root: str | Path, access_token: str
) -> APIRouter:
    expected = str(access_token or "")
    if len(expected) < 32:
        raise ValueError("recovery_qualification_token_invalid")
    root = Path(staging_root).resolve(strict=False)
    router = APIRouter(
        prefix="/api/aion/business/discovery-runtime/backup-recovery",
        tags=["aion-business-discovery-backup-recovery"],
    )

    @router.post("/qualify")
    def qualify(
        request: RecoveryQualificationRequest,
        x_tessaris_discovery_token: str | None = Header(default=None),
    ) -> dict[str, Any]:
        if not hmac.compare_digest(str(x_tessaris_discovery_token or ""), expected):
            raise HTTPException(status_code=403, detail="discovery_access_denied")
        snapshot_key_path = root / "snapshot-encryption.key"
        snapshot_key_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if snapshot_key_path.exists():
            snapshot_key = snapshot_key_path.read_bytes()
        else:
            snapshot_key = os.urandom(32)
            snapshot_key_path.write_bytes(snapshot_key)
            os.chmod(snapshot_key_path, 0o600)
        service = BusinessVaultRecoveryQualificationService(
            configured_business_vault_runtime(),
            vault_encryption_key=_key(
                os.environ.get("TESSARIS_BUSINESS_VAULT_KEY_B64", ""),
                "recovery_vault_key_invalid",
            ),
            snapshot_encryption_key=snapshot_key,
            staging_root=root,
            business_stable_id=os.environ["TESSARIS_BUSINESS_STABLE_ID"],
        )
        try:
            return {
                "ok": True,
                "recovery": service.run(
                    workspace_id=request.workspace_id, snapshot_id=request.snapshot_id
                ),
                "external_classes_staged": ["backup_destination", "secret_store"],
                "release_scope": "discovery_qualification_only",
            }
        except (RuntimeError, VaultSnapshotError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return router
