from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
import asyncio
from hashlib import sha256
import base64
import json
import os
from pathlib import Path
import secrets
import subprocess
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
from backend.modules.aion_business.runtime.accountant_harness_service import AccountantHarnessService
from backend.modules.aion_business.providers.quickbooks_online_accounting_adapter import QuickBooksOnlineAccountingAdapter
from backend.modules.aion_business.providers.sage_accounting_adapter import SageAccountingAdapter
from backend.modules.aion_business.providers.zoho_books_accounting_adapter import ZohoBooksAccountingAdapter
from backend.modules.aion_business.providers.freeagent_accounting_adapter import FreeAgentAccountingAdapter
from backend.modules.aion_business.providers.freshbooks_accounting_adapter import FreshBooksAccountingAdapter


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

SAGE_AUTHORIZE_URL = "https://www.sageone.com/oauth2/auth/central"
SAGE_TOKEN_URL = "https://oauth.accounting.sage.com/token"
SAGE_ACCOUNTING_BASE = "https://api.accounting.sage.com/v3.1"
SAGE_APP_KEYCHAIN_SERVICE = "com.tessaris.aion.sage-accounting-app"
SAGE_TOKEN_KEYCHAIN_SERVICE = "com.tessaris.aion.sage-accounting"
SAGE_SCOPE = "full_access"

QUICKBOOKS_AUTHORIZE_URL = "https://appcenter.intuit.com/connect/oauth2"
QUICKBOOKS_TOKEN_URL = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"
QUICKBOOKS_APP_KEYCHAIN_SERVICE = "com.tessaris.aion.quickbooks-online-app"
QUICKBOOKS_TOKEN_KEYCHAIN_SERVICE = "com.tessaris.aion.quickbooks-online"
QUICKBOOKS_SCOPE = "com.intuit.quickbooks.accounting"

ZOHO_BOOKS_APP_KEYCHAIN_SERVICE = "com.tessaris.aion.zoho-books-app"
ZOHO_BOOKS_TOKEN_KEYCHAIN_SERVICE = "com.tessaris.aion.zoho-books"
ZOHO_BOOKS_SCOPES = [
    "ZohoBooks.settings.READ",
    "ZohoBooks.invoices.READ",
    "ZohoBooks.bills.READ",
    "ZohoBooks.customerpayments.READ",
    "ZohoBooks.vendorpayments.READ",
    "ZohoBooks.banking.READ",
    "ZohoBooks.accountants.READ",
]

FREEAGENT_APP_KEYCHAIN_SERVICE = "com.tessaris.aion.freeagent-app"
FREEAGENT_TOKEN_KEYCHAIN_SERVICE = "com.tessaris.aion.freeagent"

FRESHBOOKS_AUTHORIZE_URL = "https://auth.freshbooks.com/oauth/authorize/"
FRESHBOOKS_TOKEN_URL = "https://api.freshbooks.com/auth/oauth/token"
FRESHBOOKS_IDENTITY_URL = "https://api.freshbooks.com/auth/api/v1/users/me"
FRESHBOOKS_APP_KEYCHAIN_SERVICE = "com.tessaris.aion.freshbooks-app"
FRESHBOOKS_TOKEN_KEYCHAIN_SERVICE = "com.tessaris.aion.freshbooks"
FRESHBOOKS_SCOPES = [
    "user:profile:read",
    "user:business:read",
    "user:account:read",
    "user:invoices:read",
    "user:bills:read",
    "user:payments:read",
    "user:expenses:read",
    "user:reports:read",
    "user:journal_entries:read",
    "offline_access",
]


class AccountingProviderSnapshotRequest(BaseModel):
    company_id: str
    actor: str = "finance_pilot"
    raw_snapshot: Dict[str, Any]


class AccountingProviderReconciliationRequest(BaseModel):
    actor: str = "finance_pilot"
    amount_tolerance_percent: float = 1.0
    date_window_days: int = 7


@router.get("/accounting/providers")
def accounting_provider_catalog() -> Dict[str, Any]:
    """Describe implemented adapters separately from live connection state."""
    return AccountantHarnessService().catalog()


@router.post("/accounting/{provider_id}/{candidate}/ingest-read-snapshot")
def ingest_accounting_provider_snapshot(
    provider_id: str, candidate: str, request: AccountingProviderSnapshotRequest
) -> Dict[str, Any]:
    """Internal adapter boundary used after an authorised provider read.

    OAuth secrets never enter this payload.  The raw provider response is
    hash-bound, normalized, and stored as read-only evidence.
    """
    business_id = canonical_business_id(candidate)
    try:
        result = AccountantHarnessService().ingest(
            business_id, provider_id, request.raw_snapshot,
            company_id=request.company_id, actor=request.actor,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "business_id": business_id, "provider": provider_id,
            **result, "external_write_performed": False}


@router.post("/accounting/{provider_id}/{candidate}/reconcile")
def reconcile_accounting_provider_snapshot(
    provider_id: str, candidate: str, request: AccountingProviderReconciliationRequest
) -> Dict[str, Any]:
    business_id = canonical_business_id(candidate)
    catalog = AccountantHarnessService().catalog()
    if provider_id not in {row["provider_id"] for row in catalog["providers"]}:
        raise HTTPException(status_code=404, detail="unknown_accounting_provider")
    try:
        result = AccountantHarnessService().reconcile(
            business_id, actor=request.actor,
            amount_tolerance=request.amount_tolerance_percent / 100,
            date_window_days=request.date_window_days,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"ok": True, "business_id": business_id, "provider": provider_id,
            "transaction_reconciliation": result, "external_write_performed": False}


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


def _sage_integration_dir(business_id: str) -> Path:
    path = AIONBusinessPaths.business_container_dir(business_id) / "integrations" / "sage_accounting"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _sage_connection_path(business_id: str) -> Path:
    return _sage_integration_dir(business_id) / "connection.json"


def _quickbooks_integration_dir(business_id: str) -> Path:
    path = AIONBusinessPaths.business_container_dir(business_id) / "integrations" / "quickbooks_online"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _quickbooks_connection_path(business_id: str) -> Path:
    return _quickbooks_integration_dir(business_id) / "connection.json"


def _zoho_books_integration_dir(business_id: str) -> Path:
    path = AIONBusinessPaths.business_container_dir(business_id) / "integrations" / "zoho_books"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _zoho_books_connection_path(business_id: str) -> Path:
    return _zoho_books_integration_dir(business_id) / "connection.json"


def _freeagent_integration_dir(business_id: str) -> Path:
    path = AIONBusinessPaths.business_container_dir(business_id) / "integrations" / "freeagent"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _freeagent_connection_path(business_id: str) -> Path:
    return _freeagent_integration_dir(business_id) / "connection.json"


def _freshbooks_integration_dir(business_id: str) -> Path:
    path = AIONBusinessPaths.business_container_dir(business_id) / "integrations" / "freshbooks"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _freshbooks_connection_path(business_id: str) -> Path:
    return _freshbooks_integration_dir(business_id) / "connection.json"


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


def _sage_app_credentials() -> tuple[str, str]:
    """Read the developer application credentials without exposing them to records or logs."""
    client_id = str(os.getenv("SAGE_ACCOUNTING_CLIENT_ID") or "").strip()
    client_secret = str(os.getenv("SAGE_ACCOUNTING_CLIENT_SECRET") or "").strip()
    if client_id and client_secret:
        return client_id, client_secret
    def keychain_value(account: str) -> str:
        try:
            result = subprocess.run(
                ["/usr/bin/security", "find-generic-password", "-w", "-s", SAGE_APP_KEYCHAIN_SERVICE, "-a", account],
                capture_output=True, text=True, check=False, timeout=5,
            )
            return result.stdout.strip() if result.returncode == 0 else ""
        except (OSError, subprocess.SubprocessError):
            return ""
    client_id = keychain_value("client_id")
    client_secret = keychain_value("client_secret")
    return client_id, client_secret


class _SageTokenStore:
    @staticmethod
    def save(business_id: str, payload: Dict[str, Any]) -> str:
        test_dir = str(os.getenv("AION_SAGE_TOKEN_STORE_DIR") or "").strip()
        if test_dir:
            path = Path(test_dir) / f"{business_id}.tokens.json"
            _write_json(path, payload)
            return f"test-secret-file://{path}"
        try:
            import keyring
            keyring.set_password(SAGE_TOKEN_KEYCHAIN_SERVICE, business_id, json.dumps(payload))
        except Exception as exc:
            raise RuntimeError("macOS Keychain is unavailable; install the keyring dependency") from exc
        return f"keychain://{SAGE_TOKEN_KEYCHAIN_SERVICE}/{business_id}"

    @staticmethod
    def load(business_id: str) -> Dict[str, Any]:
        test_dir = str(os.getenv("AION_SAGE_TOKEN_STORE_DIR") or "").strip()
        if test_dir:
            return _read_json(Path(test_dir) / f"{business_id}.tokens.json", {})
        try:
            import keyring
            raw = keyring.get_password(SAGE_TOKEN_KEYCHAIN_SERVICE, business_id)
            return json.loads(raw) if raw else {}
        except Exception:
            return {}


def _sage_redirect_uri() -> str:
    return str(
        os.getenv("SAGE_ACCOUNTING_REDIRECT_URI")
        or "http://localhost:8080/api/aion/integrations/sage-accounting/callback"
    ).strip()


