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
from urllib.parse import urlencode

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
from backend.modules.aion_business.runtime.workflow_file_cabinet_repository import (
    WorkflowFileCabinetRepository,
)


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
    "accounting.invoices.read",
    "accounting.payments.read",
    "accounting.banktransactions.read",
    "accounting.manualjournals.read",
    "accounting.reports.profitandloss.read",
    "accounting.reports.balancesheet.read",
    "accounting.reports.banksummary.read",
    "projects.read",
]


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
        "read_only": True,
        "external_writes_enabled": False,
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
    }
    _write_json(_integration_dir(business_id) / "oauth_pending.json", pending)
    connection = _public_connection(business_id)
    connection.update({"status": "awaiting_authorisation", "last_error": None, "scopes": XERO_SCOPES})
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
        connection = _public_connection(business_id)
        connection.update({"status": "not_connected", "last_error": error or "missing_authorisation_code"})
        _write_json(_connection_path(business_id), connection)
        return HTMLResponse("<h2>Xero connection was not completed</h2><p>You can close this window and return to Tessaris.</p>", status_code=400)
    token = await _token_request({
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": str(pending.get("redirect_uri") or _redirect_uri()),
        "client_id": str(os.getenv("XERO_CLIENT_ID") or "").strip(),
        "code_verifier": str(pending.get("code_verifier") or ""),
    }, business_id)
    secret_ref = _TokenStore.save(business_id, token)
    tenants = [_tenant_public(item) for item in await _connections(str(token.get("access_token") or ""), business_id)]
    selected = tenants[0] if len(tenants) == 1 else {}
    connection = {
        "provider": "xero",
        "business_id": business_id,
        "status": "connected" if selected else "tenant_selection_required",
        "tenant_id": selected.get("tenant_id"),
        "tenant_name": selected.get("tenant_name"),
        "tenant_type": selected.get("tenant_type"),
        "available_tenants": tenants,
        "scopes": XERO_SCOPES,
        "secret_ref": secret_ref,
        "read_only": True,
        "external_writes_enabled": False,
        "connected_at": _now(),
        "last_sync_status": "never_synced",
        "last_error": None,
    }
    _write_json(_connection_path(business_id), connection)
    pending_path.unlink(missing_ok=True)
    tenant_message = f"Connected to {selected.get('tenant_name')}." if selected else "Authorised. Select the Xero organisation in Tessaris."
    return HTMLResponse(f"<h2>Xero connected to Tessaris</h2><p>{tenant_message}</p><p>You can close this window and return to Finance.</p>")


class TenantSelection(BaseModel):
    tenant_id: str


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
                collection_root = {"invoices": "Invoices", "bank_transactions": "BankTransactions", "payments": "Payments", "manual_journals": "ManualJournals"}.get(key)
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
