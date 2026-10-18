"""Authenticated discovery-only journey 25 composition endpoint."""

from __future__ import annotations

import hmac
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from backend.modules.aion_business.runtime.business_vault_portable_transfer import (
    BusinessVaultPortableExportService,
    BusinessVaultPortableTransferError,
    LegacyBusinessImportService,
)
from backend.modules.aion_business.runtime.business_vault_runtime import (
    configured_business_vault_runtime,
)


class PortableTransferQualificationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    workspace_id: str = Field(min_length=1, max_length=120)
    migration_id: str = Field(default="journey25", min_length=1, max_length=120)
    export_id: str = Field(default="journey25-whole-business", min_length=1, max_length=120)
    passphrase: str = Field(min_length=16, max_length=512)


def create_business_vault_portable_transfer_qualification_router(
    *, source_root: str | Path, export_root: str | Path, access_token: str,
) -> APIRouter:
    expected = str(access_token or "")
    if len(expected) < 32:
        raise ValueError("portable_transfer_qualification_token_invalid")
    source = Path(source_root).resolve(strict=False)
    exports = Path(export_root).resolve(strict=False)
    router = APIRouter(
        prefix="/api/aion/business/discovery-runtime/import-export-migration",
        tags=["aion-business-discovery-import-export-migration"],
    )

    def authorize(value: str | None) -> None:
        supplied = str(value or "")
        if not hmac.compare_digest(supplied, expected):
            raise HTTPException(status_code=403, detail="discovery_access_denied")

    @router.post("/qualify")
    def qualify(
        request: PortableTransferQualificationRequest,
        x_tessaris_discovery_token: str | None = Header(default=None),
    ) -> dict[str, Any]:
        authorize(x_tessaris_discovery_token)
        try:
            runtime = configured_business_vault_runtime()
            importer = LegacyBusinessImportService(runtime)
            dry_run = importer.inspect(
                source_root=source, migration_id=request.migration_id
            )
            imported = importer.execute(
                workspace_id=request.workspace_id,
                source_root=source,
                migration_id=request.migration_id,
            )
            exporter = BusinessVaultPortableExportService(runtime)
            export_path = exporter.create_export(
                workspace_id=request.workspace_id,
                export_id=request.export_id,
                destination_root=exports,
                passphrase=request.passphrase,
            )
            readback = exporter.summary(
                exporter.readback(export_path=export_path, passphrase=request.passphrase)
            )
            return {
                "ok": True,
                "dry_run": {
                    key: value
                    for key, value in dry_run.items()
                    if not str(key).startswith("_")
                },
                "import": imported,
                "export": {
                    "file_name": export_path.name,
                    "owner_private": export_path.stat().st_mode & 0o777 == 0o600,
                    **readback,
                },
                "legacy_source_retained": imported["source_retained"],
                "customer_content_in_response": False,
                "release_scope": "discovery_qualification_only",
            }
        except BusinessVaultPortableTransferError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail="legacy_source_not_prepared") from exc

    return router