def _sage_public_connection(business_id: str) -> Dict[str, Any]:
    value = _read_json(_sage_connection_path(business_id), {})
    client_id, client_secret = _sage_app_credentials()
    connected = value.get("status") == "connected"
    return {
        "provider": "sage_accounting",
        "business_id": business_id,
        "configured": bool(client_id and client_secret),
        "status": value.get("status") or "not_connected",
        "connected": connected,
        "sage_business_id": value.get("sage_business_id"),
        "sage_business_name": value.get("sage_business_name"),
        "available_businesses": value.get("available_businesses") or [],
        "scope": value.get("scope"),
        "read_only": not connected,
        "external_writes_enabled": False,
        "write_mode": "approval_and_provider_readback_required",
        "connected_at": value.get("connected_at"),
        "last_sync_at": value.get("last_sync_at"),
        "last_sync_status": value.get("last_sync_status") or "never_synced",
        "last_error": value.get("last_error"),
    }


async def _sage_request_json(
    method: str, url: str, *, operation: str, timeout: float = 30.0, **kwargs: Any
) -> Any:
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.request(method, url, **kwargs)
    except (httpx.TimeoutException, httpx.TransportError) as exc:
        raise HTTPException(status_code=504, detail={
            "code": "sage_provider_unavailable", "provider": "sage_accounting",
            "operation": operation, "error_type": type(exc).__name__, "retryable": True,
        }) from exc
    if response.status_code >= 400:
        raise HTTPException(status_code=502, detail={
            "code": "sage_provider_request_failed", "provider": "sage_accounting",
            "operation": operation, "provider_status": response.status_code,
            "retryable": response.status_code == 429 or response.status_code >= 500,
        })
    try:
        return response.json()
    except ValueError as exc:
        raise HTTPException(status_code=502, detail={
            "code": "sage_invalid_json", "provider": "sage_accounting", "operation": operation,
        }) from exc


async def _sage_token_request(data: Dict[str, str]) -> Dict[str, Any]:
    value = await _sage_request_json(
        "POST", SAGE_TOKEN_URL, operation="token_exchange",
        data=data, headers={"Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"},
    )
    value["obtained_at"] = _now()
    value["expires_at"] = (
        datetime.now(UTC) + timedelta(seconds=max(30, int(value.get("expires_in") or 300)))
    ).replace(microsecond=0).isoformat()
    if value.get("refresh_token_expires_in"):
        value["refresh_token_expires_at"] = (
            datetime.now(UTC) + timedelta(seconds=int(value["refresh_token_expires_in"]))
        ).replace(microsecond=0).isoformat()
    return value


async def _sage_valid_access_token(business_id: str) -> str:
    token = _SageTokenStore.load(business_id)
    if not token:
        raise HTTPException(status_code=409, detail="sage_accounting_not_connected")
    try:
        valid = datetime.fromisoformat(str(token.get("expires_at") or "").replace("Z", "+00:00")) > datetime.now(UTC) + timedelta(seconds=45)
    except ValueError:
        valid = False
    if valid and token.get("access_token"):
        return str(token["access_token"])
    refresh_token = str(token.get("refresh_token") or "")
    client_id, client_secret = _sage_app_credentials()
    if not refresh_token or not client_id or not client_secret:
        raise HTTPException(status_code=409, detail="sage_accounting_reconnect_required")
    refreshed = await _sage_token_request({
        "grant_type": "refresh_token", "refresh_token": refresh_token,
        "client_id": client_id, "client_secret": client_secret,
    })
    if not refreshed.get("refresh_token"):
        refreshed["refresh_token"] = refresh_token
    _SageTokenStore.save(business_id, refreshed)
    return str(refreshed.get("access_token") or "")


async def _sage_businesses(access_token: str) -> list[Dict[str, Any]]:
    value = await _sage_request_json(
        "GET", f"{SAGE_ACCOUNTING_BASE}/businesses", operation="businesses",
        headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
    )
    items = value.get("$items") or value.get("items") or [] if isinstance(value, dict) else []
    return [
        {"business_id": item.get("id"), "business_name": item.get("displayed_as") or item.get("name")}
        for item in items if item.get("id")
    ]


def _quickbooks_app_credentials() -> tuple[str, str]:
    """Load Intuit app credentials without writing them into workspace records."""
    client_id = str(os.getenv("QUICKBOOKS_ONLINE_CLIENT_ID") or "").strip()
    client_secret = str(os.getenv("QUICKBOOKS_ONLINE_CLIENT_SECRET") or "").strip()
    if client_id and client_secret:
        return client_id, client_secret

    def keychain_value(account: str) -> str:
        try:
            result = subprocess.run(
                ["/usr/bin/security", "find-generic-password", "-w", "-s", QUICKBOOKS_APP_KEYCHAIN_SERVICE, "-a", account],
                capture_output=True, text=True, check=False, timeout=5,
            )
            return result.stdout.strip() if result.returncode == 0 else ""
        except (OSError, subprocess.SubprocessError):
            return ""

    return keychain_value("client_id"), keychain_value("client_secret")


class _QuickBooksTokenStore:
    @staticmethod
    def save(business_id: str, payload: Dict[str, Any]) -> str:
        test_dir = str(os.getenv("AION_QUICKBOOKS_TOKEN_STORE_DIR") or "").strip()
        if test_dir:
            path = Path(test_dir) / f"{business_id}.tokens.json"
            _write_json(path, payload)
            return f"test-secret-file://{path}"
        try:
            import keyring
            keyring.set_password(QUICKBOOKS_TOKEN_KEYCHAIN_SERVICE, business_id, json.dumps(payload))
        except Exception as exc:
            raise RuntimeError("macOS Keychain is unavailable; install the keyring dependency") from exc
        return f"keychain://{QUICKBOOKS_TOKEN_KEYCHAIN_SERVICE}/{business_id}"

    @staticmethod
    def load(business_id: str) -> Dict[str, Any]:
        test_dir = str(os.getenv("AION_QUICKBOOKS_TOKEN_STORE_DIR") or "").strip()
        if test_dir:
            return _read_json(Path(test_dir) / f"{business_id}.tokens.json", {})
        try:
            import keyring
            raw = keyring.get_password(QUICKBOOKS_TOKEN_KEYCHAIN_SERVICE, business_id)
            return json.loads(raw) if raw else {}
        except Exception:
            return {}


def _quickbooks_redirect_uri() -> str:
    return str(
        os.getenv("QUICKBOOKS_ONLINE_REDIRECT_URI")
        or "http://localhost:8080/api/aion/integrations/quickbooks-online/callback"
    ).strip()


def _quickbooks_sandbox() -> bool:
    return str(os.getenv("QUICKBOOKS_ONLINE_ENVIRONMENT") or "sandbox").strip().lower() != "production"


def _quickbooks_public_connection(business_id: str) -> Dict[str, Any]:
    value = _read_json(_quickbooks_connection_path(business_id), {})
    client_id, client_secret = _quickbooks_app_credentials()
    connected = value.get("status") == "connected"
    return {
        "provider": "quickbooks_online",
        "business_id": business_id,
        "configured": bool(client_id and client_secret),
        "environment": "sandbox" if _quickbooks_sandbox() else "production",
        "status": value.get("status") or "not_connected",
        "connected": connected,
        "realm_id": value.get("realm_id"),
        "scope": value.get("scope"),
        "read_only": not connected,
        "external_writes_enabled": False,
        "write_mode": "approval_and_provider_readback_required",
        "connected_at": value.get("connected_at"),
        "last_sync_at": value.get("last_sync_at"),
        "last_sync_status": value.get("last_sync_status") or "never_synced",
        "last_error": value.get("last_error"),
    }


async def _quickbooks_request_json(
    method: str, url: str, *, operation: str, timeout: float = 30.0, **kwargs: Any
) -> Any:
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.request(method, url, **kwargs)
    except (httpx.TimeoutException, httpx.TransportError) as exc:
        raise HTTPException(status_code=504, detail={
            "code": "quickbooks_provider_unavailable", "provider": "quickbooks_online",
            "operation": operation, "error_type": type(exc).__name__, "retryable": True,
        }) from exc
    if response.status_code >= 400:
        raise HTTPException(status_code=502, detail={
            "code": "quickbooks_provider_request_failed", "provider": "quickbooks_online",
            "operation": operation, "provider_status": response.status_code,
            "retryable": response.status_code == 429 or response.status_code >= 500,
        })
    try:
        return response.json()
    except ValueError as exc:
        raise HTTPException(status_code=502, detail={
            "code": "quickbooks_invalid_json", "provider": "quickbooks_online", "operation": operation,
        }) from exc


async def _quickbooks_token_request(data: Dict[str, str]) -> Dict[str, Any]:
    client_id, client_secret = _quickbooks_app_credentials()
    value = await _quickbooks_request_json(
        "POST", QUICKBOOKS_TOKEN_URL, operation="token_exchange", data=data,
        auth=(client_id, client_secret),
        headers={"Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"},
    )
    value["obtained_at"] = _now()
    value["expires_at"] = (
        datetime.now(UTC) + timedelta(seconds=max(30, int(value.get("expires_in") or 3600)))
    ).replace(microsecond=0).isoformat()
    if value.get("x_refresh_token_expires_in"):
        value["refresh_token_expires_at"] = (
            datetime.now(UTC) + timedelta(seconds=int(value["x_refresh_token_expires_in"]))
        ).replace(microsecond=0).isoformat()
    return value


