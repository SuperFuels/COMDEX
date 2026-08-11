from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
import asyncio
from hashlib import sha256
import base64
import json
import os
from pathlib import Path
import secrets
from typing import Any, Dict
from urllib.parse import quote, urlencode

import httpx
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from backend.modules.aion_business.contracts.business_containers import (
    BusinessContainerMeta,
    BusinessFinancialModelContainer,
)
from backend.modules.aion_business.runtime.business_container_repository import BusinessContainerRepository
from backend.modules.aion_business.runtime.canonical_business_identity import canonical_business_id
from backend.modules.aion_business.runtime.paths import AIONBusinessPaths
from backend.modules.aion_business.runtime.finance_inbox_service import FinanceInboxService
from backend.modules.aion_business.runtime.workflow_file_cabinet_repository import (
    WorkflowFileCabinetRepository,
)
from backend.modules.aion_business.runtime.xero_bookkeeping_export_service import XeroBookkeepingExportService
from backend.modules.aion_business.runtime.xero_supplier_contact_service import XeroSupplierContactService
from backend.modules.aion_business.runtime.xero_sales_invoice_export_service import XeroSalesInvoiceExportService


router = APIRouter(prefix="/api/aion/integrations", tags=["aion-finance-integrations"])

XERO_AUTHORIZE_URL = "https://login.xero.com/identity/connect/authorize"
XERO_TOKEN_URL = "https://identity.xero.com/connect/token"
XERO_CONNECTIONS_URL = "https://api.xero.com/connections"
XERO_ACCOUNTING_BASE = "https://api.xero.com/api.xro/2.0"
XERO_PROJECTS_BASE = "https://api.xero.com/projects.xro/2.0"
XERO_KEYCHAIN_SERVICE = "com.tessaris.aion.xero"
XERO_SCOPES = [
    "offline_access",
    "accounting.settings.read",
    "accounting.contacts",
    "accounting.invoices",
    "accounting.payments",
    "accounting.banktransactions",
    "accounting.manualjournals",
    "accounting.attachments",
    "accounting.reports.profitandloss.read",
    "accounting.reports.balancesheet.read",
    "accounting.reports.banksummary.read",
    "projects.read",
]
XERO_WRITE_SCOPES = {
    "accounting.contacts",
    "accounting.invoices", "accounting.payments", "accounting.banktransactions",
    "accounting.manualjournals", "accounting.attachments",
}


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _hash(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)
    return "sha256:" + sha256(raw.encode("utf-8")).hexdigest()


def _integration_dir(business_id: str) -> Path:
    path = AIONBusinessPaths.business_container_dir(business_id) / "integrations" / "xero"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _connection_path(business_id: str) -> Path:
    return _integration_dir(business_id) / "connection.json"


def _read_json(path: Path, fallback: Any) -> Any:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value
    except Exception:
        return fallback


