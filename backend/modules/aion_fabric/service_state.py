from __future__ import annotations

import json
import os
import secrets
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict

from backend.modules.aion_business.runtime.business_vault_runtime import (
    configured_business_vault_runtime,
    guardian_mode_requested,
)
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore

from .canonical import utc_now_iso


class PrivateServiceState:
    """Private, process-independent credentials for household-facing surfaces."""

    KEYRING_SERVICE = "com.tessaris.aion-fabric.private-service-state.v1"
    _DEFAULTS: Dict[str, Callable[[], str]] = {
        "companion_token": lambda: secrets.token_urlsafe(24),
        "companion_csrf": lambda: secrets.token_urlsafe(24),
        "companion_pair_code": lambda: f"{secrets.randbelow(1_000_000):06d}",
        "canvas_token": lambda: secrets.token_urlsafe(24),
        "education_token": lambda: secrets.token_urlsafe(24),
    }

    def __init__(self, base_dir: str | Path) -> None:
        self.path = Path(base_dir) / "private_service_state.json"

    def _file_state(self) -> Dict[str, str]:
        state: Dict[str, str] = {}
        if self.path.exists():
            try:
                value = json.loads(self.path.read_text(encoding="utf-8"))
                if isinstance(value, dict):
                    state = {str(key): str(item) for key, item in value.items() if isinstance(item, str)}
            except (OSError, ValueError, json.JSONDecodeError):
                state = {}
        return {key: state[key] for key in self._DEFAULTS if state.get(key)}

    def _with_defaults(self, state: Dict[str, str]) -> tuple[Dict[str, str], bool]:
        changed = False
        for key, factory in self._DEFAULTS.items():
            if not state.get(key):
                state[key] = factory()
                changed = True
        return state, changed

    @staticmethod
    def _production_custody_required() -> bool:
        mode = str(os.environ.get("TESSARIS_RUNTIME_MODE") or "development").lower()
        return guardian_mode_requested() or mode in {"production", "prod"}

    def _record_migration(self, workspace_id: str) -> None:
        if not self.path.exists() or not guardian_mode_requested():
            return
        from hashlib import sha256

        source_hash = sha256(self.path.read_bytes()).hexdigest()
        domains = VaultDomainStore(
            configured_business_vault_runtime().guardian,
            actor_id="aion-fabric-private-service-state",
        )
        entity_id = f"aion_fabric.private_service_state_migration.{source_hash}"
        if domains.get_optional("security.audit", workspace_id=workspace_id, entity_id=entity_id):
            return
        domains.put(
            "security.audit",
            workspace_id=workspace_id,
            entity_id=entity_id,
            payload={
                "schema_version": "aion.private-service-state-migration.v1",
                "source_sha256": source_hash,
                "source_retained": True,
                "copied_to_os_credential_store": True,
                "raw_secret_copied_to_guardian": False,
                "completed_at": utc_now_iso(),
            },
        )

    def _load_keyring(self) -> Dict[str, str]:
        workspace_id = str(os.environ.get("TESSARIS_BUSINESS_STABLE_ID") or "").strip()
        if not workspace_id:
            raise RuntimeError("aion_fabric_private_service_workspace_required")
        try:
            import keyring
        except Exception as exc:
            raise RuntimeError("aion_fabric_os_credential_store_unavailable") from exc
        try:
            raw = keyring.get_password(self.KEYRING_SERVICE, workspace_id)
            parsed = json.loads(raw) if raw else {}
            state = {
                key: str(parsed[key]) for key in self._DEFAULTS
                if isinstance(parsed, dict) and isinstance(parsed.get(key), str) and parsed.get(key)
            }
            legacy = self._file_state()
            if not state and legacy:
                state = legacy
            state, changed = self._with_defaults(state)
            if changed or not raw:
                encoded = json.dumps(state, sort_keys=True, separators=(",", ":"))
                keyring.set_password(self.KEYRING_SERVICE, workspace_id, encoded)
                if keyring.get_password(self.KEYRING_SERVICE, workspace_id) != encoded:
                    raise RuntimeError("aion_fabric_os_credential_store_verification_failed")
            if legacy:
                self._record_migration(workspace_id)
            return state
        except RuntimeError:
            raise
        except Exception as exc:
            raise RuntimeError("aion_fabric_os_credential_store_unavailable") from exc

    def load(self) -> Dict[str, str]:
        if self._production_custody_required():
            return self._load_keyring()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        state, changed = self._with_defaults(self._file_state())
        if changed or not self.path.exists():
            temporary = self.path.with_suffix(".tmp")
            temporary.write_text(json.dumps(state, sort_keys=True), encoding="utf-8")
            os.chmod(temporary, 0o600)
            temporary.replace(self.path)
        else:
            os.chmod(self.path, 0o600)
        return state


class ConnectionHealthMonitor:
    """Small local watchdog that recovers changing TV addresses without taking over playback."""

    def __init__(
        self,
        check: Callable[[], Dict[str, Any]],
        *,
        interval_seconds: float = 12.0,
    ) -> None:
        self.check = check
        self.interval_seconds = max(2.0, interval_seconds)
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._wake = threading.Event()
        self._thread: threading.Thread | None = None
        self._state: Dict[str, Any] = {
            "status": "starting",
            "message": "Checking the television connection…",
            "last_checked_at": None,
            "last_connected_at": None,
            "host": None,
            "consecutive_failures": 0,
        }

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="pilot-connection-health", daemon=True)
        self._thread.start()

    def retry_now(self) -> Dict[str, Any]:
        # A button press should provide a fresh result immediately.  Waking the
        # background loop alone made the dashboard appear unresponsive for up
        # to one polling interval.
        self._refresh_once()
        self._wake.set()
        return self.snapshot()

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._state)

    def _run(self) -> None:
        while not self._stop.is_set():
            self._refresh_once()
            self._wake.wait(self.interval_seconds)
            self._wake.clear()

    def _refresh_once(self) -> None:
        try:
            result = dict(self.check())
            connected = bool(result.get("connected"))
            with self._lock:
                failures = 0 if connected else int(self._state.get("consecutive_failures", 0)) + 1
                self._state.update(
                    {
                        "status": "connected" if connected else "recovering",
                        "message": (
                            "TV connected and ready."
                            if connected
                            else "Pilot is looking for the TV. Keep it on and on the same Wi-Fi."
                        ),
                        "host": result.get("host"),
                        "last_checked_at": time.time(),
                        "last_connected_at": time.time() if connected else self._state.get("last_connected_at"),
                        "consecutive_failures": failures,
                        "detail": str(result.get("detail") or ""),
                    }
                )
        except Exception as exc:
            with self._lock:
                self._state.update(
                    {
                        "status": "recovering",
                        "message": "Pilot is reconnecting to the TV automatically.",
                        "last_checked_at": time.time(),
                        "consecutive_failures": int(self._state.get("consecutive_failures", 0)) + 1,
                        "detail": f"{type(exc).__name__}: {exc}"[:240],
                    }
                )

    def stop(self) -> None:
        self._stop.set()
        self._wake.set()
        if self._thread:
            self._thread.join(timeout=3)
