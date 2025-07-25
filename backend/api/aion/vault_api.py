# backend/modules/glyphvault/vault_api.py

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional

from backend.modules.glyphvault.vault_manager import VAULT

router = APIRouter()

class VaultSaveRequest(BaseModel):
    container_id: str
    associated_data: Optional[str] = None  # Optional hex string for associated auth data

class VaultRestoreRequest(BaseModel):
    filename: str
    associated_data: Optional[str] = None  # Optional hex string

class VaultDeleteRequest(BaseModel):
    filename: str

@router.post("/vault/save")
def save_container_snapshot(request: VaultSaveRequest):
    try:
        assoc_data = bytes.fromhex(request.associated_data) if request.associated_data else None
        filename = VAULT.save_snapshot(request.container_id, assoc_data)
        return {"status": "success", "filename": filename}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to save snapshot: {str(e)}")

@router.get("/vault/list")
def list_snapshots(container_id: Optional[str] = Query(None)) -> dict:
    try:
        snapshots = VAULT.list_snapshots(container_id)
        return {"snapshots": snapshots}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list snapshots: {str(e)}")

@router.post("/vault/restore")
def restore_container_snapshot(request: VaultRestoreRequest):
    try:
        assoc_data = bytes.fromhex(request.associated_data) if request.associated_data else None
        success = VAULT.load_snapshot(request.filename, assoc_data)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to restore snapshot (decryption or loading error)")
        return {"status": "success", "message": f"Snapshot '{request.filename}' restored successfully."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to restore snapshot: {str(e)}")

@router.delete("/vault/delete")
def delete_snapshot(request: VaultDeleteRequest):
    try:
        success = VAULT.delete_snapshot(request.filename)
        if not success:
            raise HTTPException(status_code=404, detail=f"Snapshot '{request.filename}' not found.")
        return {"status": "success", "message": f"Snapshot '{request.filename}' deleted successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete snapshot: {str(e)}")