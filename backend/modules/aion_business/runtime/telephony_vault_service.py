"""Safe, workspace-scoped setup and verification for the sales phone stack."""

from __future__ import annotations

import base64
from datetime import datetime, timezone
import json
import re
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from backend.modules.aion_business.runtime.canonical_business_identity import canonical_business_id
from backend.modules.aion_business.runtime.paths import AIONBusinessPaths
from backend.modules.aion_business.runtime.telephony_credentials import (
    get_retell_api_key,
    retell_api_key_present,
    set_retell_api_key,
)
from backend.modules.aion_business.runtime.twilio_credentials import (
    get_twilio_account_sid,
    get_twilio_api_secret,
    get_twilio_api_username,
    get_twilio_carrier_number,
    get_twilio_credential_readiness,
    get_twilio_trunk,
    set_twilio_credentials,
)


TWILIO_ACCOUNT_RE = re.compile(r"^AC[a-fA-F0-9]{32}$")
TWILIO_KEY_RE = re.compile(r"^SK[a-fA-F0-9]{32}$")
E164_RE = re.compile(r"^\+[1-9][0-9]{7,14}$")


class TelephonyVaultService:
    """Connect both provider accounts while keeping every secret in Keychain."""

    def _workspace(self, workspace_id: str) -> str:
        return canonical_business_id(workspace_id)

    def _status_path(self, workspace_id: str) -> Path:
        directory = AIONBusinessPaths.business_container_dir(self._workspace(workspace_id)) / "integrations"
        directory.mkdir(parents=True, exist_ok=True)
        return directory / "sales_telephony.json"

    def _metadata(self, workspace_id: str) -> dict[str, Any]:
        path = self._status_path(workspace_id)
        if not path.exists():
            return {}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _write_metadata(self, workspace_id: str, data: dict[str, Any]) -> None:
        path = self._status_path(workspace_id)
        safe = {
            key: value
            for key, value in data.items()
            if key not in {"api_key", "api_key_secret", "sip_password", "auth_token"}
        }
        path.write_text(json.dumps(safe, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        try:
            path.chmod(0o600)
        except OSError:
            pass

    @staticmethod
    def _json_request(url: str, authorization: str) -> Any:
        request = Request(url, headers={"Accept": "application/json", "Authorization": authorization})
        try:
            with urlopen(request, timeout=12) as response:
                return json.loads(response.read().decode("utf-8") or "{}")
        except HTTPError as exc:
            if exc.code in {401, 403}:
                raise PermissionError("provider_rejected_credentials") from exc
            raise RuntimeError(f"provider_check_failed_{exc.code}") from exc
        except (URLError, TimeoutError) as exc:
            raise RuntimeError("provider_unreachable") from exc

    def validate_twilio(self, account_sid: str, api_key_sid: str, api_key_secret: str) -> dict[str, Any]:
        if not TWILIO_ACCOUNT_RE.fullmatch(account_sid):
            raise ValueError("invalid_twilio_account_sid")
        if not TWILIO_KEY_RE.fullmatch(api_key_sid):
            raise ValueError("invalid_twilio_api_key_sid")
        if len(api_key_secret) < 12:
            raise ValueError("invalid_twilio_api_key_secret")
        token = base64.b64encode(f"{api_key_sid}:{api_key_secret}".encode("utf-8")).decode("ascii")
        record = self._json_request(
            f"https://api.twilio.com/2010-04-01/Accounts/{quote(account_sid)}.json",
            f"Basic {token}",
        )
        return {"account_status": str(record.get("status") or "active")}

    def validate_retell(self, api_key: str) -> dict[str, Any]:
        if len(api_key) < 20:
            raise ValueError("invalid_retell_api_key")
        authorization = f"Bearer {api_key}"
        agents = self._json_request(
            "https://api.retellai.com/list-agents?" + urlencode({"limit": 100, "is_latest": "true"}),
            authorization,
        )
        numbers = self._json_request(
            "https://api.retellai.com/v2/list-phone-numbers?" + urlencode({"limit": 1000}),
            authorization,
        )
        agent_rows = agents if isinstance(agents, list) else agents.get("agents", [])
        number_rows = numbers if isinstance(numbers, list) else numbers.get("phone_numbers", [])
        safe_numbers = []
        for row in number_rows if isinstance(number_rows, list) else []:
            if isinstance(row, dict):
                value = str(row.get("phone_number") or row.get("number") or "").strip()
                if value:
                    safe_numbers.append(value)
        return {"agent_count": len(agent_rows or []), "phone_numbers": safe_numbers}

    def save_twilio(self, workspace_id: str, values: dict[str, str]) -> dict[str, Any]:
        workspace = self._workspace(workspace_id)
        normalized = {key: str(value or "").strip() for key, value in values.items()}
        phone_number = normalized.get("from_number", "")
        if not E164_RE.fullmatch(phone_number):
            raise ValueError("phone_number_must_use_e164_format")
        termination_uri = normalized.get("termination_uri", "").removeprefix("sip:")
        if not termination_uri or " " in termination_uri or ".pstn.twilio.com" not in termination_uri.lower():
            raise ValueError("valid_twilio_termination_uri_required")
        if not normalized.get("sip_username") or not normalized.get("sip_password"):
            raise ValueError("sip_credentials_required")
        verified = self.validate_twilio(
            normalized.get("account_sid", ""),
            normalized.get("api_key_sid", ""),
            normalized.get("api_key_secret", ""),
        )
        normalized["termination_uri"] = termination_uri
        normalized["carrier_number"] = phone_number
        normalized["caller_id"] = phone_number
        set_twilio_credentials(workspace, normalized)
        metadata = self._metadata(workspace)
        metadata["twilio"] = {
            "validated": True,
            "validated_at": datetime.now(timezone.utc).isoformat(),
            "phone_number": phone_number,
            "termination_uri": termination_uri,
            "account_status": verified.get("account_status", "active"),
        }
        self._write_metadata(workspace, metadata)
        return self.status(workspace)

    def save_retell(self, workspace_id: str, api_key: str) -> dict[str, Any]:
        workspace = self._workspace(workspace_id)
        api_key = str(api_key or "").strip()
        verified = self.validate_retell(api_key)
        set_retell_api_key(workspace, api_key)
        metadata = self._metadata(workspace)
        metadata["retell"] = {
            "validated": True,
            "validated_at": datetime.now(timezone.utc).isoformat(),
            "agent_count": verified["agent_count"],
            "phone_numbers": verified["phone_numbers"],
        }
        self._write_metadata(workspace, metadata)
        return self.status(workspace)

    def refresh(self, workspace_id: str) -> dict[str, Any]:
        workspace = self._workspace(workspace_id)
        metadata = self._metadata(workspace)
        readiness = get_twilio_credential_readiness(workspace)
        if readiness.get("credential_ready"):
            verified = self.validate_twilio(
                get_twilio_account_sid(workspace),
                get_twilio_api_username(workspace),
                get_twilio_api_secret(workspace),
            )
            twilio = dict(metadata.get("twilio") or {})
            trunk = get_twilio_trunk(workspace)
            twilio.update({
                "validated": True,
                "validated_at": datetime.now(timezone.utc).isoformat(),
                "phone_number": get_twilio_carrier_number(workspace),
                "termination_uri": str(trunk.get("termination_uri") or ""),
                **verified,
            })
            metadata["twilio"] = twilio
        if retell_api_key_present(workspace):
            verified = self.validate_retell(get_retell_api_key(workspace))
            metadata["retell"] = {
                "validated": True,
                "validated_at": datetime.now(timezone.utc).isoformat(),
                **verified,
            }
        self._write_metadata(workspace, metadata)
        return self.status(workspace)

    def status(self, workspace_id: str) -> dict[str, Any]:
        workspace = self._workspace(workspace_id)
        metadata = self._metadata(workspace)
        readiness = get_twilio_credential_readiness(workspace)
        twilio_meta = dict(metadata.get("twilio") or {})
        retell_meta = dict(metadata.get("retell") or {})
        phone_number = str(twilio_meta.get("phone_number") or "")
        retell_numbers = [str(value) for value in retell_meta.get("phone_numbers", [])]
        twilio_ready = bool(readiness.get("credential_ready") and readiness.get("phone_number_configured") and readiness.get("sip_trunk_configured") and twilio_meta.get("validated"))
        retell_ready = bool(retell_api_key_present(workspace) and retell_meta.get("validated"))
        number_imported = bool(phone_number and phone_number in retell_numbers)
        return {
            "ok": True,
            "workspace_id": workspace,
            "twilio": {
                "connected": twilio_ready,
                "credential_present": bool(readiness.get("credential_ready")),
                "number_configured": bool(readiness.get("phone_number_configured")),
                "trunk_configured": bool(readiness.get("sip_trunk_configured")),
                "phone_number": phone_number,
                "termination_uri": str(twilio_meta.get("termination_uri") or ""),
                "validated_at": twilio_meta.get("validated_at"),
            },
            "retell": {
                "connected": retell_ready,
                "credential_present": retell_api_key_present(workspace),
                "agent_count": int(retell_meta.get("agent_count") or 0),
                "phone_number_count": len(retell_numbers),
                "validated_at": retell_meta.get("validated_at"),
            },
            "routing": {
                "number_imported_to_retell": number_imported,
                "ready_to_build_callers": bool(twilio_ready and retell_ready and number_imported),
            },
            "completed_steps": int(twilio_ready) + int(retell_ready),
            "total_steps": 2,
        }
