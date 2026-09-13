from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from backend.modules.vault.connector_readiness import ConnectorReadinessService
from backend.modules.vault.credential_schema import gmail_oauth_credential
from backend.modules.vault.credential_store import InMemoryVaultCredentialStore
from backend.api.local_node_router import get_runtime


router = APIRouter(prefix="/api/vault", tags=["vault"])

_STORE = InMemoryVaultCredentialStore()


def _aion_flow_bindings():
    from backend.modules.aion_business.runtime.aion_flow_model_bindings import AionFlowModelBindings

    data_root = Path(os.environ.get("TESSARIS_DATA_ROOT") or os.environ.get("DATA_ROOT") or "data").resolve()
    return AionFlowModelBindings(data_root / "aion_flow" / "credential_bindings")


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


class AionFlowBindingCreateRequest(BaseModel):
    binding_id: str = Field(min_length=1, max_length=80)
    provider: str = Field(min_length=1, max_length=80)
    label: str = Field(default="", max_length=100)
    secret: str = Field(min_length=1, max_length=65536)


@router.get("/aion-flow/bindings")
def list_aion_flow_bindings(provider: str = "") -> Dict[str, Any]:
    """Return safe binding metadata for the visual picker; never secret material."""

    return {"ok": True, **_aion_flow_bindings().public_bindings(provider=provider)}


@router.post("/aion-flow/bindings")
def create_aion_flow_binding(
    payload: AionFlowBindingCreateRequest,
    x_aion_vault_intent: str = Header(default=""),
) -> Dict[str, Any]:
    """Move a user-entered secret straight into the encrypted mother vault."""

    if x_aion_vault_intent != "create-aion-flow-binding-v1":
        raise HTTPException(status_code=403, detail="explicit_vault_intent_required")
    try:
        binding = _aion_flow_bindings().create(
            binding_id=payload.binding_id,
            provider=payload.provider,
            secret=payload.secret,
            label=payload.label,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"ok": True, "binding": binding, "raw_secret_returned": False}


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


# AION PATCH: Vault AI Provider Keys v1
class AiProviderKeySaveRequest(BaseModel):
    api_key: str
    model: Optional[str] = None


@router.get("/ai-providers")
def list_ai_providers() -> Dict[str, Any]:
    from backend.modules.vault.ai_provider_key_store import list_ai_provider_public_records

    return {
        "ok": True,
        **list_ai_provider_public_records(),
    }


@router.get("/local-models")
def list_local_models() -> Dict[str, Any]:
    """Inventory local model cards without reading or exposing model weights."""
    from backend.modules.aion_inference.local_model_vault import LocalModelVault

    return LocalModelVault().snapshot()


@router.post("/ai-providers/{provider_id}")
def save_ai_provider_key(provider_id: str, payload: AiProviderKeySaveRequest) -> Dict[str, Any]:
    from backend.modules.vault.ai_provider_key_store import set_ai_provider_key

    try:
        record = set_ai_provider_key(
            provider_id=provider_id,
            api_key=payload.api_key,
            model=payload.model,
        )
    except ValueError as exc:
        return {
            "ok": False,
            "error": str(exc),
        }

    return {
        "ok": True,
        "provider": record,
    }


@router.delete("/ai-providers/{provider_id}")
def delete_ai_provider(provider_id: str) -> Dict[str, Any]:
    from backend.modules.vault.ai_provider_key_store import delete_ai_provider_key

    return {
        "ok": True,
        "provider": delete_ai_provider_key(provider_id),
    }
# END AION PATCH: Vault AI Provider Keys v1


class TwilioConnectionSaveRequest(BaseModel):
    account_sid: str
    api_key_sid: str
    api_key_secret: str
    from_number: str
    trunk_sid: str = ""
    termination_uri: str
    sip_username: str
    sip_password: str


class RetellConnectionSaveRequest(BaseModel):
    api_key: str


def _telephony_error(exc: Exception) -> HTTPException:
    if isinstance(exc, ValueError):
        return HTTPException(status_code=422, detail=str(exc))
    if isinstance(exc, PermissionError):
        return HTTPException(status_code=401, detail=str(exc))
    return HTTPException(status_code=503, detail=str(exc) or "telephony_connection_failed")


@router.get("/telephony/{workspace_id}")
def telephony_status(workspace_id: str) -> Dict[str, Any]:
    from backend.modules.aion_business.runtime.telephony_vault_service import TelephonyVaultService
    try:
        return TelephonyVaultService().status(workspace_id)
    except Exception as exc:
        raise _telephony_error(exc) from exc


@router.post("/telephony/{workspace_id}/twilio")
def save_twilio_connection(workspace_id: str, payload: TwilioConnectionSaveRequest) -> Dict[str, Any]:
    from backend.modules.aion_business.runtime.telephony_vault_service import TelephonyVaultService
    try:
        return TelephonyVaultService().save_twilio(workspace_id, payload.model_dump())
    except Exception as exc:
        raise _telephony_error(exc) from exc


@router.post("/telephony/{workspace_id}/retell")
def save_retell_connection(workspace_id: str, payload: RetellConnectionSaveRequest) -> Dict[str, Any]:
    from backend.modules.aion_business.runtime.telephony_vault_service import TelephonyVaultService
    try:
        return TelephonyVaultService().save_retell(workspace_id, payload.api_key)
    except Exception as exc:
        raise _telephony_error(exc) from exc


@router.post("/telephony/{workspace_id}/refresh")
def refresh_telephony_connection(workspace_id: str) -> Dict[str, Any]:
    from backend.modules.aion_business.runtime.telephony_vault_service import TelephonyVaultService
    try:
        return TelephonyVaultService().refresh(workspace_id)
    except Exception as exc:
        raise _telephony_error(exc) from exc