async def _quickbooks_valid_access_token(business_id: str) -> str:
    token = _QuickBooksTokenStore.load(business_id)
    if not token:
        raise HTTPException(status_code=409, detail="quickbooks_online_not_connected")
    try:
        valid = datetime.fromisoformat(str(token.get("expires_at") or "").replace("Z", "+00:00")) > datetime.now(UTC) + timedelta(seconds=45)
    except ValueError:
        valid = False
    if valid and token.get("access_token"):
        return str(token["access_token"])
    refresh_token = str(token.get("refresh_token") or "")
    client_id, client_secret = _quickbooks_app_credentials()
    if not refresh_token or not client_id or not client_secret:
        raise HTTPException(status_code=409, detail="quickbooks_online_reconnect_required")
    refreshed = await _quickbooks_token_request({
        "grant_type": "refresh_token", "refresh_token": refresh_token,
    })
    if not refreshed.get("refresh_token"):
        refreshed["refresh_token"] = refresh_token
    _QuickBooksTokenStore.save(business_id, refreshed)
    return str(refreshed.get("access_token") or "")


def _zoho_books_accounts_domain() -> str:
    domain = str(os.getenv("ZOHO_BOOKS_ACCOUNTS_DOMAIN") or "https://accounts.zoho.eu").strip().rstrip("/")
    if not domain.startswith("https://"):
        raise RuntimeError("zoho_books_accounts_domain_must_be_https")
    return domain


def _zoho_books_default_api_domain() -> str:
    domain = str(os.getenv("ZOHO_BOOKS_API_DOMAIN") or "https://www.zohoapis.eu").strip().rstrip("/")
    if not domain.startswith("https://"):
        raise RuntimeError("zoho_books_api_domain_must_be_https")
    return domain


def _zoho_books_app_credentials() -> tuple[str, str]:
    """Load the Zoho developer application credentials without exposing them."""
    client_id = str(os.getenv("ZOHO_BOOKS_CLIENT_ID") or "").strip()
    client_secret = str(os.getenv("ZOHO_BOOKS_CLIENT_SECRET") or "").strip()
    if client_id and client_secret:
        return client_id, client_secret

    def keychain_value(account: str) -> str:
        try:
            result = subprocess.run(
                ["/usr/bin/security", "find-generic-password", "-w", "-s", ZOHO_BOOKS_APP_KEYCHAIN_SERVICE, "-a", account],
                capture_output=True, text=True, check=False, timeout=5,
            )
            return result.stdout.strip() if result.returncode == 0 else ""
        except (OSError, subprocess.SubprocessError):
            return ""

    return keychain_value("client_id"), keychain_value("client_secret")


class _ZohoBooksTokenStore:
    @staticmethod
    def save(business_id: str, payload: Dict[str, Any]) -> str:
        test_dir = str(os.getenv("AION_ZOHO_BOOKS_TOKEN_STORE_DIR") or "").strip()
        if test_dir:
            path = Path(test_dir) / f"{business_id}.tokens.json"
            _write_json(path, payload)
            return f"test-secret-file://{path}"
        try:
            import keyring
            keyring.set_password(ZOHO_BOOKS_TOKEN_KEYCHAIN_SERVICE, business_id, json.dumps(payload))
        except Exception as exc:
            raise RuntimeError("macOS Keychain is unavailable; install the keyring dependency") from exc
        return f"keychain://{ZOHO_BOOKS_TOKEN_KEYCHAIN_SERVICE}/{business_id}"

    @staticmethod
    def load(business_id: str) -> Dict[str, Any]:
        test_dir = str(os.getenv("AION_ZOHO_BOOKS_TOKEN_STORE_DIR") or "").strip()
        if test_dir:
            return _read_json(Path(test_dir) / f"{business_id}.tokens.json", {})
        try:
            import keyring
            raw = keyring.get_password(ZOHO_BOOKS_TOKEN_KEYCHAIN_SERVICE, business_id)
            return json.loads(raw) if raw else {}
        except Exception:
            return {}


def _zoho_books_redirect_uri() -> str:
    return str(
        os.getenv("ZOHO_BOOKS_REDIRECT_URI")
        or "http://localhost:8080/api/aion/integrations/zoho-books/callback"
    ).strip()


def _zoho_books_public_connection(business_id: str) -> Dict[str, Any]:
    value = _read_json(_zoho_books_connection_path(business_id), {})
    client_id, client_secret = _zoho_books_app_credentials()
    connected = value.get("status") == "connected"
    return {
        "provider": "zoho_books",
        "business_id": business_id,
        "configured": bool(client_id and client_secret),
        "region": "eu" if _zoho_books_accounts_domain().endswith(".eu") else "custom",
        "status": value.get("status") or "not_connected",
        "connected": connected,
        "organization_id": value.get("organization_id"),
        "organization_name": value.get("organization_name"),
        "available_organizations": value.get("available_organizations") or [],
        "api_domain": value.get("api_domain") or _zoho_books_default_api_domain(),
        "scope": value.get("scope"),
        "read_only": True,
        "external_writes_enabled": False,
        "write_mode": "approval_and_provider_readback_required",
        "connected_at": value.get("connected_at"),
        "last_sync_at": value.get("last_sync_at"),
        "last_sync_status": value.get("last_sync_status") or "never_synced",
        "last_error": value.get("last_error"),
    }


async def _zoho_books_request_json(
    method: str, url: str, *, operation: str, timeout: float = 30.0, **kwargs: Any
) -> Any:
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.request(method, url, **kwargs)
    except (httpx.TimeoutException, httpx.TransportError) as exc:
        raise HTTPException(status_code=504, detail={
            "code": "zoho_books_provider_unavailable", "provider": "zoho_books",
            "operation": operation, "error_type": type(exc).__name__, "retryable": True,
        }) from exc
    if response.status_code >= 400:
        raise HTTPException(status_code=502, detail={
            "code": "zoho_books_provider_request_failed", "provider": "zoho_books",
            "operation": operation, "provider_status": response.status_code,
            "retryable": response.status_code == 429 or response.status_code >= 500,
        })
    try:
        return response.json()
    except ValueError as exc:
        raise HTTPException(status_code=502, detail={
            "code": "zoho_books_invalid_json", "provider": "zoho_books", "operation": operation,
        }) from exc


async def _zoho_books_token_request(data: Dict[str, str]) -> Dict[str, Any]:
    value = await _zoho_books_request_json(
        "POST", f"{_zoho_books_accounts_domain()}/oauth/v2/token", operation="token_exchange",
        data=data, headers={"Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"},
    )
    value["obtained_at"] = _now()
    value["expires_at"] = (
        datetime.now(UTC) + timedelta(seconds=max(30, int(value.get("expires_in") or 3600)))
    ).replace(microsecond=0).isoformat()
    value["api_domain"] = str(value.get("api_domain") or _zoho_books_default_api_domain()).rstrip("/")
    return value


async def _zoho_books_valid_access_token(business_id: str) -> tuple[str, str]:
    token = _ZohoBooksTokenStore.load(business_id)
    if not token:
        raise HTTPException(status_code=409, detail="zoho_books_not_connected")
    try:
        valid = datetime.fromisoformat(str(token.get("expires_at") or "").replace("Z", "+00:00")) > datetime.now(UTC) + timedelta(seconds=45)
    except ValueError:
        valid = False
    api_domain = str(token.get("api_domain") or _zoho_books_default_api_domain()).rstrip("/")
    if valid and token.get("access_token"):
        return str(token["access_token"]), api_domain
    refresh_token = str(token.get("refresh_token") or "")
    client_id, client_secret = _zoho_books_app_credentials()
    if not refresh_token or not client_id or not client_secret:
        raise HTTPException(status_code=409, detail="zoho_books_reconnect_required")
    refreshed = await _zoho_books_token_request({
        "grant_type": "refresh_token", "refresh_token": refresh_token,
        "client_id": client_id, "client_secret": client_secret,
    })
    if not refreshed.get("refresh_token"):
        refreshed["refresh_token"] = refresh_token
    _ZohoBooksTokenStore.save(business_id, refreshed)
    return str(refreshed.get("access_token") or ""), str(refreshed.get("api_domain") or api_domain).rstrip("/")


async def _zoho_books_organizations(access_token: str, api_domain: str) -> list[Dict[str, Any]]:
    value = await _zoho_books_request_json(
        "GET", f"{api_domain.rstrip('/')}/books/v3/organizations", operation="organizations",
        headers={"Authorization": f"Zoho-oauthtoken {access_token}", "Accept": "application/json"},
    )
    items = value.get("organizations") or [] if isinstance(value, dict) else []
    return [
        {
            "organization_id": str(item.get("organization_id") or ""),
            "organization_name": item.get("name") or item.get("organization_name"),
            "currency_code": item.get("currency_code"),
            "country_code": item.get("country_code"),
        }
        for item in items if item.get("organization_id")
    ]


def _freeagent_sandbox() -> bool:
    return str(os.getenv("FREEAGENT_ENVIRONMENT") or "production").strip().lower() == "sandbox"


def _freeagent_base_url() -> str:
    return "https://api.sandbox.freeagent.com/v2" if _freeagent_sandbox() else "https://api.freeagent.com/v2"