def _write_json(path: Path, payload: Any, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8")
    try:
        path.chmod(mode)
    except OSError:
        pass


def _record_connector_attempt(
    business_id: str | None,
    *,
    operation: str,
    status: str,
    attempt: int,
    provider_status: int | None = None,
    retryable: bool = False,
    error_code: str | None = None,
    error_type: str | None = None,
) -> Dict[str, Any] | None:
    """Persist a secret-free connector receipt and File Cabinet pointer."""
    if not business_id:
        return None
    business_id = canonical_business_id(business_id)
    occurred_at = _now()
    receipt_id = f"xero_{datetime.now(UTC).strftime('%Y%m%dT%H%M%S%fZ')}_{secrets.token_hex(3)}"
    receipt = {
        "schema_version": "aion.connector_attempt_receipt.v1",
        "receipt_id": receipt_id,
        "business_id": business_id,
        "department_id": "finance",
        "provider": "xero",
        "operation": operation,
        "status": status,
        "attempt": attempt,
        "provider_status": provider_status,
        "retryable": retryable,
        "error_code": error_code,
        "error_type": error_type,
        "occurred_at": occurred_at,
        "external_write_performed": False,
        "contains_credentials": False,
    }
    receipt["receipt_hash"] = _hash(receipt)
    path = _integration_dir(business_id) / "receipts" / f"{receipt_id}.json"
    _write_json(path, receipt)
    tree = WorkflowFileCabinetRepository.load(business_id)
    folders = tree.get("folders") or (tree.get("root") or {}).get("children") or []
    finance = next((item for item in folders if item.get("id") == "folder_finance"), None)
    if finance is None:
        finance = {"id": "folder_finance", "name": "Finance", "type": "department", "children": []}
        folders.append(finance)
    children = finance.setdefault("children", [])
    receipt_folder = next((item for item in children if item.get("id") == "folder_finance_connector_receipts"), None)
    if receipt_folder is None:
        receipt_folder = {"id": "folder_finance_connector_receipts", "name": "Connector Receipts", "type": "folder", "children": []}
        children.append(receipt_folder)
    receipt_folder.setdefault("children", []).append({
        "id": f"finance_connector_receipt_pointer_{receipt_id}",
        "name": f"Xero · {operation} · {status} · attempt {attempt}",
        "type": "business_container_artifact",
        "document_type": "connector_attempt_receipt",
        "status": status,
        "target": {"storage_path": str(path), "receipt_hash": receipt["receipt_hash"]},
    })
    tree["folders"] = folders
    tree["root"] = {**(tree.get("root") or {}), "id": "root", "type": "folder", "name": "Workflows", "children": folders}
    WorkflowFileCabinetRepository.save(business_id, tree)
    return receipt


def _public_connection(business_id: str) -> Dict[str, Any]:
    value = _read_json(_connection_path(business_id), {})
    granted_scopes = list(value.get("scopes") or [])
    missing_scopes = [scope for scope in XERO_SCOPES if scope not in granted_scopes]
    connected = value.get("status") == "connected"
    write_authorised = connected and XERO_WRITE_SCOPES.issubset(set(granted_scopes))
    return {
        "provider": "xero",
        "business_id": business_id,
        "configured": bool(str(os.getenv("XERO_CLIENT_ID") or "").strip()),
        "status": value.get("status") or "not_connected",
        "connected": connected,
        "tenant_id": value.get("tenant_id"),
        "tenant_name": value.get("tenant_name"),
        "tenant_type": value.get("tenant_type"),
        "available_tenants": value.get("available_tenants") or [],
        "scopes": granted_scopes,
        "required_scopes": XERO_SCOPES,
        "missing_scopes": missing_scopes,
        "reauthorisation_required": connected and bool(missing_scopes),
        "reauthorisation_pending": bool(value.get("reauthorisation_pending")),
        "read_only": not write_authorised,
        "external_writes_enabled": write_authorised,
        "write_mode": "exact_payload_approval_and_readback_verification" if write_authorised else "reauthorisation_required",
        "connected_at": value.get("connected_at"),
        "last_sync_at": value.get("last_sync_at"),
        "last_sync_status": value.get("last_sync_status") or "never_synced",
        "last_error": value.get("last_error"),
        "sync_summary": value.get("sync_summary") or {},
    }


class _TokenStore:
    """Keep OAuth token material outside the Business Container.

    Production macOS runs use Keychain through the Python keyring backend. Tests
    may opt into an isolated file store with AION_XERO_TOKEN_STORE_DIR.
    """

    @staticmethod
    def save(business_id: str, payload: Dict[str, Any]) -> str:
        test_dir = str(os.getenv("AION_XERO_TOKEN_STORE_DIR") or "").strip()
        if test_dir:
            path = Path(test_dir) / f"{business_id}.tokens.json"
            _write_json(path, payload)
            return f"test-secret-file://{path}"
        try:
            import keyring
            keyring.set_password(XERO_KEYCHAIN_SERVICE, business_id, json.dumps(payload))
        except Exception as exc:
            raise RuntimeError("macOS Keychain is unavailable; install the keyring dependency") from exc
        return f"keychain://{XERO_KEYCHAIN_SERVICE}/{business_id}"

    @staticmethod
    def load(business_id: str) -> Dict[str, Any]:
        test_dir = str(os.getenv("AION_XERO_TOKEN_STORE_DIR") or "").strip()
        if test_dir:
            return _read_json(Path(test_dir) / f"{business_id}.tokens.json", {})
        try:
            import keyring
            raw = keyring.get_password(XERO_KEYCHAIN_SERVICE, business_id)
            return json.loads(raw) if raw else {}
        except Exception:
            return {}

    @staticmethod
    def delete(business_id: str) -> None:
        test_dir = str(os.getenv("AION_XERO_TOKEN_STORE_DIR") or "").strip()
        if test_dir:
            (Path(test_dir) / f"{business_id}.tokens.json").unlink(missing_ok=True)
            return
        try:
            import keyring
            keyring.delete_password(XERO_KEYCHAIN_SERVICE, business_id)
        except Exception:
            pass


def _redirect_uri() -> str:
    return str(
        os.getenv("XERO_REDIRECT_URI")
        or "http://localhost:8080/api/aion/integrations/xero/callback"
    ).strip()


def _pkce_challenge(verifier: str) -> str:
    digest = sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


async def _xero_request_json(
    operation: str,
    method: str,
    url: str,
    *,
    timeout: float,
    attempts: int = 3,
    business_id: str | None = None,
    **kwargs: Any,
) -> Any:
    """Bounded retry policy with structured, secret-free diagnostics."""
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.request(method, url, **kwargs)
            retryable = response.status_code == 429 or response.status_code >= 500
            if response.status_code < 400:
                try:
                    value = response.json()
                    _record_connector_attempt(business_id, operation=operation, status="succeeded", attempt=attempt, provider_status=response.status_code)
                    return value
                except ValueError as exc:
                    _record_connector_attempt(business_id, operation=operation, status="failed", attempt=attempt, provider_status=response.status_code, error_code="xero_invalid_json")
                    raise HTTPException(status_code=502, detail={
                        "code": "xero_invalid_json", "provider": "xero",
                        "operation": operation, "attempt": attempt, "retryable": False,
                    }) from exc
            if not retryable or attempt == attempts:
                _record_connector_attempt(business_id, operation=operation, status="failed", attempt=attempt, provider_status=response.status_code, retryable=retryable, error_code="xero_provider_request_failed")
                raise HTTPException(status_code=502, detail={
                    "code": "xero_provider_request_failed", "provider": "xero",
                    "operation": operation, "provider_status": response.status_code,
                    "attempt": attempt, "retryable": retryable,
                })
            _record_connector_attempt(business_id, operation=operation, status="retrying", attempt=attempt, provider_status=response.status_code, retryable=True, error_code="xero_provider_retryable_status")
        except HTTPException:
            raise
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            last_error = exc
            if attempt == attempts:
                _record_connector_attempt(business_id, operation=operation, status="failed", attempt=attempt, retryable=True, error_code="xero_provider_unavailable", error_type=type(exc).__name__)
                raise HTTPException(status_code=504, detail={
                    "code": "xero_provider_unavailable", "provider": "xero",
                    "operation": operation, "attempt": attempt,
                    "error_type": type(exc).__name__, "retryable": True,
                }) from exc
            _record_connector_attempt(business_id, operation=operation, status="retrying", attempt=attempt, retryable=True, error_code="xero_transport_retry", error_type=type(exc).__name__)
        await asyncio.sleep(min(0.25 * (2 ** (attempt - 1)), 2.0))
    raise HTTPException(status_code=504, detail={
        "code": "xero_provider_unavailable", "provider": "xero",
        "operation": operation, "error_type": type(last_error).__name__ if last_error else "Unknown",
        "retryable": True,
    })


async def _token_request(data: Dict[str, str], business_id: str | None = None) -> Dict[str, Any]:
    token = await _xero_request_json(
        "token_exchange", "POST", XERO_TOKEN_URL, timeout=30.0, business_id=business_id, data=data,
        headers={"Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"},
    )
    token["obtained_at"] = _now()
    token["expires_at"] = (
        datetime.now(UTC) + timedelta(seconds=max(60, int(token.get("expires_in") or 1800)))
    ).replace(microsecond=0).isoformat()
    return token


async def _valid_access_token(business_id: str) -> str:
    token = _TokenStore.load(business_id)
    if not token:
        raise HTTPException(status_code=409, detail="xero_not_connected")
    expires_at = str(token.get("expires_at") or "")
    try:
        still_valid = datetime.fromisoformat(expires_at.replace("Z", "+00:00")) > datetime.now(UTC) + timedelta(minutes=2)
    except ValueError:
        still_valid = False
    if still_valid and token.get("access_token"):
        return str(token["access_token"])

    refresh = str(token.get("refresh_token") or "")
    client_id = str(os.getenv("XERO_CLIENT_ID") or "").strip()
    if not refresh or not client_id:
        raise HTTPException(status_code=409, detail="xero_reconnect_required")
    refreshed = await _token_request({
        "grant_type": "refresh_token",
        "refresh_token": refresh,
        "client_id": client_id,
    }, business_id)
    if not refreshed.get("refresh_token"):
        refreshed["refresh_token"] = refresh
    _TokenStore.save(business_id, refreshed)
    return str(refreshed.get("access_token") or "")


async def _connections(access_token: str, business_id: str | None = None) -> list[Dict[str, Any]]:
    value = await _xero_request_json(
        "connections", "GET", XERO_CONNECTIONS_URL, timeout=30.0, business_id=business_id,
        headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
    )
    return value if isinstance(value, list) else []


def _tenant_public(item: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "tenant_id": item.get("tenantId"),
        "tenant_name": item.get("tenantName"),
        "tenant_type": item.get("tenantType"),
        "updated_at": item.get("updatedDateUtc"),
    }


@router.get("/xero/{candidate}/status")
def xero_status(candidate: str) -> Dict[str, Any]:
    business_id = canonical_business_id(candidate)
    return {"ok": True, "connection": _public_connection(business_id)}


@router.get("/xero/{candidate}/receipts")
def xero_connector_receipts(candidate: str) -> Dict[str, Any]:
    business_id = canonical_business_id(candidate)
    receipt_dir = _integration_dir(business_id) / "receipts"
    receipts = [
        _read_json(path, {})
        for path in sorted(receipt_dir.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True)
    ] if receipt_dir.exists() else []
    return {"ok": True, "business_id": business_id, "receipts": receipts}


@router.get("/xero/{candidate}/contacts")
def xero_contacts(candidate: str) -> Dict[str, Any]:
    business_id = canonical_business_id(candidate)
    connection = _read_json(_connection_path(business_id), {})
    sync_id = str((connection.get("latest_snapshot_ref") or {}).get("sync_id") or "")
    payload = _read_json(_integration_dir(business_id) / "syncs" / sync_id / "contacts.json", {}) if sync_id else {}
    contacts = [{"contact_id": item.get("ContactID"), "name": item.get("Name"),
                 "email": item.get("EmailAddress"), "status": item.get("ContactStatus")}
                for item in payload.get("Contacts") or []
                if item.get("ContactID") and item.get("ContactStatus") != "ARCHIVED"]
    return {"ok": True, "business_id": business_id, "sync_id": sync_id, "contacts": contacts[:1000]}


@router.post("/xero/{candidate}/connect")
def xero_connect(candidate: str) -> Dict[str, Any]:
    business_id = canonical_business_id(candidate)
    client_id = str(os.getenv("XERO_CLIENT_ID") or "").strip()
    if not client_id:
        return {
            "ok": False,
            "reason": "xero_oauth_config_missing",
            "message": "Add XERO_CLIENT_ID and register the displayed redirect URI in the Xero developer portal.",
            "required_env": ["XERO_CLIENT_ID", "XERO_REDIRECT_URI"],
            "redirect_uri": _redirect_uri(),
            "connection": _public_connection(business_id),
        }
    state = secrets.token_urlsafe(32)
    verifier = secrets.token_urlsafe(64)
    pending = {
        "business_id": business_id,
        "state": state,
        "code_verifier": verifier,
        "created_at": _now(),
        "redirect_uri": _redirect_uri(),
        "previous_connection": _read_json(_connection_path(business_id), {}),
    }
    _write_json(_integration_dir(business_id) / "oauth_pending.json", pending)
    connection = _read_json(_connection_path(business_id), {})
    was_connected = connection.get("status") == "connected" and bool(connection.get("tenant_id"))
    connection.update({"status": "connected" if was_connected else "awaiting_authorisation",
                       "reauthorisation_pending": was_connected, "last_error": None})
    _write_json(_connection_path(business_id), connection)
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": _redirect_uri(),
        "scope": " ".join(XERO_SCOPES),
        "state": state,
        "code_challenge": _pkce_challenge(verifier),
        "code_challenge_method": "S256",
    }
    return {
        "ok": True,
        "connect_url": XERO_AUTHORIZE_URL + "?" + urlencode(params),
        "redirect_uri": _redirect_uri(),
        "connection": _public_connection(business_id),
    }


