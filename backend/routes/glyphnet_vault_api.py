from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import Optional, Dict, Any

from backend.modules.encryption.vault_exporter import export_container_vault
from backend.modules.encryption.vault_importer import import_encrypted_vault

router = APIRouter()


class VaultExportRequest(BaseModel):
    container_id: str
    target_id: Optional[str] = None


class VaultImportRequest(BaseModel):
    sender: str
    payload: str  # Encrypted string


@router.post("/glyphnet/vault/export")
async def vault_export(req: VaultExportRequest) -> Dict[str, Any]:
    """
    Exports a symbolic container vault and optionally encrypts it for the target.
    """
    return export_container_vault(req.container_id, req.target_id)


@router.post("/glyphnet/vault/import")
async def vault_import(req: VaultImportRequest) -> Dict[str, Any]:
    """
    Imports a symbolic container vault sent by another agent via GlyphPush.
    """
    data = {
        "sender": req.sender,
        "payload": req.payload
    }
    return import_encrypted_vault(data)