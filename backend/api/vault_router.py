from __future__ import annotations

import os
import hashlib
import secrets
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlencode

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from backend.modules.vault.connector_readiness import ConnectorReadinessService
from backend.modules.vault.credential_schema import gmail_oauth_credential
from backend.modules.vault.credential_store import InMemoryVaultCredentialStore
from backend.api.local_node_router import get_runtime
from backend.modules.connectors.business_integration_catalog import get_business_integration_catalog


router = APIRouter(prefix="/api/vault", tags=["vault"])

_STORE = InMemoryVaultCredentialStore()


def _aion_flow_bindings(workspace_id: str = "home-fixed"):
    from backend.modules.aion_business.runtime.aion_flow_model_bindings import AionFlowModelBindings
    from backend.modules.aion_business.runtime.business_vault_runtime import guardian_mode_requested
    from backend.modules.aion_business.runtime.business_vault_runtime import configured_business_vault_runtime
    from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore

    data_root = Path(os.environ.get("TESSARIS_DATA_ROOT") or os.environ.get("DATA_ROOT") or "data").resolve()
    domain_store = None
    credential_root = data_root / "aion_flow" / "credential_bindings"
    if guardian_mode_requested():
        runtime = configured_business_vault_runtime()
        domain_store = VaultDomainStore(
            runtime.guardian, actor_id="aion-flow-model-binding-api",
        )
        credential_root = Path(
            os.environ.get("TESSARIS_AION_FLOW_CREDENTIAL_STORE_PATH")
            or (
                Path(os.environ["TESSARIS_SECURITY_ROOT"])
                / "aion-flow-model-bindings"
                if os.environ.get("TESSARIS_SECURITY_ROOT")
                else Path.home()
                / ".tessaris/security/aion-flow-model-bindings"
            )
        ).expanduser().resolve()
    return AionFlowModelBindings(
        credential_root,
        workspace_id=workspace_id,
        domain_store=domain_store,
    )


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
    workspace_id: str = Field(default="home-fixed", min_length=1, max_length=160)
    binding_id: str = Field(min_length=1, max_length=80)
    provider: str = Field(min_length=1, max_length=80)
    label: str = Field(default="", max_length=100)
    secret: str = Field(min_length=1, max_length=65536)


class LocalModelSelectionRequest(BaseModel):
    workspace_id: str = Field(default="home-fixed", min_length=1, max_length=160)
    model_id: str = Field(min_length=1, max_length=200)


@router.get("/aion-flow/bindings")
def list_aion_flow_bindings(provider: str = "", workspace_id: str = "home-fixed") -> Dict[str, Any]:
    """Return safe binding metadata for the visual picker; never secret material."""

    return {"ok": True, **_aion_flow_bindings(workspace_id).public_bindings(provider=provider)}


