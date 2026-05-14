from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from backend.modules.local_node.contracts_local_node import utc_now_iso


DEFAULT_GMAIL_CONNECTOR_CONFIG: Dict[str, Any] = {
    "connector_id": "connector.gmail.default",
    "provider": "gmail",
    "account_id": "default",
    "display_name": "Default Gmail account",
    "auth_status": "not_connected",
    "connector_health": "not_connected",
    "polling_enabled": False,
    "search_scope": "inbox",
    "unread_only": True,
    "labels": [],
    "folders": ["INBOX"],
    "last_poll_at": None,
    "last_poll_status": "never_polled",
    "last_error": None,
    "dry_run_only": True,
    "external_writes_enabled": False,
    "created_at": None,
    "updated_at": None,
}


class ConnectorRegistryStore:
    def __init__(self, base_dir: str) -> None:
        self.base_path = Path(base_dir) / "connectors"
        self.gmail_path = self.base_path / "gmail.default.json"
        self.base_path.mkdir(parents=True, exist_ok=True)

        if not self.gmail_path.exists():
            now = utc_now_iso()
            payload = {
                **DEFAULT_GMAIL_CONNECTOR_CONFIG,
                "created_at": now,
                "updated_at": now,
            }
            self.gmail_path.write_text(
                json.dumps(payload, indent=2, ensure_ascii=False, default=str),
                encoding="utf-8",
            )


    def _read_json(self, path: Path, default: Any = None) -> Any:
        try:
            if not path.exists():
                return default
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return default

    def _write_json(self, path: Path, payload: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )

    def get_gmail_config(self) -> Dict[str, Any]:
        try:
            data = json.loads(self.gmail_path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return {
                    **DEFAULT_GMAIL_CONNECTOR_CONFIG,
                    **data,
                }
        except Exception:
            pass

        now = utc_now_iso()
        return {
            **DEFAULT_GMAIL_CONNECTOR_CONFIG,
            "created_at": now,
            "updated_at": now,
        }

    def save_gmail_config(self, updates: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        current = self.get_gmail_config()
        now = utc_now_iso()
        next_payload = {
            **current,
            **(updates or {}),
            "updated_at": now,
        }

        if not next_payload.get("created_at"):
            next_payload["created_at"] = now

        self.gmail_path.write_text(
            json.dumps(next_payload, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
        return next_payload


    def gmail_token_path(self) -> Path:
        return self.base_path / "gmail.default.tokens.json"

    def get_hubspot_config(self) -> Dict[str, Any]:
        now = utc_now_iso()
        item = self._read_json(
            self.base_path / "hubspot.default.json",
            default={},
        )

        if not item:
            item = {
                "connector_id": "connector.hubspot.default",
                "provider": "hubspot",
                "account_id": "default",
                "display_name": "Default HubSpot account",
                "auth_status": "not_connected",
                "connector_health": "not_connected",
                "scopes": [],
                "portal_id": None,
                "portal_name": None,
                "token_reference": None,
                "last_check_at": None,
                "last_error": None,
                "dry_run_only": True,
                "external_writes_enabled": False,
                "created_at": now,
                "updated_at": now,
            }
            self.save_hubspot_config(item)

        return item

    def save_hubspot_config(self, item: Dict[str, Any]) -> Dict[str, Any]:
        now = utc_now_iso()
        current = self.get_hubspot_config() if not item.get("created_at") else {}
        payload = {
            **current,
            **item,
            "connector_id": item.get("connector_id") or "connector.hubspot.default",
            "provider": "hubspot",
            "updated_at": now,
        }

        if not payload.get("created_at"):
            payload["created_at"] = now

        self._write_json(self.base_path / "hubspot.default.json", payload)
        return payload

    def save_hubspot_token_payload(self, token_payload: Dict[str, Any]) -> Dict[str, Any]:
        token_ref = self.base_path / "hubspot.default.tokens.json"
        self._write_json(token_ref, token_payload)

        item = self.get_hubspot_config()
        item.update(
            {
                "auth_status": "connected",
                "connector_health": "available",
                "token_reference": str(token_ref),
                "token_stored_at": utc_now_iso(),
                "last_error": None,
            }
        )

        return self.save_hubspot_config(item)

    def read_hubspot_token_payload(self) -> Dict[str, Any]:
        item = self.get_hubspot_config()
        token_ref = item.get("token_reference") or str(self.base_path / "hubspot.default.tokens.json")
        return self._read_json(Path(token_ref), default={})

    def disconnect_hubspot(self) -> Dict[str, Any]:
        item = self.get_hubspot_config()
        item.update(
            {
                "auth_status": "not_connected",
                "connector_health": "not_connected",
                "last_error": "HubSpot disconnected locally",
                "external_writes_enabled": False,
                "dry_run_only": True,
            }
        )
        return self.save_hubspot_config(item)

    def save_gmail_token_payload(self, token_payload: Dict[str, Any]) -> Dict[str, Any]:
        now = utc_now_iso()
        safe_payload = {
            **(token_payload or {}),
            "stored_at": now,
            "provider": "gmail",
            "account_id": "default",
        }

        token_path = self.gmail_token_path()
        token_path.write_text(
            json.dumps(safe_payload, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )

        try:
            token_path.chmod(0o600)
        except Exception:
            pass

        return {
            "token_reference": str(token_path),
            "stored_at": now,
        }

    def has_gmail_token_reference(self) -> bool:
        return self.gmail_token_path().exists()

    def load_gmail_token_payload(self) -> Dict[str, Any]:
        token_path = self.gmail_token_path()
        if not token_path.exists():
            return {}

        try:
            data = json.loads(token_path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}


    def gmail_health(self) -> Dict[str, Any]:
        config = self.get_gmail_config()
        auth_status = str(config.get("auth_status") or "not_connected")
        polling_enabled = config.get("polling_enabled") is True

        if auth_status == "connected":
            connector_health = "available" if polling_enabled else "connected_polling_disabled"
        else:
            connector_health = "not_connected"

        return {
            "ok": True,
            "connector_id": config.get("connector_id"),
            "provider": "gmail",
            "account_id": config.get("account_id") or "default",
            "auth_status": auth_status,
            "connector_health": connector_health,
            "polling_enabled": polling_enabled,
            "search_scope": config.get("search_scope") or "inbox",
            "unread_only": config.get("unread_only") is not False,
            "labels": config.get("labels") or [],
            "folders": config.get("folders") or ["INBOX"],
            "last_poll_at": config.get("last_poll_at"),
            "last_poll_status": config.get("last_poll_status"),
            "last_error": config.get("last_error"),
            "dry_run_only": config.get("dry_run_only") is not False,
            "external_writes_enabled": config.get("external_writes_enabled") is True,
            "at": utc_now_iso(),
        }
