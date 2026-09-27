from __future__ import annotations

import os
import hashlib
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from backend.modules.vault.connector_readiness import ConnectorReadinessService
from backend.modules.vault.credential_schema import gmail_oauth_credential
from backend.modules.vault.credential_store import InMemoryVaultCredentialStore
from backend.api.local_node_router import get_runtime
from backend.modules.connectors.business_integration_catalog import get_business_integration_catalog


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


class LocalModelSelectionRequest(BaseModel):
    workspace_id: str = Field(default="home-fixed", min_length=1, max_length=160)
    model_id: str = Field(min_length=1, max_length=200)


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


@router.get("/integration-providers")
def list_integration_providers(
    business_id: str = "costa-conexion",
    workspace_id: str = "costa-conexion",
    owner_user_id: str = "local_user",
) -> Dict[str, Any]:
    """Return a safe, truthful view of business integrations for the Vault UI."""

    catalog = get_business_integration_catalog()
    gmail = gmail_status(
        business_id=business_id,
        workspace_id=workspace_id,
        owner_user_id=owner_user_id,
    ).get("gmail", {})
    providers = []
    for item in catalog["providers"]:
        provider = dict(item)
        if provider["provider_id"] == "gmail":
            provider["connected"] = bool(gmail.get("ready"))
            provider["configured"] = provider["connected"]
            provider["connection_reason"] = gmail.get("reason") or "not_connected"
        provider["available_to_connect"] = provider["implementation"] in {
            "adapter_ready",
            "credential_ready",
            "sandbox_verified",
            "live_verified",
        }
        providers.append(provider)

    return {
        **catalog,
        "providers": providers,
        "connected_count": sum(bool(item["connected"]) for item in providers),
        "configured_count": sum(bool(item["configured"]) for item in providers),
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


def _local_model_workspace_selection(workspace_id: str) -> Dict[str, Any]:
    from backend.modules.aion_inference.local_model_selection_store import load_local_model_selection

    return load_local_model_selection(workspace_id)


@router.get("/local-models")
def list_local_models(workspace_id: str = "home-fixed") -> Dict[str, Any]:
    """Inventory local model cards without reading or exposing model weights."""
    from backend.modules.aion_inference.local_model_vault import LocalModelVault
    from backend.modules.aion_inference.local_model_selection_store import save_local_model_selection

    snapshot = LocalModelVault().snapshot()
    selected = _local_model_workspace_selection(workspace_id)
    selected_id = selected.get("model_id") or selected.get("model")
    snapshot["workspace_id"] = workspace_id
    snapshot["selected_model_id"] = selected_id if selected.get("source") == "local_model_vault" else None
    for model in snapshot.get("models") or []:
        if isinstance(model, dict):
            model["selected"] = bool(model.get("model_id") == snapshot["selected_model_id"])
    return snapshot


@router.post("/local-models/select")
def select_local_model(
    payload: LocalModelSelectionRequest,
    x_aion_vault_intent: str = Header(default=""),
) -> Dict[str, Any]:
    """Bind one verified local package to a workspace and start its loopback runtime."""
    if x_aion_vault_intent != "select-local-model-v1":
        raise HTTPException(status_code=403, detail="explicit_vault_intent_required")
    from backend.modules.aion_business.runtime.business_container_repository import BusinessContainerRepository
    from backend.modules.aion_fabric.canonical import utc_now_iso
    from backend.modules.aion_inference.local_model_vault import LocalModelVault
    from backend.services.aion_mission_mode.pilot_local_model_runtime import (
        ensure_selected_local_runtime,
        selected_local_runtime_profile,
    )

    snapshot = LocalModelVault().snapshot()
    model = next(
        (item for item in snapshot.get("models") or []
         if isinstance(item, dict) and item.get("model_id") == payload.model_id),
        None,
    )
    installation = next(
        (item for item in (model or {}).get("installations") or []
         if isinstance(item, dict) and item.get("selectable") is True),
        None,
    )
    if not model or model.get("selection_status") != "selectable" or not installation:
        raise HTTPException(status_code=409, detail="local_model_package_not_mounted_or_verified")
    model_path = Path(str(installation.get("model_path") or "")).resolve()
    if not model_path.is_file():
        raise HTTPException(status_code=409, detail="local_model_weight_file_missing")
    digest = hashlib.sha256()
    with model_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    expected_hash = str(installation.get("model_sha256") or "").lower()
    if digest.hexdigest() != expected_hash:
        raise HTTPException(status_code=409, detail="local_model_weight_hash_mismatch")
    runtime_values = {
        **dict(model.get("runtime_profile") or {}),
        **dict(installation.get("runtime_profile") or {}),
    }
    runtime_profile = selected_local_runtime_profile(
        model_id=payload.model_id,
        adapter=str(runtime_values.get("adapter") or ""),
        endpoint=str(runtime_values.get("endpoint") or ""),
        model_sha256=expected_hash,
        model_path=str(model_path),
        finance_arithmetic=str(runtime_values.get("finance_arithmetic") or ""),
        chat_template_kwargs=runtime_values.get("chat_template_kwargs"),
        max_output_tokens=runtime_values.get("max_output_tokens"),
        context_size=runtime_values.get("context_size"),
        parallel_slots=runtime_values.get("parallel_slots"),
    )
    runtime_status = ensure_selected_local_runtime(runtime_profile)
    repository = BusinessContainerRepository()
    workspace = repository.load_optional_dict(payload.workspace_id, "operational_runtime_summary") or {
        "workspace_id": payload.workspace_id,
        "kind": "operational_runtime_summary",
    }
    selection = {
        "provider": "local_model", "provider_id": "local_model",
        "model": payload.model_id, "model_id": payload.model_id,
        "source": "local_model_vault", "selection_status": "selectable",
        "release_status": model.get("release_status"),
        "binding_ref": installation.get("warehouse", {}).get("sha256"),
        "storage_root": installation.get("storage_root"),
        "selected_at": utc_now_iso(),
    }
    save_local_model_selection(payload.workspace_id, selection)
    # Retain the compatibility projection for older clients. The dedicated Vault
    # record above is authoritative and cannot be erased by briefing updates.
    workspace["coo_model_selection"] = selection
    repository.save_dict(payload.workspace_id, "operational_runtime_summary", workspace)
    return {
        "ok": True, "workspace_id": payload.workspace_id, "selection": selection,
        "runtime": runtime_status,
    }


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