@router.get("/xero/callback", response_class=HTMLResponse)
async def xero_callback(
    code: str = Query(default=""),
    state: str = Query(default=""),
    error: str = Query(default=""),
) -> HTMLResponse:
    pending_match: tuple[str, Dict[str, Any], Path] | None = None
    root = AIONBusinessPaths.BUSINESS_CONTAINERS
    for path in root.glob("*/integrations/xero/oauth_pending.json"):
        pending = _read_json(path, {})
        if pending.get("state") == state:
            pending_match = (str(pending.get("business_id") or path.parents[2].name), pending, path)
            break
    if not pending_match:
        return HTMLResponse("<h2>Xero connection failed</h2><p>The OAuth state was not recognised. Return to Tessaris and try again.</p>", status_code=400)
    business_id, pending, pending_path = pending_match
    if error or not code:
        previous = pending.get("previous_connection") or {}
        connection = dict(previous) if previous.get("status") == "connected" else _public_connection(business_id)
        connection.update({"status": "connected" if previous.get("status") == "connected" else "not_connected",
                           "reauthorisation_pending": False,
                           "last_error": error or "missing_authorisation_code"})
        _write_json(_connection_path(business_id), connection)
        return HTMLResponse("<h2>Xero connection was not completed</h2><p>You can close this window and return to Tessaris.</p>", status_code=400)
    token = await _token_request({
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": str(pending.get("redirect_uri") or _redirect_uri()),
        "client_id": str(os.getenv("XERO_CLIENT_ID") or "").strip(),
        "code_verifier": str(pending.get("code_verifier") or ""),
    }, business_id)
    granted_scopes = str(token.get("scope") or "").split() or list(XERO_SCOPES)
    secret_ref = _TokenStore.save(business_id, token)
    tenants = [_tenant_public(item) for item in await _connections(str(token.get("access_token") or ""), business_id)]
    selected = tenants[0] if len(tenants) == 1 else {}
    connection = {
        **(pending.get("previous_connection") or {}),
        "provider": "xero",
        "business_id": business_id,
        "status": "connected" if selected else "tenant_selection_required",
        "tenant_id": selected.get("tenant_id"),
        "tenant_name": selected.get("tenant_name"),
        "tenant_type": selected.get("tenant_type"),
        "available_tenants": tenants,
        "scopes": granted_scopes,
        "secret_ref": secret_ref,
        "read_only": False,
        "external_writes_enabled": True,
        "connected_at": _now(),
        "last_sync_status": "never_synced",
        "last_error": None,
        "reauthorisation_pending": False,
    }
    _write_json(_connection_path(business_id), connection)
    pending_path.unlink(missing_ok=True)
    tenant_message = f"Connected to {selected.get('tenant_name')}." if selected else "Authorised. Select the Xero organisation in Tessaris."
    return HTMLResponse(f"<h2>Xero connected to Tessaris</h2><p>{tenant_message}</p><p>You can close this window and return to Finance.</p>")