def _freeagent_app_credentials() -> tuple[str, str]:
    client_id = str(os.getenv("FREEAGENT_CLIENT_ID") or "").strip()
    client_secret = str(os.getenv("FREEAGENT_CLIENT_SECRET") or "").strip()
    if client_id and client_secret:
        return client_id, client_secret

    def keychain_value(account: str) -> str:
        try:
            result = subprocess.run(
                ["/usr/bin/security", "find-generic-password", "-w", "-s", FREEAGENT_APP_KEYCHAIN_SERVICE, "-a", account],
                capture_output=True, text=True, check=False, timeout=5,
            )
            return result.stdout.strip() if result.returncode == 0 else ""
        except (OSError, subprocess.SubprocessError):
            return ""

    return keychain_value("client_id"), keychain_value("client_secret")


class _FreeAgentTokenStore:
    @staticmethod
    def save(business_id: str, payload: Dict[str, Any]) -> str:
        test_dir = str(os.getenv("AION_FREEAGENT_TOKEN_STORE_DIR") or "").strip()
        if test_dir:
            path = Path(test_dir) / f"{business_id}.tokens.json"
            _write_json(path, payload)
            return f"test-secret-file://{path}"
        try:
            import keyring
            keyring.set_password(FREEAGENT_TOKEN_KEYCHAIN_SERVICE, business_id, json.dumps(payload))
        except Exception as exc:
            raise RuntimeError("macOS Keychain is unavailable; install the keyring dependency") from exc
        return f"keychain://{FREEAGENT_TOKEN_KEYCHAIN_SERVICE}/{business_id}"

    @staticmethod
    def load(business_id: str) -> Dict[str, Any]:
        test_dir = str(os.getenv("AION_FREEAGENT_TOKEN_STORE_DIR") or "").strip()
        if test_dir:
            return _read_json(Path(test_dir) / f"{business_id}.tokens.json", {})
        try:
            import keyring
            raw = keyring.get_password(FREEAGENT_TOKEN_KEYCHAIN_SERVICE, business_id)
            return json.loads(raw) if raw else {}
        except Exception:
            return {}


def _freeagent_redirect_uri() -> str:
    return str(
        os.getenv("FREEAGENT_REDIRECT_URI")
        or "http://localhost:8080/api/aion/integrations/freeagent/callback"
    ).strip()


def _freeagent_public_connection(business_id: str) -> Dict[str, Any]:
    value = _read_json(_freeagent_connection_path(business_id), {})
    client_id, client_secret = _freeagent_app_credentials()
    connected = value.get("status") == "connected"
    return {
        "provider": "freeagent",
        "business_id": business_id,
        "configured": bool(client_id and client_secret),
        "environment": "sandbox" if _freeagent_sandbox() else "production",
        "status": value.get("status") or "not_connected",
        "connected": connected,
        "company_id": value.get("company_id"),
        "company_name": value.get("company_name"),
        "company_subdomain": value.get("company_subdomain"),
        "currency": value.get("currency"),
        "read_only": True,
        "external_writes_enabled": False,
        "write_mode": "approval_and_provider_readback_required",
        "connected_at": value.get("connected_at"),
        "last_sync_at": value.get("last_sync_at"),
        "last_sync_status": value.get("last_sync_status") or "never_synced",
        "last_error": value.get("last_error"),
    }


async def _freeagent_request_json(
    method: str, url: str, *, operation: str, timeout: float = 30.0, **kwargs: Any
) -> Any:
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.request(method, url, **kwargs)
    except (httpx.TimeoutException, httpx.TransportError) as exc:
        raise HTTPException(status_code=504, detail={
            "code": "freeagent_provider_unavailable", "provider": "freeagent",
            "operation": operation, "error_type": type(exc).__name__, "retryable": True,
        }) from exc
    if response.status_code >= 400:
        raise HTTPException(status_code=502, detail={
            "code": "freeagent_provider_request_failed", "provider": "freeagent",
            "operation": operation, "provider_status": response.status_code,
            "retryable": response.status_code == 429 or response.status_code >= 500,
        })
    try:
        return response.json()
    except ValueError as exc:
        raise HTTPException(status_code=502, detail={
            "code": "freeagent_invalid_json", "provider": "freeagent", "operation": operation,
        }) from exc


async def _freeagent_token_request(data: Dict[str, str]) -> Dict[str, Any]:
    client_id, client_secret = _freeagent_app_credentials()
    value = await _freeagent_request_json(
        "POST", f"{_freeagent_base_url()}/token_endpoint", operation="token_exchange",
        data=data, auth=(client_id, client_secret),
        headers={"Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"},
    )
    value["obtained_at"] = _now()
    value["expires_at"] = (
        datetime.now(UTC) + timedelta(seconds=max(30, int(value.get("expires_in") or 3600)))
    ).replace(microsecond=0).isoformat()
    if value.get("refresh_token_expires_in"):
        value["refresh_token_expires_at"] = (
            datetime.now(UTC) + timedelta(seconds=int(value["refresh_token_expires_in"]))
        ).replace(microsecond=0).isoformat()
    return value


async def _freeagent_valid_access_token(business_id: str) -> str:
    token = _FreeAgentTokenStore.load(business_id)
    if not token:
        raise HTTPException(status_code=409, detail="freeagent_not_connected")
    try:
        valid = datetime.fromisoformat(str(token.get("expires_at") or "").replace("Z", "+00:00")) > datetime.now(UTC) + timedelta(seconds=45)
    except ValueError:
        valid = False
    if valid and token.get("access_token"):
        return str(token["access_token"])
    refresh_token = str(token.get("refresh_token") or "")
    client_id, client_secret = _freeagent_app_credentials()
    if not refresh_token or not client_id or not client_secret:
        raise HTTPException(status_code=409, detail="freeagent_reconnect_required")
    refreshed = await _freeagent_token_request({
        "grant_type": "refresh_token", "refresh_token": refresh_token,
    })
    if not refreshed.get("refresh_token"):
        refreshed["refresh_token"] = refresh_token
    _FreeAgentTokenStore.save(business_id, refreshed)
    return str(refreshed.get("access_token") or "")


async def _freeagent_company(access_token: str) -> Dict[str, Any]:
    value = await _freeagent_request_json(
        "GET", f"{_freeagent_base_url()}/company", operation="company",
        headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
    )
    company = value.get("company") or {} if isinstance(value, dict) else {}
    return {
        "company_id": str(company.get("id") or ""),
        "company_name": company.get("name"),
        "company_subdomain": company.get("subdomain"),
        "currency": company.get("currency"),
        "company_type": company.get("type"),
    }


def _freshbooks_app_credentials() -> tuple[str, str]:
    client_id = str(os.getenv("FRESHBOOKS_CLIENT_ID") or "").strip()
    client_secret = str(os.getenv("FRESHBOOKS_CLIENT_SECRET") or "").strip()
    if client_id and client_secret:
        return client_id, client_secret

    def keychain_value(account: str) -> str:
        try:
            result = subprocess.run(
                ["/usr/bin/security", "find-generic-password", "-w", "-s", FRESHBOOKS_APP_KEYCHAIN_SERVICE, "-a", account],
                capture_output=True, text=True, check=False, timeout=5,
            )
            return result.stdout.strip() if result.returncode == 0 else ""
        except (OSError, subprocess.SubprocessError):
            return ""

    return keychain_value("client_id"), keychain_value("client_secret")


class _FreshBooksTokenStore:
    @staticmethod
    def save(business_id: str, payload: Dict[str, Any]) -> str:
        test_dir = str(os.getenv("AION_FRESHBOOKS_TOKEN_STORE_DIR") or "").strip()
        if test_dir:
            path = Path(test_dir) / f"{business_id}.tokens.json"
            _write_json(path, payload)
            return f"test-secret-file://{path}"
        try:
            import keyring
            keyring.set_password(FRESHBOOKS_TOKEN_KEYCHAIN_SERVICE, business_id, json.dumps(payload))
        except Exception as exc:
            raise RuntimeError("macOS Keychain is unavailable; install the keyring dependency") from exc
        return f"keychain://{FRESHBOOKS_TOKEN_KEYCHAIN_SERVICE}/{business_id}"

    @staticmethod
    def load(business_id: str) -> Dict[str, Any]:
        test_dir = str(os.getenv("AION_FRESHBOOKS_TOKEN_STORE_DIR") or "").strip()
        if test_dir:
            return _read_json(Path(test_dir) / f"{business_id}.tokens.json", {})
        try:
            import keyring
            raw = keyring.get_password(FRESHBOOKS_TOKEN_KEYCHAIN_SERVICE, business_id)
            return json.loads(raw) if raw else {}
        except Exception:
            return {}


def _freshbooks_redirect_uri() -> str:
    return str(
        os.getenv("FRESHBOOKS_REDIRECT_URI")
        or "https://tessaris.ai/api/aion/integrations/freshbooks/callback"
    ).strip()


