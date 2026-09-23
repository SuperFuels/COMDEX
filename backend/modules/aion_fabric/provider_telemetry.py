from __future__ import annotations

import base64
import json
import os
import re
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict

from .canonical import canonical_bytes, canonical_hash, utc_now_iso
from .identity import DeviceIdentity


class TrustedProviderTelemetry:
    """Accept signed, persona-bound playback facts from explicitly trusted adapters."""

    _lock = threading.RLock()
    _SCOPES = {"metadata.read", "playback.read", "entitlement.read"}
    _PLAYBACK_STATES = {"unknown", "idle", "buffering", "paused", "playing", "ended"}
    _ENTITLEMENTS = {"unknown", "included", "rental", "purchase", "unavailable"}

    def __init__(self, runtime_dir: str | Path) -> None:
        self.root = Path(runtime_dir) / "provider_telemetry"
        self.sources_path = self.root / "trusted_sources.json"
        self.state_path = self.root / "state.json"
        self.root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _read(path: Path, fallback: Dict[str, Any]) -> Dict[str, Any]:
        if not path.exists():
            return fallback
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else fallback
        except (OSError, json.JSONDecodeError):
            return fallback

    @staticmethod
    def _write(path: Path, value: Dict[str, Any]) -> None:
        temporary = path.with_suffix(".tmp")
        temporary.write_bytes(canonical_bytes(value))
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)

    @staticmethod
    def _clean(value: Any, limit: int) -> str:
        return " ".join(str(value or "").split()).strip()[:limit]

    def register_source(
        self,
        *,
        source_id: str,
        provider: str,
        public_key: str,
        persona_id: str,
        scopes: list[str],
        approved_by: str,
    ) -> Dict[str, Any]:
        if not re.fullmatch(r"source_[A-Za-z0-9_-]{8,100}", source_id):
            raise ValueError("Invalid provider telemetry source identity")
        provider = self._clean(provider, 80).lower()
        if not re.fullmatch(r"[a-z0-9][a-z0-9 ._+-]{1,79}", provider):
            raise ValueError("Invalid provider name")
        if not re.fullmatch(r"persona_[A-Za-z0-9]+", persona_id):
            raise ValueError("Invalid private persona binding")
        normalized_scopes = sorted(set(str(value) for value in scopes))
        if not normalized_scopes or any(value not in self._SCOPES for value in normalized_scopes):
            raise ValueError("Invalid provider telemetry scope")
        try:
            if len(base64.b64decode(public_key, validate=True)) != 32:
                raise ValueError
        except (ValueError, TypeError):
            raise ValueError("Provider telemetry requires an Ed25519 public key") from None
        if not self._clean(approved_by, 100):
            raise ValueError("Local approval evidence is required")
        record = {
            "source_id": source_id,
            "provider": provider,
            "public_key": public_key,
            "persona_id": persona_id,
            "scopes": normalized_scopes,
            "status": "trusted",
            "approved_by": self._clean(approved_by, 100),
            "registered_at": utc_now_iso(),
        }
        with self._lock:
            store = self._read(self.sources_path, {"schema_version": "pilot.provider-telemetry-sources.v1", "sources": []})
            sources = [item for item in store.get("sources") or [] if item.get("source_id") != source_id]
            store["sources"] = (sources + [record])[-64:]
            store["updated_at"] = utc_now_iso()
            self._write(self.sources_path, store)
        return {key: value for key, value in record.items() if key != "public_key"}

    @staticmethod
    def _timestamp(value: str) -> datetime:
        try:
            result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (AttributeError, ValueError) as exc:
            raise ValueError("Provider telemetry timestamp must be ISO-8601") from exc
        if result.tzinfo is None:
            raise ValueError("Provider telemetry timestamp must include a timezone")
        return result.astimezone(timezone.utc)

    def accept(self, envelope: Dict[str, Any], signature: str) -> Dict[str, Any]:
        required = {"schema_version", "source_id", "provider", "persona_id", "nonce", "observed_at", "content", "playback", "entitlement"}
        if set(envelope) != required or envelope.get("schema_version") != "pilot.provider-telemetry-envelope.v1":
            raise ValueError("Invalid provider telemetry envelope")
        source_id = str(envelope.get("source_id") or "")
        with self._lock:
            sources = self._read(self.sources_path, {"sources": []})
            source = next((item for item in sources.get("sources") or [] if item.get("source_id") == source_id and item.get("status") == "trusted"), None)
            if source is None:
                raise PermissionError("Provider telemetry source is not trusted")
            if envelope.get("provider") != source.get("provider") or envelope.get("persona_id") != source.get("persona_id"):
                raise PermissionError("Provider telemetry source, provider and persona binding do not match")
            nonce = str(envelope.get("nonce") or "")
            if not re.fullmatch(r"[A-Za-z0-9_-]{16,100}", nonce):
                raise ValueError("Invalid provider telemetry nonce")
            observed_at = self._timestamp(str(envelope.get("observed_at") or ""))
            now = datetime.now(timezone.utc)
            if observed_at < now - timedelta(minutes=2) or observed_at > now + timedelta(seconds=30):
                raise PermissionError("Provider telemetry is stale or from the future")
            state = self._read(self.state_path, {"schema_version": "pilot.provider-telemetry.store.v1", "records": [], "used_nonces": []})
            if nonce in state.get("used_nonces") or []:
                raise PermissionError("Provider telemetry replay detected")
            if not DeviceIdentity.verify(str(source["public_key"]), canonical_bytes(envelope), signature):
                raise PermissionError("Provider telemetry signature is invalid")

            scopes = set(source.get("scopes") or [])
            content = dict(envelope.get("content") or {})
            playback = dict(envelope.get("playback") or {})
            entitlement = dict(envelope.get("entitlement") or {})
            state_name = str(playback.get("state") or "unknown").lower()
            if state_name not in self._PLAYBACK_STATES:
                raise ValueError("Invalid provider playback state")
            entitlement_status = str(entitlement.get("status") or "unknown").lower()
            if entitlement_status not in self._ENTITLEMENTS:
                raise ValueError("Invalid provider entitlement state")
            position = max(0, min(int(playback.get("position_seconds") or 0), 604800))
            duration = max(0, min(int(playback.get("duration_seconds") or 0), 604800))
            if duration and position > duration + 30:
                raise ValueError("Playback position exceeds duration")
            record: Dict[str, Any] = {
                "schema_version": "pilot.provider-telemetry.v1",
                "telemetry_id": f"telemetry_{canonical_hash({'source_id': source_id, 'nonce': nonce})[:32]}",
                "source_id": source_id,
                "provider": str(source["provider"]),
                "persona_id": str(source["persona_id"]),
                "observed_at": observed_at.isoformat(),
                "received_at": utc_now_iso(),
                "authenticated": True,
                "scopes": sorted(scopes),
                "content": {
                    "content_id": self._clean(content.get("content_id"), 160),
                    "title": self._clean(content.get("title"), 240),
                    "series_title": self._clean(content.get("series_title"), 240),
                    "season": self._clean(content.get("season"), 40),
                    "episode": self._clean(content.get("episode"), 80),
                } if "metadata.read" in scopes else {},
                "playback": {
                    "state": state_name,
                    "position_seconds": position,
                    "duration_seconds": duration,
                } if "playback.read" in scopes else {"state": "unknown"},
                "entitlement": {
                    "status": entitlement_status,
                    "verified": entitlement_status != "unknown",
                } if "entitlement.read" in scopes else {"status": "unknown", "verified": False},
                "raw_provider_response_retained": False,
                "provider_secret_exposed": False,
                "account_identifier_exposed": False,
            }
            record["record_hash"] = canonical_hash(record)
            state["records"] = list(state.get("records") or [])[-49:] + [record]
            state["used_nonces"] = list(state.get("used_nonces") or [])[-255:] + [nonce]
            state["updated_at"] = utc_now_iso()
            self._write(self.state_path, state)
            return dict(record)

    def latest(self, *, persona_id: str | None = None, provider: str | None = None, maximum_age_seconds: int = 180) -> Dict[str, Any] | None:
        state = self._read(self.state_path, {"records": []})
        now = datetime.now(timezone.utc)
        for record in reversed(state.get("records") or []):
            if persona_id and record.get("persona_id") != persona_id:
                continue
            if provider and str(record.get("provider") or "").lower() != provider.lower():
                continue
            try:
                observed = self._timestamp(str(record.get("observed_at") or ""))
            except ValueError:
                continue
            if 0 <= (now - observed).total_seconds() <= maximum_age_seconds:
                return dict(record)
        return None

    def snapshot(self, *, persona_id: str | None = None) -> Dict[str, Any]:
        sources = self._read(self.sources_path, {"sources": []})
        trusted = [item for item in sources.get("sources") or [] if item.get("status") == "trusted"]
        return {
            "schema_version": "pilot.provider-telemetry.snapshot.v1",
            "trusted_sources": len(trusted),
            "latest": self.latest(persona_id=persona_id),
            "public_keys_exposed": False,
            "provider_secrets_exposed": False,
            "replay_protected": True,
        }