class TenantSelection(BaseModel):
    tenant_id: str


class XeroBookkeepingExportPrepare(BaseModel):
    draft_id: str
    xero_contact_id: str
    prepared_by_person_id: str
    target_status: str = "DRAFT"


class XeroBookkeepingExportApproval(BaseModel):
    approved_by_person_id: str
    approved_payload_hash: str


class XeroBookkeepingExportExecution(BaseModel):
    executed_by_person_id: str

class XeroSupplierPrepare(BaseModel):
    name: str
    email: str | None = None
    prepared_by_person_id: str

class XeroSupplierApproval(BaseModel):
    approved_by_person_id: str
    approved_payload_hash: str

class XeroSupplierExecution(BaseModel):
    executed_by_person_id: str

class XeroSalesInvoicePrepare(BaseModel):
    invoice_id: str
    xero_contact_id: str
    prepared_by_person_id: str
    target_status: str = "DRAFT"

class XeroSalesInvoiceApproval(BaseModel):
    approved_by_person_id: str
    approved_payload_hash: str

class XeroSalesInvoiceExecution(BaseModel):
    executed_by_person_id: str


@router.post("/xero/{candidate}/tenant")
async def select_xero_tenant(candidate: str, request: TenantSelection) -> Dict[str, Any]:
    business_id = canonical_business_id(candidate)
    access_token = await _valid_access_token(business_id)
    tenants = [_tenant_public(item) for item in await _connections(access_token, business_id)]
    selected = next((item for item in tenants if item.get("tenant_id") == request.tenant_id), None)
    if not selected:
        raise HTTPException(status_code=404, detail="xero_tenant_not_found")
    connection = _read_json(_connection_path(business_id), {})
    connection.update({
        "status": "connected",
        **selected,
        "available_tenants": tenants,
        "last_error": None,
    })
    _write_json(_connection_path(business_id), connection)
    return {"ok": True, "connection": _public_connection(business_id)}


