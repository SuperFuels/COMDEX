from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from backend.modules.vault.connector_readiness import ConnectorReadinessService
from backend.modules.vault.credential_schema import gmail_oauth_credential
from backend.modules.vault.credential_store import InMemoryVaultCredentialStore
from backend.api.local_node_router import get_runtime


router = APIRouter(prefix="/api/vault", tags=["vault"])

_STORE = InMemoryVaultCredentialStore()


class VaultCredentialSeedRequest(BaseModel):
    business_id: str = "costa-conexion"
    workspace_id: str = "costa-conexion"
    owner_user_id: str = "local_user"
    department_id: Optional[str] = None
    connector_id: str = "gmail"
    connected: bool = False
    secret_ref: Optional[str] = None


class ConnectorReadinessRequest(BaseModel):
    business_id: str = "costa-conexion"
    workspace_id: str = "costa-conexion"
    owner_user_id: str = "local_user"
    connector_id: str = "gmail"
    credential_key: str = "vault.gmail.credentials"
    required_scopes: list[str] = Field(default_factory=list)


@router.get("/credentials")
def list_credentials(
    business_id: str = "costa-conexion",
    workspace_id: str = "costa-conexion",
) -> Dict[str, Any]:
    records = _STORE.list_for_workspace(
        business_id=business_id,
        workspace_id=workspace_id,
    )

    return {
        "ok": True,
        "credentials": [record.safe_public_dict() for record in records],
    }


@router.post("/dev/seed-gmail")
def dev_seed_gmail_credential(payload: VaultCredentialSeedRequest) -> Dict[str, Any]:
    """
    Dev-only seed route for local desktop testing.

    This stores credential metadata and a secret_ref only. It does not store raw
    OAuth tokens, passwords, API keys, or refresh tokens.
    """

    if payload.connector_id != "gmail":
        return {
            "ok": False,
            "error": "only_gmail_seed_supported",
        }

    credential = gmail_oauth_credential(
        business_id=payload.business_id,
        workspace_id=payload.workspace_id,
        owner_user_id=payload.owner_user_id,
        department_id=payload.department_id,
        secret_ref=payload.secret_ref or (
            f"secret://gmail/{payload.business_id}/{payload.owner_user_id}"
            if payload.connected
            else None
        ),
        status="connected" if payload.connected else "missing",
    )

    _STORE.upsert(credential)

    return {
        "ok": True,
        "credential": credential.safe_public_dict(),
    }


@router.post("/connectors/readiness")
def check_connector_readiness(payload: ConnectorReadinessRequest) -> Dict[str, Any]:
    result = ConnectorReadinessService(_STORE).check(
        business_id=payload.business_id,
        workspace_id=payload.workspace_id,
        owner_user_id=payload.owner_user_id,
        connector_id=payload.connector_id,
        credential_key=payload.credential_key,
        required_scopes=payload.required_scopes,
    )

    return {
        "ok": True,
        "readiness": result.to_dict(),
    }


@router.get("/connectors/gmail/status")
def gmail_status(
    business_id: str = "costa-conexion",
    workspace_id: str = "costa-conexion",
    owner_user_id: str = "local_user",
) -> Dict[str, Any]:
    required_scopes = [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.compose",
    ]

    local_health: Dict[str, Any] = {}
    try:
        local_health = get_runtime().get_gmail_connector_health()
    except Exception as exc:
        local_health = {
            "ok": False,
            "auth_status": "unknown",
            "connector_health": "unknown",
            "last_error": str(exc),
        }

    local_connected = (
        local_health.get("auth_status") == "connected"
        and local_health.get("connector_health") == "available"
    )

    if local_connected:
        return {
            "ok": True,
            "gmail": {
                "ok": True,
                "connector_id": "gmail",
                "credential_key": "vault.gmail.credentials",
                "status": "connected",
                "ready": True,
                "reason": "local_node_gmail_connected",
                "required_scopes": required_scopes,
                "granted_scopes": required_scopes,
                "source": "local_node_gmail_health",
                "local_node": local_health,
            },
            "live_send_enabled": False,
            "dry_run_only": True,
            "external_writes_enabled": False,
        }

    result = ConnectorReadinessService(_STORE).check(
        business_id=business_id,
        workspace_id=workspace_id,
        owner_user_id=owner_user_id,
        connector_id="gmail",
        credential_key="vault.gmail.credentials",
        required_scopes=required_scopes,
    )

    return {
        "ok": True,
        "gmail": {
            **result.to_dict(),
            "source": "vault_metadata_store",
            "local_node": local_health,
        },
        "live_send_enabled": False,
        "dry_run_only": True,
        "external_writes_enabled": False,
    }
