"""Provider-neutral OAuth authority lifecycle with secrets outside the Business Vault."""

from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
import json
import os
from pathlib import Path
import secrets
import tempfile
from typing import Any

from backend.modules.aion_business.runtime.business_vault_runtime import (
    configured_business_vault_runtime,
    guardian_mode_requested,
)
from backend.modules.aion_business.runtime.canonical_business_identity import canonical_business_id
from backend.modules.aion_business.runtime.finance_integration_store import FinanceIntegrationStore
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _safe(value: str, label: str) -> str:
    clean = str(value or "").strip().lower().replace(" ", "_")
    if not clean or clean in {".", ".."} or any(
        char not in "abcdefghijklmnopqrstuvwxyz0123456789_.-" for char in clean
    ):
        raise ValueError(f"provider_connection_{label}_invalid")
    return clean


class ProviderAuthorityStore:
    """Keychain in production; isolated owner-private files in qualification/tests."""

    SERVICE = "com.tessaris.provider-authority"

    @classmethod
    def _account(cls, workspace_id: str, provider: str) -> str:
        return f"{canonical_business_id(workspace_id)}:{_safe(provider, 'provider')}"

    @classmethod
    def _test_path(cls, account: str) -> Path | None:
        root = str(os.getenv("TESSARIS_PROVIDER_SECRET_STORE_DIR") or "").strip()
        if not root and os.getenv("TESSARIS_DISCOVERY_MODE") == "1":
            try:
                roots = json.loads(os.getenv("TESSARIS_DISCOVERY_SECRET_STORE_ROOTS") or "[]")
            except json.JSONDecodeError:
                roots = []
            if isinstance(roots, list) and roots:
                root = str(Path(str(roots[0])) / "provider-authority")
        return Path(root) / f"{sha256(account.encode()).hexdigest()}.authority.json" if root else None

    @classmethod
    def save(cls, workspace_id: str, provider: str, payload: dict[str, Any]) -> str:
        account = cls._account(workspace_id, provider)
        path = cls._test_path(account)
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        if path is not None:
            path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            descriptor, name = tempfile.mkstemp(prefix=".provider-authority-", dir=path.parent)
            temporary = Path(name)
            try:
                with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                    stream.write(encoded)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.chmod(temporary, 0o600)
                os.replace(temporary, path)
                os.chmod(path, 0o600)
            finally:
                temporary.unlink(missing_ok=True)
            return "secret-store://provider-authority/" + sha256(account.encode()).hexdigest()
        import keyring
        keyring.set_password(cls.SERVICE, account, encoded)
        return f"keychain://{cls.SERVICE}/{sha256(account.encode()).hexdigest()}"

    @classmethod
    def load(cls, workspace_id: str, provider: str) -> dict[str, Any]:
        account = cls._account(workspace_id, provider)
        path = cls._test_path(account)
        if path is not None:
            try:
                value = json.loads(path.read_text(encoding="utf-8"))
                return value if isinstance(value, dict) else {}
            except (OSError, json.JSONDecodeError):
                return {}
        import keyring
        raw = keyring.get_password(cls.SERVICE, account)
        value = json.loads(raw) if raw else {}
        return value if isinstance(value, dict) else {}

    @classmethod
    def delete(cls, workspace_id: str, provider: str) -> None:
        account = cls._account(workspace_id, provider)
        path = cls._test_path(account)
        if path is not None:
            path.unlink(missing_ok=True)
            return
        import keyring
        try:
            keyring.delete_password(cls.SERVICE, account)
        except Exception:
            pass