@router.post("/aion-flow/bindings")
def create_aion_flow_binding(
    payload: AionFlowBindingCreateRequest,
    x_aion_vault_intent: str = Header(default=""),
) -> Dict[str, Any]:
    """Move a user-entered secret straight into the encrypted mother vault."""

    if x_aion_vault_intent != "create-aion-flow-binding-v1":
        raise HTTPException(status_code=403, detail="explicit_vault_intent_required")
    try:
        binding = _aion_flow_bindings(payload.workspace_id).create(
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


_PAYMENT_PROVIDER_DOCS = {
    "stripe": "https://docs.stripe.com/connect/oauth-reference",
    "paypal": "https://developer.paypal.com/platforms/seller-onboarding",
    "square": "https://developer.squareup.com/docs/oauth-api/overview",
    "gocardless": "https://docs.gocardless.com/getting-started/partners/connecting-your-users-accounts",
    "revolut": "https://developer.revolut.com/docs/api/merchant",
    "sumup": "https://developer.sumup.com/tools/authorization/oauth",
    "mollie": "https://docs.mollie.com/docs/authentication-via-oauth",
    "braintree": "https://developer.paypal.com/braintree/docs/guides/extend/oauth/overview",
    "worldpay": "https://docs.worldpay.com/access/products/get-started",
    "adyen": "https://docs.adyen.com/platforms/onboard-users",
    "checkout_com": "https://www.checkout.com/docs/docs/Integrate/partner-accreditation-guide.pdf",
}


@router.get("/payment-providers")
def list_payment_providers() -> Dict[str, Any]:
    """Expose payment-connector readiness without returning credentials."""

    catalog = get_business_integration_catalog()
    providers = []
    for item in catalog["providers"]:
        if item.get("category") != "payments":
            continue
        missing = list(item.get("missing_setup") or [])
        providers.append({
            **item,
            "developer_setup_ready": bool(item.get("configured")),
            "missing_setup": missing,
            "docs_url": _PAYMENT_PROVIDER_DOCS.get(str(item.get("provider_id")), ""),
            "connection_status": "ready_to_connect" if item.get("configured") else "developer_setup_required",
        })
    return {
        "ok": True,
        "schema_version": "tessaris.payment_connections.v1",
        "providers": providers,
        "bank_transfer_available": True,
        "customer_card_data_stored": False,
    }


@router.get("/payment-providers/{provider_id}/connect-url")
def payment_provider_connect_url(provider_id: str) -> Dict[str, Any]:
    """Create the provider-owned onboarding URL once platform credentials exist.

    Token exchange and webhook verification belong on Tessaris's HTTPS service;
    this local endpoint deliberately never accepts or exposes provider secrets.
    """

    provider = str(provider_id or "").strip().lower()
    catalog = {item["provider_id"]: item for item in get_business_integration_catalog()["providers"]}
    item = catalog.get(provider)
    if not item or item.get("category") != "payments":
        raise HTTPException(status_code=404, detail="payment_provider_not_found")
    if not item.get("configured"):
        return {
            "ok": False,
            "provider_id": provider,
            "reason": "developer_setup_required",
            "missing_setup": item.get("missing_setup") or item.get("required_setup") or [],
            "docs_url": _PAYMENT_PROVIDER_DOCS.get(provider, ""),
        }

    redirect_base = os.getenv("TESSARIS_PAYMENT_OAUTH_REDIRECT_URL", "").strip()
    redirect_uri = f"{redirect_base.rstrip('/')}/{provider}"
    state = secrets.token_urlsafe(32)
    if provider == "stripe":
        query = urlencode({
            "response_type": "code",
            "client_id": os.getenv("STRIPE_CONNECT_CLIENT_ID", ""),
            "scope": "read_write",
            "redirect_uri": redirect_uri,
            "state": state,
        })
        connect_url = f"https://connect.stripe.com/oauth/authorize?{query}"
    elif provider == "square":
        query = urlencode({
            "client_id": os.getenv("SQUARE_APPLICATION_ID", ""),
            "scope": "MERCHANT_PROFILE_READ ORDERS_READ ORDERS_WRITE PAYMENTS_READ PAYMENTS_WRITE",
            "session": "false",
            "redirect_uri": redirect_uri,
            "state": state,
        })
        connect_url = f"https://connect.squareup.com/oauth2/authorize?{query}"
    elif provider == "gocardless":
        query = urlencode({
            "client_id": os.getenv("GOCARDLESS_CLIENT_ID", ""),
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "read_write",
            "state": state,
        })
        connect_url = f"https://connect.gocardless.com/oauth/authorize?{query}"
    elif provider == "sumup":
        query = urlencode({
            "response_type": "code",
            "client_id": os.getenv("SUMUP_CLIENT_ID", ""),
            "redirect_uri": redirect_uri,
            "scope": "payments",
            "state": state,
        })
        connect_url = f"https://api.sumup.com/authorize?{query}"
    elif provider == "mollie":
        query = urlencode({
            "client_id": os.getenv("MOLLIE_CLIENT_ID", ""),
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "payments.read payments.write payment-links.read payment-links.write",
            "state": state,
        })
        connect_url = f"https://www.mollie.com/oauth2/authorize?{query}"
    elif provider == "revolut":
        return {
            "ok": False,
            "provider_id": provider,
            "reason": "revolut_merchant_account_required",
            "docs_url": _PAYMENT_PROVIDER_DOCS["revolut"],
        }
    elif provider in {"braintree", "worldpay", "adyen", "checkout_com"}:
        reasons = {
            "braintree": "braintree_production_oauth_approval_required",
            "worldpay": "worldpay_implementation_manager_setup_required",
            "adyen": "adyen_platform_account_required",
            "checkout_com": "checkout_partner_accreditation_required",
        }
        return {
            "ok": False,
            "provider_id": provider,
            "reason": reasons[provider],
            "docs_url": _PAYMENT_PROVIDER_DOCS[provider],
        }
    else:
        # PayPal merchant onboarding is created through Partner Referrals and
        # requires an approved partner account; there is no safe static URL.
        return {
            "ok": False,
            "provider_id": provider,
            "reason": "paypal_partner_referral_required",
            "docs_url": _PAYMENT_PROVIDER_DOCS["paypal"],
        }
    return {"ok": True, "provider_id": provider, "connect_url": connect_url, "state": state}


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