async def _xero_get(access_token: str, tenant_id: str, path: str, params: Dict[str, Any] | None = None,
                    business_id: str | None = None) -> Dict[str, Any]:
    value = await _xero_request_json(
        path.replace("/", "_"), "GET", f"{XERO_ACCOUNTING_BASE}/{path.lstrip('/')}",
        timeout=45.0, business_id=business_id, params=params or {},
        headers={"Authorization": f"Bearer {access_token}", "Xero-tenant-id": tenant_id, "Accept": "application/json"},
    )
    return value if isinstance(value, dict) else {"value": value}


async def _xero_put(access_token: str, tenant_id: str, path: str, payload: Dict[str, Any], *,
                    idempotency_key: str, business_id: str) -> Dict[str, Any]:
    value = await _xero_request_json(
        f"write_{path.replace('/', '_')}", "PUT", f"{XERO_ACCOUNTING_BASE}/{path.lstrip('/')}",
        timeout=45.0, business_id=business_id, json=payload,
        headers={"Authorization": f"Bearer {access_token}", "Xero-tenant-id": tenant_id,
                 "Accept": "application/json", "Content-Type": "application/json",
                 "Idempotency-Key": idempotency_key},
    )
    return value if isinstance(value, dict) else {"value": value}


async def _xero_put_attachment(access_token: str, tenant_id: str, path: str, filename: str,
                               content: bytes, mime_type: str, *, idempotency_key: str,
                               business_id: str) -> Dict[str, Any]:
    safe_filename = quote(Path(filename).name, safe="._-")
    value = await _xero_request_json(
        f"write_{path.replace('/', '_')}_attachment", "PUT",
        f"{XERO_ACCOUNTING_BASE}/{path.lstrip('/')}/Attachments/{safe_filename}",
        timeout=45.0, business_id=business_id, content=content,
        headers={"Authorization": f"Bearer {access_token}", "Xero-tenant-id": tenant_id,
                 "Accept": "application/json", "Content-Type": mime_type,
                 "Content-Disposition": f'attachment; filename="{Path(filename).name}"',
                 "Idempotency-Key": idempotency_key},
    )
    return value if isinstance(value, dict) else {"value": value}


async def _xero_projects_get(access_token: str, tenant_id: str, path: str,
                             business_id: str | None = None) -> Dict[str, Any]:
    value = await _xero_request_json(
        f"projects_{path.replace('/', '_')}", "GET", f"{XERO_PROJECTS_BASE}/{path.lstrip('/')}",
        timeout=45.0, business_id=business_id,
        headers={"Authorization": f"Bearer {access_token}", "Xero-tenant-id": tenant_id, "Accept": "application/json"},
    )
    return value if isinstance(value, dict) else {"value": value}


async def _xero_get_collection_pages(access_token: str, tenant_id: str, path: str,
                                     root: str, business_id: str, *, max_pages: int = 20) -> Dict[str, Any]:
    """Retrieve a bounded accounting collection without loading an unbounded history."""
    records: list[Dict[str, Any]] = []
    for page in range(1, max_pages + 1):
        payload = await _xero_get(access_token, tenant_id, path, {"page": page}, business_id)
        batch = [item for item in (payload.get(root) or []) if isinstance(item, dict)]
        records.extend(batch)
        if len(batch) < 100:
            return {root: records, "AionPagination": {"pages_fetched": page, "truncated": False}}
    return {root: records, "AionPagination": {"pages_fetched": max_pages, "truncated": True}}


def _update_finance_model_with_xero(business_id: str, snapshot: Dict[str, Any], evidence_ref: Dict[str, Any]) -> None:
    repository = BusinessContainerRepository()
    current = repository.load_optional_dict(business_id, "business_financial_model") or {}
    current.update({
        "id": f"{business_id}.business_financial_model",
        "workspace_id": business_id,
        "kind": "business_financial_model",
        "meta": BusinessContainerMeta(
            workspace_id=business_id,
            container_key="business_financial_model",
            updated_at=_now(),
            source="xero_read_only_sync",
        ).model_dump(mode="json"),
    })
    integration = dict(current.get("integration_evidence") or {})
    integration["xero"] = {
        "status": "connected",
        "tenant_id": snapshot.get("tenant_id"),
        "tenant_name": snapshot.get("tenant_name"),
        "last_sync_at": snapshot.get("synced_at"),
        "period": snapshot.get("period"),
        "summary": snapshot.get("summary"),
        "evidence_ref": evidence_ref,
        "read_only": True,
    }
    current["integration_evidence"] = integration
    refs = list(current.get("evidence_refs") or [])
    refs = [item for item in refs if item.get("source") != "xero_read_only_sync"]
    refs.append(evidence_ref)
    current["evidence_refs"] = refs
    current["revision"] = int(current.get("revision") or 0) + 1
    repository.save_model(BusinessFinancialModelContainer(**current))