def _freshbooks_public_connection(business_id: str) -> Dict[str, Any]:
    value = _read_json(_freshbooks_connection_path(business_id), {})
    client_id, client_secret = _freshbooks_app_credentials()
    connected = value.get("status") == "connected"
    return {
        "provider": "freshbooks",
        "business_id": business_id,
        "configured": bool(client_id and client_secret),
        "status": value.get("status") or "not_connected",
        "connected": connected,
        "account_id": value.get("account_id"),
        "provider_business_id": value.get("provider_business_id"),
        "company_id": value.get("company_id"),
        "company_name": value.get("company_name"),
        "currency": value.get("currency"),
        "read_only": True,
        "external_writes_enabled": False,
        "write_mode": "approval_and_provider_readback_required",
        "connected_at": value.get("connected_at"),
        "last_sync_at": value.get("last_sync_at"),
        "last_sync_status": value.get("last_sync_status") or "never_synced",
        "last_error": value.get("last_error"),
    }


async def _freshbooks_request_json(
    method: str, url: str, *, operation: str, timeout: float = 30.0, **kwargs: Any
) -> Any:
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.request(method, url, **kwargs)
    except (httpx.TimeoutException, httpx.TransportError) as exc:
        raise HTTPException(status_code=504, detail={
            "code": "freshbooks_provider_unavailable", "provider": "freshbooks",
            "operation": operation, "error_type": type(exc).__name__, "retryable": True,
        }) from exc
    if response.status_code >= 400:
        raise HTTPException(status_code=502, detail={
            "code": "freshbooks_provider_request_failed", "provider": "freshbooks",
            "operation": operation, "provider_status": response.status_code,
            "retryable": response.status_code == 429 or response.status_code >= 500,
        })
    try:
        return response.json()
    except ValueError as exc:
        raise HTTPException(status_code=502, detail={
            "code": "freshbooks_invalid_json", "provider": "freshbooks", "operation": operation,
        }) from exc


async def _freshbooks_token_request(data: Dict[str, str]) -> Dict[str, Any]:
    value = await _freshbooks_request_json(
        "POST", FRESHBOOKS_TOKEN_URL, operation="token_exchange", json=data,
        headers={"Accept": "application/json", "Content-Type": "application/json"},
    )
    value["obtained_at"] = _now()
    value["expires_at"] = (
        datetime.now(UTC) + timedelta(seconds=max(30, int(value.get("expires_in") or 3600)))
    ).replace(microsecond=0).isoformat()
    return value


async def _freshbooks_valid_access_token(business_id: str) -> str:
    token = _FreshBooksTokenStore.load(business_id)
    if not token:
        raise HTTPException(status_code=409, detail="freshbooks_not_connected")
    try:
        valid = datetime.fromisoformat(str(token.get("expires_at") or "").replace("Z", "+00:00")) > datetime.now(UTC) + timedelta(seconds=45)
    except ValueError:
        valid = False
    if valid and token.get("access_token"):
        return str(token["access_token"])
    refresh_token = str(token.get("refresh_token") or "")
    client_id, client_secret = _freshbooks_app_credentials()
    if not refresh_token or not client_id or not client_secret:
        raise HTTPException(status_code=409, detail="freshbooks_reconnect_required")
    refreshed = await _freshbooks_token_request({
        "grant_type": "refresh_token",
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "redirect_uri": _freshbooks_redirect_uri(),
    })
    _FreshBooksTokenStore.save(business_id, refreshed)
    return str(refreshed.get("access_token") or "")


async def _freshbooks_businesses(access_token: str) -> list[Dict[str, Any]]:
    value = await _freshbooks_request_json(
        "GET", FRESHBOOKS_IDENTITY_URL, operation="identity",
        headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
    )
    response = value.get("response") or {} if isinstance(value, dict) else {}
    memberships = response.get("business_memberships") or []
    result: list[Dict[str, Any]] = []
    for membership in memberships:
        business = membership.get("business") or {}
        account_id = str(business.get("account_id") or membership.get("account_id") or "")
        # FreshBooks exposes both a numeric business ID and the UUID required by
        # business-scoped accounting/report endpoints.  Keep the UUID in the
        # governed company identifier so Chart of Accounts and ledger reports
        # are addressed correctly.
        provider_business_id = str(
            business.get("business_uuid")
            or business.get("uuid")
            or business.get("id")
            or business.get("business_id")
            or ""
        )
        if not account_id:
            continue
        result.append({
            "account_id": account_id,
            "provider_business_id": provider_business_id,
            "company_id": account_id + (f"|{provider_business_id}" if provider_business_id else ""),
            "company_name": business.get("name") or business.get("business_name") or membership.get("role"),
            "currency": business.get("currency_code") or business.get("currency"),
        })
    return result


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


@router.get("/sage-accounting/{candidate}/status")
def sage_accounting_status(candidate: str) -> Dict[str, Any]:
    business_id = canonical_business_id(candidate)
    return {"ok": True, "connection": _sage_public_connection(business_id)}


@router.get("/sage-accounting/{candidate}/connect")
@router.post("/sage-accounting/{candidate}/connect")
def sage_accounting_connect(candidate: str) -> Dict[str, Any]:
    business_id = canonical_business_id(candidate)
    client_id, client_secret = _sage_app_credentials()
    if not client_id or not client_secret:
        return {
            "ok": False,
            "reason": "sage_accounting_oauth_config_missing",
            "message": "Store the Sage Accounting Client ID and Client Secret in Tessaris Vault.",
            "redirect_uri": _sage_redirect_uri(),
            "connection": _sage_public_connection(business_id),
        }
    state = secrets.token_urlsafe(32)
    pending = {
        "business_id": business_id,
        "state": state,
        "created_at": _now(),
        "redirect_uri": _sage_redirect_uri(),
        "previous_connection": _read_json(_sage_connection_path(business_id), {}),
    }
    _write_json(_sage_integration_dir(business_id) / "oauth_pending.json", pending)
    connection = _read_json(_sage_connection_path(business_id), {})
    connection.update({"status": "awaiting_authorisation", "last_error": None})
    _write_json(_sage_connection_path(business_id), connection)
    params = {
        "filter": "apiv3.1",
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": _sage_redirect_uri(),
        "scope": SAGE_SCOPE,
        "state": state,
    }
    return {
        "ok": True,
        "connect_url": SAGE_AUTHORIZE_URL + "?" + urlencode(params),
        "redirect_uri": _sage_redirect_uri(),
        "connection": _sage_public_connection(business_id),
    }


@router.get("/sage-accounting/callback", response_class=HTMLResponse)
async def sage_accounting_callback(
    code: str = Query(default=""),
    state: str = Query(default=""),
    error: str = Query(default=""),
) -> HTMLResponse:
    pending_match: tuple[str, Dict[str, Any], Path] | None = None
    root = AIONBusinessPaths.BUSINESS_CONTAINERS
    for path in root.glob("*/integrations/sage_accounting/oauth_pending.json"):
        pending = _read_json(path, {})
        if secrets.compare_digest(str(pending.get("state") or ""), state):
            pending_match = (str(pending.get("business_id") or path.parents[2].name), pending, path)
            break
    if not pending_match:
        return HTMLResponse(
            "<h2>Sage connection failed</h2><p>The OAuth state was not recognised. Return to Tessaris and try again.</p>",
            status_code=400,
        )
    business_id, pending, pending_path = pending_match
    if error or not code:
        previous = pending.get("previous_connection") or {}
        connection = dict(previous)
        connection.update({
            "status": previous.get("status") or "not_connected",
            "last_error": error or "missing_authorisation_code",
        })
        _write_json(_sage_connection_path(business_id), connection)
        pending_path.unlink(missing_ok=True)
        return HTMLResponse(
            "<h2>Sage connection was not completed</h2><p>You can close this window and return to Tessaris.</p>",
            status_code=400,
        )
    client_id, client_secret = _sage_app_credentials()
    token = await _sage_token_request({
        "grant_type": "authorization_code",
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": str(pending.get("redirect_uri") or _sage_redirect_uri()),
    })
    secret_ref = _SageTokenStore.save(business_id, token)
    businesses = await _sage_businesses(str(token.get("access_token") or ""))
    selected = businesses[0] if len(businesses) == 1 else {}
    connection = {
        **(pending.get("previous_connection") or {}),
        "provider": "sage_accounting",
        "business_id": business_id,
        "status": "connected" if selected else "business_selection_required",
        "sage_business_id": selected.get("business_id"),
        "sage_business_name": selected.get("business_name"),
        "available_businesses": businesses,
        "scope": token.get("scope") or SAGE_SCOPE,
        "secret_ref": secret_ref,
        "connected_at": _now(),
        "last_sync_status": "never_synced",
        "last_error": None,
    }
    _write_json(_sage_connection_path(business_id), connection)
    pending_path.unlink(missing_ok=True)
    message = (
        f"Connected to {selected.get('business_name')}."
        if selected else "Authorised. Select the Sage business in Tessaris."
    )
    return HTMLResponse(
        f"<h2>Sage Accounting connected to Tessaris</h2><p>{message}</p>"
        "<p>You can close this window and return to Finance.</p>"
    )


class SageBusinessSelection(BaseModel):
    business_id: str


@router.post("/sage-accounting/{candidate}/business")
async def select_sage_accounting_business(
    candidate: str, request: SageBusinessSelection
) -> Dict[str, Any]:
    business_id = canonical_business_id(candidate)
    access_token = await _sage_valid_access_token(business_id)
    businesses = await _sage_businesses(access_token)
    selected = next((item for item in businesses if item.get("business_id") == request.business_id), None)
    if not selected:
        raise HTTPException(status_code=404, detail="sage_accounting_business_not_found")
    connection = _read_json(_sage_connection_path(business_id), {})
    connection.update({
        "status": "connected",
        "sage_business_id": selected["business_id"],
        "sage_business_name": selected.get("business_name"),
        "available_businesses": businesses,
        "last_error": None,
    })
    _write_json(_sage_connection_path(business_id), connection)
    return {"ok": True, "connection": _sage_public_connection(business_id)}