class ProviderConnectionLifecycleService:
    """Persist public connection state and receipts without retaining authority material."""

    def __init__(self, *, domain_store: VaultDomainStore | None = None) -> None:
        self.domain_store = domain_store
        if domain_store is None and guardian_mode_requested():
            runtime = configured_business_vault_runtime()
            self.domain_store = VaultDomainStore(
                runtime.guardian, actor_id="provider-connection-runtime"
            )
        self.integrations = FinanceIntegrationStore(domain_store=self.domain_store)

    def status(self, workspace_id: str, provider: str) -> dict[str, Any]:
        workspace_id = canonical_business_id(workspace_id)
        provider = _safe(provider, "provider")
        value = self.integrations.read_json(
            self.integrations.root(workspace_id, provider) / "connection_lifecycle.json", {}
        )
        authority_present = bool(ProviderAuthorityStore.load(workspace_id, provider))
        state = str(value.get("status") or "not_connected")
        return {
            **value,
            "workspace_id": workspace_id,
            "provider": provider,
            "status": state,
            "connected": state == "connected" and authority_present,
            "authority_present": authority_present,
            "raw_tokens_exposed": False,
        }

    def connect(
        self, workspace_id: str, provider: str, *, authority: dict[str, Any],
        actor_id: str, granted_scopes: list[str], provider_account_hash: str,
    ) -> dict[str, Any]:
        workspace_id = canonical_business_id(workspace_id)
        provider = _safe(provider, "provider")
        if not str(authority.get("access_token") or ""):
            raise ValueError("provider_connection_access_token_required")
        previous = self.status(workspace_id, provider)
        generation = int(previous.get("generation") or 0) + 1
        secret_ref = ProviderAuthorityStore.save(workspace_id, provider, authority)
        record = {
            "schema_version": "tessaris.provider-connection-lifecycle.v1",
            "workspace_id": workspace_id,
            "provider": provider,
            "status": "connected",
            "generation": generation,
            "granted_scopes": sorted(set(str(item) for item in granted_scopes if str(item))),
            "provider_account_hash": str(provider_account_hash or "")[:128],
            "secret_storage": secret_ref.split("://", 1)[0],
            "connected_at": _now(),
            "connected_by": str(actor_id or "provider-adapter")[:160],
            "last_refresh_at": None,
            "revoked_at": None,
        }
        self._write(workspace_id, provider, record)
        self._receipt(workspace_id, provider, "connected", actor_id, generation)
        return self.status(workspace_id, provider)

    def refresh(
        self, workspace_id: str, provider: str, *, authority: dict[str, Any], actor_id: str,
    ) -> dict[str, Any]:
        current = self.status(workspace_id, provider)
        if not current["connected"]:
            raise PermissionError("provider_connection_reconnect_required")
        if not str(authority.get("access_token") or ""):
            raise ValueError("provider_connection_access_token_required")
        ProviderAuthorityStore.save(current["workspace_id"], current["provider"], authority)
        record = {key: value for key, value in current.items() if key not in {
            "connected", "authority_present", "raw_tokens_exposed"
        }}
        record["last_refresh_at"] = _now()
        record["last_refreshed_by"] = str(actor_id or "provider-adapter")[:160]
        self._write(current["workspace_id"], current["provider"], record)
        self._receipt(
            current["workspace_id"], current["provider"], "refreshed", actor_id,
            int(current["generation"]),
        )
        return self.status(current["workspace_id"], current["provider"])

    def revoke(self, workspace_id: str, provider: str, *, actor_id: str) -> dict[str, Any]:
        current = self.status(workspace_id, provider)
        if current["status"] == "not_connected":
            return current
        ProviderAuthorityStore.delete(current["workspace_id"], current["provider"])
        record = {key: value for key, value in current.items() if key not in {
            "connected", "authority_present", "raw_tokens_exposed"
        }}
        record.update({
            "status": "revoked", "revoked_at": _now(),
            "revoked_by": str(actor_id or "provider-adapter")[:160],
            "secret_storage": None,
        })
        self._write(current["workspace_id"], current["provider"], record)
        self._receipt(
            current["workspace_id"], current["provider"], "revoked", actor_id,
            int(current.get("generation") or 0),
        )
        return self.status(current["workspace_id"], current["provider"])

    def _write(self, workspace_id: str, provider: str, record: dict[str, Any]) -> None:
        self.integrations.write_json(
            self.integrations.root(workspace_id, provider) / "connection_lifecycle.json", record
        )
        if self.domain_store is not None:
            entity_id = f"provider_connections/{provider}/current"
            current = self.domain_store.get_optional(
                "departments.operational_records", workspace_id=workspace_id, entity_id=entity_id
            )
            self.domain_store.put(
                "departments.operational_records", workspace_id=workspace_id,
                entity_id=entity_id, payload=record,
                expected_version=int(current["version"]) if current else None,
                actor_id="provider-connection-runtime",
            )

    def _receipt(
        self, workspace_id: str, provider: str, event_type: str,
        actor_id: str, generation: int,
    ) -> None:
        if self.domain_store is None:
            return
        occurred_at = _now()
        receipt_id = "provider-connection-" + secrets.token_hex(12)
        receipt = {
            "schema_version": "tessaris.provider-connection-receipt.v1",
            "receipt_id": receipt_id,
            "provider": provider,
            "event_type": event_type,
            "generation": generation,
            "occurred_at": occurred_at,
            "actor_id": str(actor_id or "provider-adapter")[:160],
            "contains_credentials": False,
        }
        self.domain_store.put(
            "security.audit", workspace_id=workspace_id,
            entity_id=f"provider_connections/receipts/{receipt_id}", payload=receipt,
            expected_version=None, actor_id="provider-connection-runtime",
        )