@router.post("/xero/{candidate}/sync")
async def sync_xero(candidate: str) -> Dict[str, Any]:
    business_id = canonical_business_id(candidate)
    connection = _read_json(_connection_path(business_id), {})
    tenant_id = str(connection.get("tenant_id") or "")
    if connection.get("status") != "connected" or not tenant_id:
        raise HTTPException(status_code=409, detail="xero_tenant_selection_required")
    access_token = await _valid_access_token(business_id)
    to_date = date.today()
    from_date = to_date - timedelta(days=365)
    requests = {
        "organisation": ("Organisation", {}),
        "accounts": ("Accounts", {}),
        "contacts": ("Contacts", {"page": 1}),
        "invoices": ("Invoices", {"page": 1}),
        "bank_transactions": ("BankTransactions", {"page": 1}),
        "payments": ("Payments", {"page": 1}),
        "manual_journals": ("ManualJournals", {"page": 1}),
        "tracking_categories": ("TrackingCategories", {}),
        "profit_and_loss": ("Reports/ProfitAndLoss", {"fromDate": from_date.isoformat(), "toDate": to_date.isoformat(), "standardLayout": "true"}),
        "balance_sheet": ("Reports/BalanceSheet", {"date": to_date.isoformat(), "standardLayout": "true"}),
        "bank_summary": ("Reports/BankSummary", {"fromDate": from_date.isoformat(), "toDate": to_date.isoformat()}),
    }
    raw: Dict[str, Any] = {}
    optional_failures: list[Dict[str, Any]] = []
    try:
        for key, (path, params) in requests.items():
            try:
                collection_root = {"contacts": "Contacts", "invoices": "Invoices", "bank_transactions": "BankTransactions", "payments": "Payments", "manual_journals": "ManualJournals"}.get(key)
                raw[key] = (
                    await _xero_get_collection_pages(access_token, tenant_id, path, collection_root, business_id)
                    if collection_root else await _xero_get(access_token, tenant_id, path, params, business_id)
                )
            except HTTPException as exc:
                if key not in {"bank_transactions", "payments", "manual_journals", "tracking_categories"}:
                    raise
                raw[key] = {
                    {"bank_transactions": "BankTransactions", "payments": "Payments", "manual_journals": "ManualJournals", "tracking_categories": "TrackingCategories"}[key]: []
                }
                detail = exc.detail if isinstance(exc.detail, dict) else {}
                optional_failures.append({"collection": key, "code": detail.get("code") or "xero_optional_collection_unavailable", "provider_status": detail.get("provider_status")})
        try:
            project_payload = await _xero_projects_get(access_token, tenant_id, "Projects", business_id)
            raw["projects"] = {
                "Projects": project_payload.get("Projects") or project_payload.get("items") or [],
                "AionPagination": project_payload.get("pagination") or {},
            }
        except HTTPException as exc:
            raw["projects"] = {"Projects": []}
            detail = exc.detail if isinstance(exc.detail, dict) else {}
            optional_failures.append({"collection": "projects", "code": detail.get("code") or "xero_projects_unavailable", "provider_status": detail.get("provider_status")})
    except Exception as exc:
        connection.update({"last_sync_status": "failed", "last_error": str(exc)[:1000]})
        _write_json(_connection_path(business_id), connection)
        raise

    sync_id = f"xero_sync_{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}"
    sync_dir = _integration_dir(business_id) / "syncs" / sync_id
    sync_dir.mkdir(parents=True, exist_ok=True)
    for key, payload in raw.items():
        _write_json(sync_dir / f"{key}.json", payload)
    summary = {
        "organisation_count": len(raw.get("organisation", {}).get("Organisations") or []),
        "account_count": len(raw.get("accounts", {}).get("Accounts") or []),
        "contact_count": len(raw.get("contacts", {}).get("Contacts") or []),
        "invoice_count": len(raw.get("invoices", {}).get("Invoices") or []),
        "bank_transaction_count": len(raw.get("bank_transactions", {}).get("BankTransactions") or []),
        "payment_count": len(raw.get("payments", {}).get("Payments") or []),
        "manual_journal_count": len(raw.get("manual_journals", {}).get("ManualJournals") or []),
        "tracking_category_count": len(raw.get("tracking_categories", {}).get("TrackingCategories") or []),
        "project_count": len(raw.get("projects", {}).get("Projects") or []),
        "reports_received": [key for key in ["profit_and_loss", "balance_sheet", "bank_summary"] if raw.get(key)],
        "optional_collection_failures": optional_failures,
    }
    snapshot = {
        "schema_version": "aion.xero.read_only_sync.v1",
        "sync_id": sync_id,
        "business_id": business_id,
        "tenant_id": tenant_id,
        "tenant_name": connection.get("tenant_name"),
        "synced_at": _now(),
        "period": {"from": from_date.isoformat(), "to": to_date.isoformat()},
        "summary": summary,
        "source_paths": {key: f"integrations/xero/syncs/{sync_id}/{key}.json" for key in raw},
        "read_only": True,
        "external_writes_enabled": False,
    }
    snapshot["snapshot_hash"] = _hash(snapshot)
    _write_json(sync_dir / "snapshot.json", snapshot)
    evidence_ref = {
        "source": "xero_read_only_sync",
        "provider": "xero",
        "sync_id": sync_id,
        "snapshot_hash": snapshot["snapshot_hash"],
        "storage_path": f"business_containers/{business_id}/integrations/xero/syncs/{sync_id}/snapshot.json",
        "tenant_id": tenant_id,
        "period": snapshot["period"],
        "observed_at": snapshot["synced_at"],
        "verification_status": "provider_sourced",
    }
    _update_finance_model_with_xero(business_id, snapshot, evidence_ref)
    connection.update({
        "last_sync_at": snapshot["synced_at"],
        "last_sync_status": "complete",
        "last_error": None,
        "sync_summary": summary,
        "latest_snapshot_ref": evidence_ref,
    })
    _write_json(_connection_path(business_id), connection)
    return {"ok": True, "connection": _public_connection(business_id), "snapshot": snapshot, "evidence_ref": evidence_ref}