@router.post("/sage-accounting/{candidate}/sync-read-snapshot")
async def sync_sage_accounting_snapshot(candidate: str) -> Dict[str, Any]:
    business_id = canonical_business_id(candidate)
    connection = _read_json(_sage_connection_path(business_id), {})
    sage_business_id = str(connection.get("sage_business_id") or "")
    if connection.get("status") != "connected" or not sage_business_id:
        raise HTTPException(status_code=409, detail="sage_accounting_business_selection_required")
    access_token = await _sage_valid_access_token(business_id)
    try:
        raw = await SageAccountingAdapter().read_snapshot(
            access_token=access_token, company_id=sage_business_id
        )
        result = AccountantHarnessService().ingest(
            business_id, "sage_accounting", raw,
            company_id=sage_business_id, actor="finance_pilot",
        )
    except (httpx.HTTPError, ValueError) as exc:
        connection.update({"last_sync_status": "failed", "last_error": type(exc).__name__})
        _write_json(_sage_connection_path(business_id), connection)
        raise HTTPException(status_code=502, detail={
            "code": "sage_accounting_sync_failed", "error_type": type(exc).__name__,
        }) from exc
    connection.update({"last_sync_at": _now(), "last_sync_status": "succeeded", "last_error": None})
    _write_json(_sage_connection_path(business_id), connection)
    return {
        "ok": True,
        "provider": "sage_accounting",
        "business_id": business_id,
        "sage_business_id": sage_business_id,
        "sync": result,
        "external_write_performed": False,
    }


@router.get("/quickbooks-online/{candidate}/status")
def quickbooks_online_status(candidate: str) -> Dict[str, Any]:
    business_id = canonical_business_id(candidate)
    return {"ok": True, "connection": _quickbooks_public_connection(business_id)}


@router.get("/quickbooks-online/{candidate}/connect")
@router.post("/quickbooks-online/{candidate}/connect")
def quickbooks_online_connect(candidate: str) -> Dict[str, Any]:
    business_id = canonical_business_id(candidate)
    client_id, client_secret = _quickbooks_app_credentials()
    if not client_id or not client_secret:
        return {
            "ok": False,
            "reason": "quickbooks_online_oauth_config_missing",
            "message": "Store the QuickBooks Online Client ID and Client Secret in Tessaris Vault.",
            "redirect_uri": _quickbooks_redirect_uri(),
            "connection": _quickbooks_public_connection(business_id),
        }
    state = secrets.token_urlsafe(32)
    pending = {
        "business_id": business_id,
        "state": state,
        "created_at": _now(),
        "redirect_uri": _quickbooks_redirect_uri(),
        "previous_connection": _read_json(_quickbooks_connection_path(business_id), {}),
    }
    _write_json(_quickbooks_integration_dir(business_id) / "oauth_pending.json", pending)
    connection = _read_json(_quickbooks_connection_path(business_id), {})
    connection.update({"status": "awaiting_authorisation", "last_error": None})
    _write_json(_quickbooks_connection_path(business_id), connection)
    params = {
        "client_id": client_id,
        "response_type": "code",
        "scope": QUICKBOOKS_SCOPE,
        "redirect_uri": _quickbooks_redirect_uri(),
        "state": state,
    }
    return {
        "ok": True,
        "connect_url": QUICKBOOKS_AUTHORIZE_URL + "?" + urlencode(params),
        "redirect_uri": _quickbooks_redirect_uri(),
        "connection": _quickbooks_public_connection(business_id),
    }


@router.get("/quickbooks-online/callback", response_class=HTMLResponse)
async def quickbooks_online_callback(
    code: str = Query(default=""),
    state: str = Query(default=""),
    realmId: str = Query(default=""),
    error: str = Query(default=""),
) -> HTMLResponse:
    pending_match: tuple[str, Dict[str, Any], Path] | None = None
    root = AIONBusinessPaths.BUSINESS_CONTAINERS
    for path in root.glob("*/integrations/quickbooks_online/oauth_pending.json"):
        pending = _read_json(path, {})
        if secrets.compare_digest(str(pending.get("state") or ""), state):
            pending_match = (str(pending.get("business_id") or path.parents[2].name), pending, path)
            break
    if not pending_match:
        return HTMLResponse(
            "<h2>QuickBooks connection failed</h2><p>The OAuth state was not recognised. Return to Tessaris and try again.</p>",
            status_code=400,
        )
    business_id, pending, pending_path = pending_match
    if error or not code or not realmId:
        previous = pending.get("previous_connection") or {}
        connection = dict(previous)
        connection.update({
            "status": previous.get("status") or "not_connected",
            "last_error": error or "missing_authorisation_code_or_realm",
        })
        _write_json(_quickbooks_connection_path(business_id), connection)
        pending_path.unlink(missing_ok=True)
        return HTMLResponse(
            "<h2>QuickBooks connection was not completed</h2><p>You can close this window and return to Tessaris.</p>",
            status_code=400,
        )
    token = await _quickbooks_token_request({
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": str(pending.get("redirect_uri") or _quickbooks_redirect_uri()),
    })
    secret_ref = _QuickBooksTokenStore.save(business_id, token)
    connection = {
        **(pending.get("previous_connection") or {}),
        "provider": "quickbooks_online",
        "business_id": business_id,
        "status": "connected",
        "realm_id": realmId,
        "environment": "sandbox" if _quickbooks_sandbox() else "production",
        "scope": token.get("scope") or QUICKBOOKS_SCOPE,
        "secret_ref": secret_ref,
        "connected_at": _now(),
        "last_sync_status": "never_synced",
        "last_error": None,
    }
    _write_json(_quickbooks_connection_path(business_id), connection)
    pending_path.unlink(missing_ok=True)
    return HTMLResponse(
        "<h2>QuickBooks Online connected to Tessaris</h2>"
        "<p>The company is authorised for approval-gated accounting work.</p>"
        "<p>You can close this window and return to Finance.</p>"
    )


@router.post("/quickbooks-online/{candidate}/sync-read-snapshot")
async def sync_quickbooks_online_snapshot(candidate: str) -> Dict[str, Any]:
    business_id = canonical_business_id(candidate)
    connection = _read_json(_quickbooks_connection_path(business_id), {})
    realm_id = str(connection.get("realm_id") or "")
    if connection.get("status") != "connected" or not realm_id:
        raise HTTPException(status_code=409, detail="quickbooks_online_company_connection_required")
    access_token = await _quickbooks_valid_access_token(business_id)
    try:
        raw = await QuickBooksOnlineAccountingAdapter().read_snapshot(
            access_token=access_token, company_id=realm_id, sandbox=_quickbooks_sandbox()
        )
        result = AccountantHarnessService().ingest(
            business_id, "quickbooks_online", raw,
            company_id=realm_id, actor="finance_pilot",
        )
    except (httpx.HTTPError, ValueError) as exc:
        connection.update({"last_sync_status": "failed", "last_error": type(exc).__name__})
        _write_json(_quickbooks_connection_path(business_id), connection)
        raise HTTPException(status_code=502, detail={
            "code": "quickbooks_online_sync_failed", "error_type": type(exc).__name__,
        }) from exc
    connection.update({"last_sync_at": _now(), "last_sync_status": "succeeded", "last_error": None})
    _write_json(_quickbooks_connection_path(business_id), connection)
    return {
        "ok": True,
        "provider": "quickbooks_online",
        "business_id": business_id,
        "realm_id": realm_id,
        "environment": "sandbox" if _quickbooks_sandbox() else "production",
        "sync": result,
        "external_write_performed": False,
    }


@router.get("/zoho-books/{candidate}/status")
def zoho_books_status(candidate: str) -> Dict[str, Any]:
    business_id = canonical_business_id(candidate)
    return {"ok": True, "connection": _zoho_books_public_connection(business_id)}


