"""Independent monotonic registry for public application-account descriptors.

The registry stores no recovery secret.  It accepts only root-signed public
descriptors, preserves every accepted version and advances one epoch at a time
through an exact previous-descriptor digest.  It is designed to run outside the
desktop's local recovery state so an old recovery kit cannot appoint its own
latest descriptor.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hmac
import json
import os
from pathlib import Path
import re
import sqlite3
import threading
from typing import Any, Callable, Mapping
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from backend.modules.aion_business.runtime.application_account_recovery import (
    ApplicationAccountRecoveryStore,
    _canonical,
    _component,
    _digest,
)


class ApplicationAccountDescriptorRegistryError(ValueError):
    pass


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class ApplicationAccountDescriptorRegistry:
    """Append-only current-account-descriptor registry backed by SQLite."""

    SCHEMA = "tessaris.application-account-descriptor-registry.v1"
    MAX_DESCRIPTOR_BYTES = 256 * 1024
    DEFAULT_MAX_ACCOUNTS = 100_000
    DEFAULT_MAX_HISTORY_PER_ACCOUNT = 1_024

    def __init__(
        self,
        path: str | Path,
        *,
        max_accounts: int = DEFAULT_MAX_ACCOUNTS,
        max_history_per_account: int = DEFAULT_MAX_HISTORY_PER_ACCOUNT,
    ) -> None:
        requested_path = Path(path).expanduser()
        if requested_path.is_symlink():
            raise ApplicationAccountDescriptorRegistryError("account_registry_path_unsafe")
        self.path = requested_path.resolve()
        self.max_accounts = max(1, min(int(max_accounts), 1_000_000))
        self.max_history_per_account = max(2, min(int(max_history_per_account), 100_000))
        self._lock = threading.RLock()
        self._prepare_path()
        self._initialize()

    def publish(self, value: Mapping[str, Any]) -> dict[str, Any]:
        descriptor = ApplicationAccountRecoveryStore.verify_descriptor(value)
        encoded = _canonical(descriptor)
        if len(encoded) > self.MAX_DESCRIPTOR_BYTES:
            raise ApplicationAccountDescriptorRegistryError("account_descriptor_too_large")
        account_id = str(descriptor["account_id"])
        workspace_id = str(descriptor["workspace_id"])
        epoch = int(descriptor["recovery_epoch"])
        digest = _digest(descriptor)
        previous_digest = descriptor.get("previous_descriptor_sha256")

        with self._lock, self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            current = connection.execute(
                "SELECT recovery_epoch, descriptor_sha256, workspace_id "
                "FROM current_descriptors WHERE account_id = ?",
                (account_id,),
            ).fetchone()
            if current is None:
                count = int(connection.execute("SELECT COUNT(*) FROM current_descriptors").fetchone()[0])
                if count >= self.max_accounts:
                    connection.execute("ROLLBACK")
                    raise ApplicationAccountDescriptorRegistryError("account_registry_capacity_exceeded")
                if epoch != 1 or previous_digest is not None:
                    connection.execute("ROLLBACK")
                    raise PermissionError("account_registry_initial_descriptor_required")
            else:
                current_epoch, current_digest, current_workspace = int(current[0]), str(current[1]), str(current[2])
                if epoch == current_epoch and hmac.compare_digest(digest, current_digest):
                    connection.execute("ROLLBACK")
                    return self._publication_result(
                        descriptor, digest=digest, accepted=False, idempotent=True,
                    )
                if epoch <= current_epoch:
                    connection.execute("ROLLBACK")
                    raise PermissionError("account_registry_epoch_rollback_or_equivocation")
                if epoch != current_epoch + 1:
                    connection.execute("ROLLBACK")
                    raise PermissionError("account_registry_epoch_gap")
                if not hmac.compare_digest(workspace_id, current_workspace):
                    connection.execute("ROLLBACK")
                    raise PermissionError("account_registry_workspace_changed")
                if not hmac.compare_digest(str(previous_digest or ""), current_digest):
                    connection.execute("ROLLBACK")
                    raise PermissionError("account_registry_descriptor_continuity_invalid")
                history_count = int(connection.execute(
                    "SELECT COUNT(*) FROM descriptor_history WHERE account_id = ?",
                    (account_id,),
                ).fetchone()[0])
                if history_count >= self.max_history_per_account:
                    connection.execute("ROLLBACK")
                    raise ApplicationAccountDescriptorRegistryError(
                        "account_registry_history_capacity_exceeded"
                    )

            received_at = _utc_now()
            try:
                connection.execute(
                    "INSERT INTO descriptor_history("
                    "account_id, recovery_epoch, descriptor_sha256, previous_descriptor_sha256, "
                    "workspace_id, descriptor_json, received_at) VALUES(?,?,?,?,?,?,?)",
                    (
                        account_id,
                        epoch,
                        digest,
                        previous_digest,
                        workspace_id,
                        encoded.decode("utf-8"),
                        received_at,
                    ),
                )
                connection.execute(
                    "INSERT INTO current_descriptors("
                    "account_id, recovery_epoch, descriptor_sha256, workspace_id, descriptor_json, updated_at"
                    ") VALUES(?,?,?,?,?,?) "
                    "ON CONFLICT(account_id) DO UPDATE SET "
                    "recovery_epoch=excluded.recovery_epoch, "
                    "descriptor_sha256=excluded.descriptor_sha256, "
                    "workspace_id=excluded.workspace_id, "
                    "descriptor_json=excluded.descriptor_json, updated_at=excluded.updated_at",
                    (account_id, epoch, digest, workspace_id, encoded.decode("utf-8"), received_at),
                )
                connection.execute("COMMIT")
            except Exception:
                connection.execute("ROLLBACK")
                raise
        return self._publication_result(descriptor, digest=digest, accepted=True, idempotent=False)

    def current(self, account_id: str) -> dict[str, Any]:
        account = self._account_id(account_id)
        with self._connect() as connection:
            row = connection.execute(
                "SELECT descriptor_json FROM current_descriptors WHERE account_id = ?",
                (account,),
            ).fetchone()
        if row is None:
            raise KeyError("account_descriptor_not_found")
        descriptor = ApplicationAccountRecoveryStore.verify_descriptor(
            json.loads(str(row[0])), expected_account_id=account,
        )
        return descriptor

    def authorize_device(
        self,
        *,
        account_id: str,
        device_id: str,
        recovery_epoch: int,
        workspace_id: str | None = None,
    ) -> dict[str, Any]:
        descriptor = self.current(account_id)
        device = _component(device_id, "device_id")
        if int(recovery_epoch) != int(descriptor["recovery_epoch"]):
            raise PermissionError("application_account_session_epoch_revoked")
        if device not in descriptor["active_devices"]:
            raise PermissionError("application_account_device_revoked")
        if workspace_id is not None and not hmac.compare_digest(
            str(descriptor["workspace_id"]), str(workspace_id),
        ):
            raise PermissionError("application_account_workspace_mismatch")
        return {
            "authorized": True,
            "account_id": descriptor["account_id"],
            "workspace_id": descriptor["workspace_id"],
            "recovery_epoch": descriptor["recovery_epoch"],
            "device_id": device,
            "descriptor_sha256": _digest(descriptor),
            "authority_source": self.SCHEMA,
        }

    def history(self, account_id: str) -> list[dict[str, Any]]:
        account = self._account_id(account_id)
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT recovery_epoch, descriptor_sha256, previous_descriptor_sha256, "
                "workspace_id, received_at FROM descriptor_history "
                "WHERE account_id = ? ORDER BY recovery_epoch ASC",
                (account,),
            ).fetchall()
        return [
            {
                "account_id": account,
                "recovery_epoch": int(row[0]),
                "descriptor_sha256": str(row[1]),
                "previous_descriptor_sha256": row[2],
                "workspace_id": str(row[3]),
                "received_at": str(row[4]),
            }
            for row in rows
        ]

    def status(self) -> dict[str, Any]:
        with self._connect() as connection:
            account_count = int(connection.execute("SELECT COUNT(*) FROM current_descriptors").fetchone()[0])
            descriptor_count = int(connection.execute("SELECT COUNT(*) FROM descriptor_history").fetchone()[0])
            integrity = str(connection.execute("PRAGMA integrity_check").fetchone()[0])
        return {
            "schema_version": self.SCHEMA,
            "account_count": account_count,
            "descriptor_count": descriptor_count,
            "sqlite_integrity": integrity,
            "stores_recovery_secrets": False,
            "independent_deployment_required": True,
        }

    def _initialize(self) -> None:
        with self._lock, self._connect() as connection:
            connection.executescript(
                """
                PRAGMA trusted_schema=OFF;
                PRAGMA journal_mode=WAL;
                PRAGMA synchronous=FULL;
                CREATE TABLE IF NOT EXISTS descriptor_history (
                    account_id TEXT NOT NULL,
                    recovery_epoch INTEGER NOT NULL CHECK(recovery_epoch >= 1),
                    descriptor_sha256 TEXT NOT NULL UNIQUE,
                    previous_descriptor_sha256 TEXT,
                    workspace_id TEXT NOT NULL,
                    descriptor_json TEXT NOT NULL,
                    received_at TEXT NOT NULL,
                    PRIMARY KEY(account_id, recovery_epoch)
                );
                CREATE TABLE IF NOT EXISTS current_descriptors (
                    account_id TEXT PRIMARY KEY,
                    recovery_epoch INTEGER NOT NULL CHECK(recovery_epoch >= 1),
                    descriptor_sha256 TEXT NOT NULL,
                    workspace_id TEXT NOT NULL,
                    descriptor_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS descriptor_history_account_digest
                    ON descriptor_history(account_id, descriptor_sha256);
                """
            )
        try:
            os.chmod(self.path, 0o600)
        except OSError:
            pass

    def _prepare_path(self) -> None:
        if self.path.is_symlink():
            raise ApplicationAccountDescriptorRegistryError("account_registry_path_unsafe")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(self.path.parent, 0o700)
        except OSError:
            pass

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(str(self.path), timeout=5.0, isolation_level=None)
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=5000")
        return connection

    @staticmethod
    def _account_id(value: str) -> str:
        account = str(value or "").strip()
        if not re.fullmatch(r"account_[0-9a-f]{40}", account):
            raise ApplicationAccountDescriptorRegistryError("account_registry_account_id_invalid")
        return account

    @staticmethod
    def _publication_result(
        descriptor: Mapping[str, Any], *, digest: str, accepted: bool, idempotent: bool,
    ) -> dict[str, Any]:
        return {
            "accepted": accepted,
            "idempotent": idempotent,
            "account_id": descriptor["account_id"],
            "workspace_id": descriptor["workspace_id"],
            "recovery_epoch": descriptor["recovery_epoch"],
            "descriptor_sha256": digest,
            "stores_recovery_secrets": False,
        }


class ApplicationAccountDescriptorRegistryClient:
    """Fail-closed HTTPS reader for a separately operated registry.

    The local cache is an anti-rollback memory, not an availability fallback:
    authorization still fails if the live registry cannot be reached.
    """

    MAX_RESPONSE_BYTES = 256 * 1024

    def __init__(
        self,
        base_url: str,
        *,
        cache_root: str | Path,
        runtime_mode: str | None = None,
        timeout_seconds: float = 3.0,
        transport: Callable[[str], Mapping[str, Any]] | None = None,
    ) -> None:
        self.base_url = str(base_url or "").strip().rstrip("/")
        self.runtime_mode = str(runtime_mode or os.getenv("TESSARIS_RUNTIME_MODE") or "development").lower()
        self.timeout_seconds = max(0.25, min(float(timeout_seconds), 30.0))
        requested_cache_root = Path(cache_root).expanduser()
        if requested_cache_root.is_symlink():
            raise ApplicationAccountDescriptorRegistryError("account_registry_cache_path_unsafe")
        self.cache_root = requested_cache_root.resolve()
        self.transport = transport
        self._lock = threading.RLock()
        self._validate_url()
        self.cache_root.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(self.cache_root, 0o700)
        except OSError:
            pass

    def current(self, account_id: str) -> dict[str, Any]:
        account = ApplicationAccountDescriptorRegistry._account_id(account_id)
        url = f"{self.base_url}/v1/accounts/{account}/descriptor"
        try:
            if self.transport is not None:
                value = dict(self.transport(url))
            else:
                request = Request(url, method="GET", headers={"Accept": "application/json"})
                with urlopen(request, timeout=self.timeout_seconds) as response:  # noqa: S310 - validated URL
                    if str(response.geturl()) != url:
                        raise RuntimeError("account_registry_redirect_not_allowed")
                    content_type = str(response.headers.get("content-type") or "").split(";", 1)[0].lower()
                    if content_type != "application/json":
                        raise RuntimeError("account_registry_response_media_type_invalid")
                    payload = response.read(self.MAX_RESPONSE_BYTES + 1)
                if len(payload) > self.MAX_RESPONSE_BYTES:
                    raise RuntimeError("account_registry_response_too_large")
                value = json.loads(payload.decode("utf-8"))
        except (ApplicationAccountDescriptorRegistryError, PermissionError):
            raise
        except Exception as exc:
            raise RuntimeError("application_account_registry_unavailable") from exc
        if not isinstance(value, dict):
            raise RuntimeError("application_account_registry_response_invalid")
        descriptor = ApplicationAccountRecoveryStore.verify_descriptor(
            value, expected_account_id=account,
        )
        self._remember_monotonic(descriptor)
        return descriptor

    def authorize_device(
        self,
        *,
        account_id: str,
        device_id: str,
        recovery_epoch: int,
        workspace_id: str | None = None,
    ) -> dict[str, Any]:
        descriptor = self.current(account_id)
        device = _component(device_id, "device_id")
        if int(recovery_epoch) != int(descriptor["recovery_epoch"]):
            raise PermissionError("application_account_session_epoch_revoked")
        if device not in descriptor["active_devices"]:
            raise PermissionError("application_account_device_revoked")
        if workspace_id is not None and not hmac.compare_digest(
            str(descriptor["workspace_id"]), str(workspace_id),
        ):
            raise PermissionError("application_account_workspace_mismatch")
        return {
            "authorized": True,
            "account_id": descriptor["account_id"],
            "workspace_id": descriptor["workspace_id"],
            "recovery_epoch": descriptor["recovery_epoch"],
            "device_id": device,
            "descriptor_sha256": _digest(descriptor),
            "authority_source": "independent_registry_https.v1",
        }

    def _remember_monotonic(self, descriptor: Mapping[str, Any]) -> None:
        account = str(descriptor["account_id"])
        path = self.cache_root / f"{account}.json"
        if path.is_symlink():
            raise RuntimeError("application_account_registry_cache_unsafe")
        with self._lock:
            if path.is_file():
                if path.stat().st_size > self.MAX_RESPONSE_BYTES:
                    raise RuntimeError("application_account_registry_cache_invalid")
                try:
                    previous = ApplicationAccountRecoveryStore.verify_descriptor(
                        json.loads(path.read_text(encoding="utf-8")),
                        expected_account_id=account,
                    )
                except Exception as exc:
                    raise RuntimeError("application_account_registry_cache_invalid") from exc
                old_epoch = int(previous["recovery_epoch"])
                new_epoch = int(descriptor["recovery_epoch"])
                if new_epoch < old_epoch:
                    raise PermissionError("application_account_registry_rollback_detected")
                if new_epoch == old_epoch and not hmac.compare_digest(
                    _digest(previous), _digest(descriptor),
                ):
                    raise PermissionError("application_account_registry_equivocation_detected")
                if new_epoch == old_epoch:
                    return
            temporary = path.with_suffix(".tmp")
            temporary.write_bytes(_canonical(dict(descriptor)))
            os.chmod(temporary, 0o600)
            os.replace(temporary, path)

    def _validate_url(self) -> None:
        parsed = urlparse(self.base_url)
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ApplicationAccountDescriptorRegistryError("account_registry_url_invalid")
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ApplicationAccountDescriptorRegistryError("account_registry_url_invalid")
        loopback = parsed.hostname in {"127.0.0.1", "::1", "localhost"}
        if self.runtime_mode in {"production", "prod"} and parsed.scheme != "https":
            raise ApplicationAccountDescriptorRegistryError("account_registry_https_required")
        if parsed.scheme == "http" and not loopback:
            raise ApplicationAccountDescriptorRegistryError("account_registry_https_required")