@router.get("/xero/{candidate}/bookkeeping-exports")
def list_xero_bookkeeping_exports(candidate: str) -> Dict[str, Any]:
    business_id = canonical_business_id(candidate)
    try:
        exports = XeroBookkeepingExportService().list(business_id)
    except (ValueError, PermissionError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"ok": True, "business_id": business_id, "exports": exports,
            "connection": _public_connection(business_id)}


@router.get("/xero/{candidate}/supplier-contacts")
def list_xero_supplier_contact_requests(candidate: str) -> Dict[str, Any]:
    business_id = canonical_business_id(candidate)
    return {"ok": True, "business_id": business_id, "requests": XeroSupplierContactService().list(business_id)}


@router.post("/xero/{candidate}/supplier-contacts/prepare")
def prepare_xero_supplier_contact(candidate: str, request: XeroSupplierPrepare) -> Dict[str, Any]:
    business_id = canonical_business_id(candidate)
    try:
        record = XeroSupplierContactService().prepare(business_id, name=request.name, email=request.email,
                                                       prepared_by_person_id=request.prepared_by_person_id)
    except PermissionError as exc: raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc: raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"ok": True, "request": record, "external_write_performed": False}


@router.post("/xero/{candidate}/supplier-contacts/{request_id}/approve")
def approve_xero_supplier_contact(candidate: str, request_id: str, request: XeroSupplierApproval) -> Dict[str, Any]:
    business_id = canonical_business_id(candidate)
    try:
        record = XeroSupplierContactService().approve(business_id, request_id,
            approved_by_person_id=request.approved_by_person_id, approved_payload_hash=request.approved_payload_hash)
    except FileNotFoundError as exc: raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc: raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc: raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"ok": True, "request": record, "external_write_performed": False}


@router.post("/xero/{candidate}/supplier-contacts/{request_id}/execute")
async def execute_xero_supplier_contact(candidate: str, request_id: str, request: XeroSupplierExecution) -> Dict[str, Any]:
    business_id = canonical_business_id(candidate); service = XeroSupplierContactService()
    try:
        record = service.execution_request(business_id, request_id, executed_by_person_id=request.executed_by_person_id)
        if record.get("status") == "verified_in_xero": return {"ok": True, "request": record, "idempotent_replay": True}
        connection = _public_connection(business_id)
        if not connection.get("external_writes_enabled"): raise HTTPException(status_code=409, detail="xero_write_reauthorisation_required")
        token = await _valid_access_token(business_id); tenant = str(connection.get("tenant_id") or "")
        if record.get("status") == "approved_for_xero_write":
            response = await _xero_put(token, tenant, "Contacts", record["payload"],
                                       idempotency_key=record["idempotency_key"], business_id=business_id)
            record = service.record_response(business_id, request_id, response)
        readback = await _xero_get(token, tenant, f"Contacts/{record['execution']['resource_id']}", business_id=business_id)
        record = service.verify(business_id, request_id, readback)
    except HTTPException: raise
    except FileNotFoundError as exc: raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc: raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc: raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"ok": True, "request": record, "external_write_performed": True, "verified_by_readback": True}


@router.post("/xero/{candidate}/bookkeeping-exports/prepare")
def prepare_xero_bookkeeping_export(candidate: str, request: XeroBookkeepingExportPrepare) -> Dict[str, Any]:
    business_id = canonical_business_id(candidate)
    try:
        record = XeroBookkeepingExportService().prepare(
            business_id, request.draft_id, xero_contact_id=request.xero_contact_id,
            prepared_by_person_id=request.prepared_by_person_id, target_status=request.target_status,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"ok": True, "business_id": business_id, "export": record, "external_write_performed": False}


@router.post("/xero/{candidate}/bookkeeping-exports/{export_id}/approve")
def approve_xero_bookkeeping_export(candidate: str, export_id: str,
                                    request: XeroBookkeepingExportApproval) -> Dict[str, Any]:
    business_id = canonical_business_id(candidate)
    try:
        record = XeroBookkeepingExportService().approve(
            business_id, export_id, approved_by_person_id=request.approved_by_person_id,
            approved_payload_hash=request.approved_payload_hash,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"ok": True, "business_id": business_id, "export": record, "external_write_performed": False}