@router.get("/zoho-books/{candidate}/connect")
@router.post("/zoho-books/{candidate}/connect")
def zoho_books_connect(candidate: str) -> Dict[str, Any]:
    business_id = canonical_business_id(candidate)
    client_id, client_secret = _zoho_books_app_credentials()
    if not client_id or not client_secret:
        return {
            "ok": False,
            "reason": "zoho_books_oauth_config_missing",
            "message": "Store the Zoho Books Client ID and Client Secret in Tessaris Vault.",
            "redirect_uri": _zoho_books_redirect_uri(),
            "connection": _zoho_books_public_connection(business_id),
        }
    state = secrets.token_urlsafe(32)
    pending = {
        "business_id": business_id,
        "state": state,
        "created_at": _now(),
        "redirect_uri": _zoho_books_redirect_uri(),
        "previous_connection": _read_json(_zoho_books_connection_path(business_id), {}),
    }
    _write_json(_zoho_books_integration_dir(business_id) / "oauth_pending.json", pending)
    connection = _read_json(_zoho_books_connection_path(business_id), {})
    connection.update({"status": "awaiting_authorisation", "last_error": None})
    _write_json(_zoho_books_connection_path(business_id), connection)
    params = {
        "client_id": client_id,
        "response_type": "code",
        "scope": ",".join(ZOHO_BOOKS_SCOPES),
        "redirect_uri": _zoho_books_redirect_uri(),
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    return {
        "ok": True,
        "connect_url": f"{_zoho_books_accounts_domain()}/oauth/v2/auth?" + urlencode(params),
        "redirect_uri": _zoho_books_redirect_uri(),
        "connection": _zoho_books_public_connection(business_id),
    }


@router.get("/zoho-books/callback", response_class=HTMLResponse)
async def zoho_books_callback(
    code: str = Query(default=""),
    state: str = Query(default=""),
    error: str = Query(default=""),
) -> HTMLResponse:
    pending_match: tuple[str, Dict[str, Any], Path] | None = None
    root = AIONBusinessPaths.BUSINESS_CONTAINERS
    for path in root.glob("*/integrations/zoho_books/oauth_pending.json"):
        pending = _read_json(path, {})
        if secrets.compare_digest(str(pending.get("state") or ""), state):
            pending_match = (str(pending.get("business_id") or path.parents[2].name), pending, path)
            break
    if not pending_match:
        return HTMLResponse(
            "<h2>Zoho Books connection failed</h2><p>The OAuth state was not recognised. Return to Tessaris and try again.</p>",
            status_code=400,
        )
    business_id, pending, pending_path = pending_match
    if error or not code:
        previous = pending.get("previous_connection") or {}
        connection = dict(previous)
        connection.update({
            "status": previous.get("status") or "not_connected",
            "last_error": error or "missing_authorisation_code",
        })
        _write_json(_zoho_books_connection_path(business_id), connection)
        pending_path.unlink(missing_ok=True)
        return HTMLResponse(
            "<h2>Zoho Books connection was not completed</h2><p>You can close this window and return to Tessaris.</p>",
            status_code=400,
        )
    client_id, client_secret = _zoho_books_app_credentials()
    token = await _zoho_books_token_request({
        "grant_type": "authorization_code",
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": str(pending.get("redirect_uri") or _zoho_books_redirect_uri()),
    })
    secret_ref = _ZohoBooksTokenStore.save(business_id, token)
    api_domain = str(token.get("api_domain") or _zoho_books_default_api_domain()).rstrip("/")
    organizations = await _zoho_books_organizations(str(token.get("access_token") or ""), api_domain)
    selected = organizations[0] if len(organizations) == 1 else {}
    connection = {
        **(pending.get("previous_connection") or {}),
        "provider": "zoho_books",
        "business_id": business_id,
        "status": "connected" if selected else "organization_selection_required",
        "organization_id": selected.get("organization_id"),
        "organization_name": selected.get("organization_name"),
        "available_organizations": organizations,
        "api_domain": api_domain,
        "scope": token.get("scope") or ",".join(ZOHO_BOOKS_SCOPES),
        "secret_ref": secret_ref,
        "connected_at": _now(),
        "last_sync_status": "never_synced",
        "last_error": None,
    }
    _write_json(_zoho_books_connection_path(business_id), connection)
    pending_path.unlink(missing_ok=True)
    message = (
        f"Connected to {selected.get('organization_name')}."
        if selected else "Authorised. Select the Zoho Books organisation in Tessaris."
    )
    return HTMLResponse(
        f"<h2>Zoho Books connected to Tessaris</h2><p>{message}</p>"
        "<p>You can close this window and return to Finance.</p>"
    )


class ZohoBooksOrganizationSelection(BaseModel):
    organization_id: str


@router.post("/zoho-books/{candidate}/organization")
async def select_zoho_books_organization(
    candidate: str, request: ZohoBooksOrganizationSelection
) -> Dict[str, Any]:
    business_id = canonical_business_id(candidate)
    access_token, api_domain = await _zoho_books_valid_access_token(business_id)
    organizations = await _zoho_books_organizations(access_token, api_domain)
    selected = next(
        (item for item in organizations if item.get("organization_id") == request.organization_id),
        None,
    )
    if not selected:
        raise HTTPException(status_code=404, detail="zoho_books_organization_not_found")
    connection = _read_json(_zoho_books_connection_path(business_id), {})
    connection.update({
        "status": "connected",
        "organization_id": selected["organization_id"],
        "organization_name": selected.get("organization_name"),
        "available_organizations": organizations,
        "api_domain": api_domain,
        "last_error": None,
    })
    _write_json(_zoho_books_connection_path(business_id), connection)
    return {"ok": True, "connection": _zoho_books_public_connection(business_id)}


@router.post("/zoho-books/{candidate}/sync-read-snapshot")
async def sync_zoho_books_snapshot(candidate: str) -> Dict[str, Any]:
    business_id = canonical_business_id(candidate)
    connection = _read_json(_zoho_books_connection_path(business_id), {})
    organization_id = str(connection.get("organization_id") or "")
    if connection.get("status") != "connected" or not organization_id:
        raise HTTPException(status_code=409, detail="zoho_books_organization_selection_required")
    access_token, api_domain = await _zoho_books_valid_access_token(business_id)
    company_id = f"{organization_id}|{api_domain}"
    try:
        raw = await ZohoBooksAccountingAdapter().read_snapshot(
            access_token=access_token, company_id=company_id
        )
        result = AccountantHarnessService().ingest(
            business_id, "zoho_books", raw,
            company_id=company_id, actor="finance_pilot",
        )
    except (httpx.HTTPError, ValueError) as exc:
        connection.update({"last_sync_status": "failed", "last_error": type(exc).__name__})
        _write_json(_zoho_books_connection_path(business_id), connection)
        raise HTTPException(status_code=502, detail={
            "code": "zoho_books_sync_failed", "error_type": type(exc).__name__,
        }) from exc
    connection.update({
        "api_domain": api_domain,
        "last_sync_at": _now(),
        "last_sync_status": "succeeded",
        "last_error": None,
    })
    _write_json(_zoho_books_connection_path(business_id), connection)
    return {
        "ok": True,
        "provider": "zoho_books",
        "business_id": business_id,
        "organization_id": organization_id,
        "api_domain": api_domain,
        "sync": result,
        "external_write_performed": False,
    }


@router.get("/freeagent/{candidate}/status")
def freeagent_status(candidate: str) -> Dict[str, Any]:
    business_id = canonical_business_id(candidate)
    return {"ok": True, "connection": _freeagent_public_connection(business_id)}


@router.get("/freeagent/{candidate}/connect")
@router.post("/freeagent/{candidate}/connect")
def freeagent_connect(candidate: str) -> Dict[str, Any]:
    business_id = canonical_business_id(candidate)
    client_id, client_secret = _freeagent_app_credentials()
    if not client_id or not client_secret:
        return {
            "ok": False,
            "reason": "freeagent_oauth_config_missing",
            "message": "Store the FreeAgent OAuth identifier and secret in Tessaris Vault.",
            "redirect_uri": _freeagent_redirect_uri(),
            "connection": _freeagent_public_connection(business_id),
        }
    state = secrets.token_urlsafe(32)
    pending = {
        "business_id": business_id,
        "state": state,
        "created_at": _now(),
        "redirect_uri": _freeagent_redirect_uri(),
        "previous_connection": _read_json(_freeagent_connection_path(business_id), {}),
    }
    _write_json(_freeagent_integration_dir(business_id) / "oauth_pending.json", pending)
    connection = _read_json(_freeagent_connection_path(business_id), {})
    connection.update({"status": "awaiting_authorisation", "last_error": None})
    _write_json(_freeagent_connection_path(business_id), connection)
    params = {
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": _freeagent_redirect_uri(),
        "state": state,
    }
    return {
        "ok": True,
        "connect_url": f"{_freeagent_base_url()}/approve_app?" + urlencode(params),
        "redirect_uri": _freeagent_redirect_uri(),
        "connection": _freeagent_public_connection(business_id),
    }


@router.get("/freeagent/callback", response_class=HTMLResponse)
async def freeagent_callback(
    code: str = Query(default=""),
    state: str = Query(default=""),
    error: str = Query(default=""),
) -> HTMLResponse:
    pending_match: tuple[str, Dict[str, Any], Path] | None = None
    root = AIONBusinessPaths.BUSINESS_CONTAINERS
    for path in root.glob("*/integrations/freeagent/oauth_pending.json"):
        pending = _read_json(path, {})
        if secrets.compare_digest(str(pending.get("state") or ""), state):
            pending_match = (str(pending.get("business_id") or path.parents[2].name), pending, path)
            break
    if not pending_match:
        return HTMLResponse(
            "<h2>FreeAgent connection failed</h2><p>The OAuth state was not recognised. Return to Tessaris and try again.</p>",
            status_code=400,
        )
    business_id, pending, pending_path = pending_match
    if error or not code:
        previous = pending.get("previous_connection") or {}
        connection = dict(previous)
        connection.update({
            "status": previous.get("status") or "not_connected",
            "last_error": error or "missing_authorisation_code",
        })
        _write_json(_freeagent_connection_path(business_id), connection)
        pending_path.unlink(missing_ok=True)
        return HTMLResponse(
            "<h2>FreeAgent connection was not completed</h2><p>You can close this window and return to Tessaris.</p>",
            status_code=400,
        )
    token = await _freeagent_token_request({
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": str(pending.get("redirect_uri") or _freeagent_redirect_uri()),
    })
    secret_ref = _FreeAgentTokenStore.save(business_id, token)
    company = await _freeagent_company(str(token.get("access_token") or ""))
    connection = {
        **(pending.get("previous_connection") or {}),
        "provider": "freeagent",
        "business_id": business_id,
        "status": "connected",
        **company,
        "environment": "sandbox" if _freeagent_sandbox() else "production",
        "secret_ref": secret_ref,
        "connected_at": _now(),
        "last_sync_status": "never_synced",
        "last_error": None,
    }
    _write_json(_freeagent_connection_path(business_id), connection)
    pending_path.unlink(missing_ok=True)
    return HTMLResponse(
        "<h2>FreeAgent connected to Tessaris</h2>"
        f"<p>Connected to {company.get('company_name') or 'the authorised company'}.</p>"
        "<p>You can close this window and return to Finance.</p>"
    )


@router.post("/freeagent/{candidate}/sync-read-snapshot")
async def sync_freeagent_snapshot(candidate: str) -> Dict[str, Any]:
    business_id = canonical_business_id(candidate)
    connection = _read_json(_freeagent_connection_path(business_id), {})
    company_id = str(connection.get("company_id") or "")
    if connection.get("status") != "connected":
        raise HTTPException(status_code=409, detail="freeagent_company_connection_required")
    access_token = await _freeagent_valid_access_token(business_id)
    try:
        raw = await FreeAgentAccountingAdapter().read_snapshot(
            access_token=access_token,
            company_id=company_id,
            sandbox=_freeagent_sandbox(),
        )
        result = AccountantHarnessService().ingest(
            business_id, "freeagent", raw,
            company_id=company_id or business_id, actor="finance_pilot",
        )
    except (httpx.HTTPError, ValueError) as exc:
        connection.update({"last_sync_status": "failed", "last_error": type(exc).__name__})
        _write_json(_freeagent_connection_path(business_id), connection)
        raise HTTPException(status_code=502, detail={
            "code": "freeagent_sync_failed", "error_type": type(exc).__name__,
        }) from exc
    connection.update({"last_sync_at": _now(), "last_sync_status": "succeeded", "last_error": None})
    _write_json(_freeagent_connection_path(business_id), connection)
    return {
        "ok": True,
        "provider": "freeagent",
        "business_id": business_id,
        "company_id": company_id,
        "environment": "sandbox" if _freeagent_sandbox() else "production",
        "sync": result,
        "external_write_performed": False,
    }


@router.get("/freshbooks/{candidate}/status")
def freshbooks_status(candidate: str) -> Dict[str, Any]:
    business_id = canonical_business_id(candidate)
    return {"ok": True, "connection": _freshbooks_public_connection(business_id)}


@router.get("/freshbooks/{candidate}/connect")
@router.post("/freshbooks/{candidate}/connect")
def freshbooks_connect(candidate: str) -> Dict[str, Any]:
    business_id = canonical_business_id(candidate)
    client_id, client_secret = _freshbooks_app_credentials()
    if not client_id or not client_secret:
        return {
            "ok": False,
            "reason": "freshbooks_oauth_config_missing",
            "message": "Store the FreshBooks client ID and secret in Tessaris Vault.",
            "redirect_uri": _freshbooks_redirect_uri(),
            "connection": _freshbooks_public_connection(business_id),
        }
    state = secrets.token_urlsafe(32)
    pending = {
        "business_id": business_id,
        "state": state,
        "created_at": _now(),
        "redirect_uri": _freshbooks_redirect_uri(),
        "previous_connection": _read_json(_freshbooks_connection_path(business_id), {}),
    }
    _write_json(_freshbooks_integration_dir(business_id) / "oauth_pending.json", pending)
    connection = _read_json(_freshbooks_connection_path(business_id), {})
    connection.update({"status": "awaiting_authorisation", "last_error": None})
    _write_json(_freshbooks_connection_path(business_id), connection)
    params = {
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": _freshbooks_redirect_uri(),
        "state": state,
        "scope": " ".join(FRESHBOOKS_SCOPES),
    }
    return {
        "ok": True,
        "connect_url": FRESHBOOKS_AUTHORIZE_URL + "?" + urlencode(params),
        "redirect_uri": _freshbooks_redirect_uri(),
        "connection": _freshbooks_public_connection(business_id),
    }


@router.get("/freshbooks/callback", response_class=HTMLResponse)
async def freshbooks_callback(
    code: str = Query(default=""),
    state: str = Query(default=""),
    error: str = Query(default=""),
) -> HTMLResponse:
    pending_match: tuple[str, Dict[str, Any], Path] | None = None
    root = AIONBusinessPaths.BUSINESS_CONTAINERS
    for path in root.glob("*/integrations/freshbooks/oauth_pending.json"):
        pending = _read_json(path, {})
        if secrets.compare_digest(str(pending.get("state") or ""), state):
            pending_match = (str(pending.get("business_id") or path.parents[2].name), pending, path)
            break
    if not pending_match:
        return HTMLResponse(
            "<h2>FreshBooks connection failed</h2><p>The OAuth state was not recognised. Return to Tessaris and try again.</p>",
            status_code=400,
        )
    business_id, pending, pending_path = pending_match
    if error or not code:
        previous = pending.get("previous_connection") or {}
        connection = dict(previous)
        connection.update({
            "status": previous.get("status") or "not_connected",
            "last_error": error or "missing_authorisation_code",
        })
        _write_json(_freshbooks_connection_path(business_id), connection)
        pending_path.unlink(missing_ok=True)
        return HTMLResponse(
            "<h2>FreshBooks connection was not completed</h2><p>You can close this window and return to Tessaris.</p>",
            status_code=400,
        )
    client_id, client_secret = _freshbooks_app_credentials()
    token = await _freshbooks_token_request({
        "grant_type": "authorization_code",
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "redirect_uri": str(pending.get("redirect_uri") or _freshbooks_redirect_uri()),
    })
    secret_ref = _FreshBooksTokenStore.save(business_id, token)
    businesses = await _freshbooks_businesses(str(token.get("access_token") or ""))
    selected = businesses[0] if len(businesses) == 1 else {}
    connection = {
        **(pending.get("previous_connection") or {}),
        "provider": "freshbooks",
        "business_id": business_id,
        "status": "connected" if selected else "business_selection_required",
        **selected,
        "available_businesses": businesses,
        "secret_ref": secret_ref,
        "connected_at": _now(),
        "last_sync_status": "never_synced",
        "last_error": None,
    }
    _write_json(_freshbooks_connection_path(business_id), connection)
    pending_path.unlink(missing_ok=True)
    message = (
        f"Connected to {selected.get('company_name') or 'the authorised business'}."
        if selected else "Authorised. Select the FreshBooks business in Tessaris."
    )
    return HTMLResponse(
        "<h2>FreshBooks connected to Tessaris</h2>"
        f"<p>{message}</p><p>You can close this window and return to Finance.</p>"
    )


class FreshBooksBusinessSelection(BaseModel):
    company_id: str


@router.post("/freshbooks/{candidate}/business")
async def select_freshbooks_business(
    candidate: str, request: FreshBooksBusinessSelection
) -> Dict[str, Any]:
    business_id = canonical_business_id(candidate)
    access_token = await _freshbooks_valid_access_token(business_id)
    businesses = await _freshbooks_businesses(access_token)
    selected = next((item for item in businesses if item.get("company_id") == request.company_id), None)
    if not selected:
        raise HTTPException(status_code=404, detail="freshbooks_business_not_found")
    connection = _read_json(_freshbooks_connection_path(business_id), {})
    connection.update({
        "status": "connected", **selected, "available_businesses": businesses,
        "last_error": None,
    })
    _write_json(_freshbooks_connection_path(business_id), connection)
    return {"ok": True, "connection": _freshbooks_public_connection(business_id)}


@router.post("/freshbooks/{candidate}/sync-read-snapshot")
async def sync_freshbooks_snapshot(candidate: str) -> Dict[str, Any]:
    business_id = canonical_business_id(candidate)
    connection = _read_json(_freshbooks_connection_path(business_id), {})
    company_id = str(connection.get("company_id") or "")
    if connection.get("status") != "connected" or not company_id:
        raise HTTPException(status_code=409, detail="freshbooks_business_connection_required")
    access_token = await _freshbooks_valid_access_token(business_id)
    try:
        raw = await FreshBooksAccountingAdapter().read_snapshot(
            access_token=access_token, company_id=company_id,
        )
        result = AccountantHarnessService().ingest(
            business_id, "freshbooks", raw,
            company_id=company_id, actor="finance_pilot",
        )
    except (httpx.HTTPError, ValueError) as exc:
        connection.update({"last_sync_status": "failed", "last_error": type(exc).__name__})
        _write_json(_freshbooks_connection_path(business_id), connection)
        raise HTTPException(status_code=502, detail={
            "code": "freshbooks_sync_failed", "error_type": type(exc).__name__,
        }) from exc
    connection.update({"last_sync_at": _now(), "last_sync_status": "succeeded", "last_error": None})
    _write_json(_freshbooks_connection_path(business_id), connection)
    return {
        "ok": True,
        "provider": "freshbooks",
        "business_id": business_id,
        "company_id": company_id,
        "sync": result,
        "external_write_performed": False,
    }


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