@router.post("/xero/{candidate}/bookkeeping-exports/{export_id}/execute")
async def execute_xero_bookkeeping_export(candidate: str, export_id: str,
                                          request: XeroBookkeepingExportExecution) -> Dict[str, Any]:
    business_id = canonical_business_id(candidate)
    service = XeroBookkeepingExportService()
    try:
        record = service.execution_request(
            business_id, export_id, executed_by_person_id=request.executed_by_person_id
        )
        if record.get("status") == "verified_in_xero":
            return {"ok": True, "business_id": business_id, "export": record,
                    "external_write_performed": True, "idempotent_replay": True}
        connection = _public_connection(business_id)
        if not connection.get("connected"):
            raise HTTPException(status_code=409, detail="xero_not_connected")
        if not connection.get("external_writes_enabled"):
            raise HTTPException(status_code=409, detail={"code": "xero_write_reauthorisation_required",
                "missing_scopes": connection.get("missing_scopes") or []})
        tenant_id = str(connection.get("tenant_id") or "")
        access_token = await _valid_access_token(business_id)
        if record.get("status") == "approved_for_xero_write":
            response = await _xero_put(
                access_token, tenant_id, record["endpoint"], record["payload"],
                idempotency_key=record["idempotency_key"], business_id=business_id,
            )
            record = service.record_response(business_id, export_id, response)
        resource_id = record["execution"]["resource_id"]
        if record.get("status") == "provider_response_received":
            readback = await _xero_get(access_token, tenant_id, f"{record['endpoint']}/{resource_id}", business_id=business_id)
            record = service.verify_readback(business_id, export_id, readback)
        if record.get("status") == "resource_verified_pending_attachment":
            file_path, document = FinanceInboxService().file_path(business_id, record["source_document_id"])
            content = file_path.read_bytes()
            expected_hash = str((record.get("attachment") or {}).get("content_hash") or "")
            actual_hash = "sha256:" + sha256(content).hexdigest()
            if actual_hash != expected_hash:
                raise HTTPException(status_code=409, detail="finance_attachment_hash_mismatch_before_xero_upload")
            filename = str((document.get("source") or {}).get("filename") or file_path.name)
            mime_type = str((document.get("source") or {}).get("mime_type") or "application/octet-stream")
            await _xero_put_attachment(
                access_token, tenant_id, f"{record['endpoint']}/{resource_id}", filename, content, mime_type,
                idempotency_key=(record["idempotency_key"] + "-attachment")[:128], business_id=business_id,
            )
            attachments = await _xero_get(
                access_token, tenant_id, f"{record['endpoint']}/{resource_id}/Attachments", business_id=business_id
            )
            record = service.verify_attachment_readback(business_id, export_id, attachments)
    except HTTPException:
        raise
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"ok": True, "business_id": business_id, "export": record,
            "external_write_performed": True, "verified_by_readback": True}


@router.get("/xero/{candidate}/sales-invoice-exports")
def list_xero_sales_invoice_exports(candidate: str) -> Dict[str, Any]:
    business_id = canonical_business_id(candidate)
    return {"ok": True, "business_id": business_id,
            "exports": XeroSalesInvoiceExportService().list(business_id),
            "connection": _public_connection(business_id)}


@router.post("/xero/{candidate}/sales-invoice-exports/prepare")
def prepare_xero_sales_invoice_export(candidate: str,
                                      request: XeroSalesInvoicePrepare) -> Dict[str, Any]:
    business_id = canonical_business_id(candidate)
    try:
        record = XeroSalesInvoiceExportService().prepare(
            business_id, request.invoice_id, xero_contact_id=request.xero_contact_id,
            prepared_by_person_id=request.prepared_by_person_id,
            target_status=request.target_status,
        )
    except FileNotFoundError as exc: raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc: raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc: raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"ok": True, "business_id": business_id, "export": record,
            "external_write_performed": False}


@router.post("/xero/{candidate}/sales-invoice-exports/{export_id}/approve")
def approve_xero_sales_invoice_export(candidate: str, export_id: str,
                                      request: XeroSalesInvoiceApproval) -> Dict[str, Any]:
    business_id = canonical_business_id(candidate)
    try:
        record = XeroSalesInvoiceExportService().approve(
            business_id, export_id, approved_by_person_id=request.approved_by_person_id,
            approved_payload_hash=request.approved_payload_hash)
    except FileNotFoundError as exc: raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc: raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc: raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"ok": True, "business_id": business_id, "export": record,
            "external_write_performed": False}


@router.post("/xero/{candidate}/sales-invoice-exports/{export_id}/execute")
async def execute_xero_sales_invoice_export(candidate: str, export_id: str,
                                             request: XeroSalesInvoiceExecution) -> Dict[str, Any]:
    business_id = canonical_business_id(candidate); service = XeroSalesInvoiceExportService()
    try:
        record = service.execution_request(
            business_id, export_id, executed_by_person_id=request.executed_by_person_id)
        if record.get("status") == "verified_in_xero":
            return {"ok": True, "business_id": business_id, "export": record,
                    "external_write_performed": True, "idempotent_replay": True}
        connection = _public_connection(business_id)
        if not connection.get("external_writes_enabled"):
            raise HTTPException(status_code=409, detail="xero_write_reauthorisation_required")
        token = await _valid_access_token(business_id); tenant = str(connection.get("tenant_id") or "")
        if record.get("status") == "approved_for_xero_write":
            response = await _xero_put(token, tenant, record["endpoint"], record["payload"],
                                       idempotency_key=record["idempotency_key"], business_id=business_id)
            record = service.record_response(business_id, export_id, response)
        readback = await _xero_get(token, tenant,
                                   f"{record['endpoint']}/{record['execution']['resource_id']}",
                                   business_id=business_id)
        record = service.verify(business_id, export_id, readback)
    except HTTPException: raise
    except FileNotFoundError as exc: raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc: raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc: raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"ok": True, "business_id": business_id, "export": record,
            "external_write_performed": True, "verified_by_readback": True}


@router.delete("/xero/{candidate}")
def disconnect_xero(candidate: str) -> Dict[str, Any]:
    business_id = canonical_business_id(candidate)
    _TokenStore.delete(business_id)
    connection = _public_connection(business_id)
    connection.update({
        "status": "not_connected",
        "tenant_id": None,
        "tenant_name": None,
        "tenant_type": None,
        "available_tenants": [],
        "last_error": None,
    })
    _write_json(_connection_path(business_id), connection)
    return {"ok": True, "connection": _public_connection(business_id)}
