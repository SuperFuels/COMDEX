from __future__ import annotations

import json
import os
import re
import urllib.parse
from pathlib import Path
from typing import Any, Dict
from uuid import uuid4

from .canonical import canonical_bytes, canonical_hash, utc_now_iso


class VerifiedEntertainmentExecution:
    """Prepare persona-bound provider routes and record only observed execution facts."""

    _NETFLIX = re.compile(r"^/title/(?P<id>[0-9]{5,12})/?$")
    _YOUTUBE = re.compile(r"^[A-Za-z0-9_-]{6,20}$")
    _PRIME = re.compile(r"^/(?:detail|gp/video/detail)/(?P<id>[A-Za-z0-9_-]{5,80})(?:/.*)?$")
    _DISNEY = re.compile(r"^/(?:video|movies|series)/(?P<id>[A-Za-z0-9_-]{3,160})(?:/.*)?$")

    def __init__(self, runtime_dir: str | Path) -> None:
        self.root = Path(runtime_dir) / "entertainment_execution"
        self.path = self.root / "state.json"
        self.root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _initial() -> Dict[str, Any]:
        return {
            "schema_version": "pilot.entertainment-execution.store.v1",
            "executions": [],
            "last_verified_by_persona": {},
            "updated_at": utc_now_iso(),
        }

    def _read(self) -> Dict[str, Any]:
        if not self.path.exists():
            return self._initial()
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else self._initial()
        except (OSError, json.JSONDecodeError):
            return self._initial()

    def _write(self, state: Dict[str, Any]) -> None:
        state["updated_at"] = utc_now_iso()
        temporary = self.path.with_suffix(".tmp")
        temporary.write_bytes(canonical_bytes(state))
        os.chmod(temporary, 0o600)
        os.replace(temporary, self.path)

    @classmethod
    def classify_official_route(cls, value: str) -> Dict[str, Any]:
        """Return a strict provider route; search, catalogue, and credential URLs fail closed."""
        parsed = urllib.parse.urlparse(str(value or "").strip())
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.port not in {None, 443}
            or parsed.fragment
        ):
            raise ValueError("Entertainment execution requires a credential-free official HTTPS route")
        host = parsed.hostname.lower().removeprefix("www.")
        path = parsed.path or "/"
        provider = route_kind = provider_id = ""
        canonical_url = ""
        if host == "netflix.com":
            match = cls._NETFLIX.fullmatch(path)
            if match:
                provider, route_kind, provider_id = "Netflix", "title", match.group("id")
                canonical_url = f"https://www.netflix.com/title/{provider_id}"
        elif host in {"youtube.com", "m.youtube.com"} and path == "/watch":
            provider_id = urllib.parse.parse_qs(parsed.query).get("v", [""])[0]
            if cls._YOUTUBE.fullmatch(provider_id):
                provider, route_kind = "YouTube", "video"
                canonical_url = f"https://www.youtube.com/watch?v={provider_id}"
        elif host == "youtu.be" and cls._YOUTUBE.fullmatch(path.lstrip("/")):
            provider, route_kind, provider_id = "YouTube", "video", path.lstrip("/")
            canonical_url = f"https://www.youtube.com/watch?v={provider_id}"
        elif host in {"primevideo.com", "amazon.com"}:
            match = cls._PRIME.fullmatch(path)
            if match:
                provider, route_kind, provider_id = "Prime Video", "title", match.group("id")
                canonical_url = urllib.parse.urlunparse(("https", parsed.hostname.lower(), path, "", "", ""))
        elif host == "disneyplus.com":
            match = cls._DISNEY.fullmatch(path)
            if match:
                provider, route_kind, provider_id = "Disney+", "title", match.group("id")
                canonical_url = urllib.parse.urlunparse(("https", parsed.hostname.lower(), path, "", "", ""))
        if not canonical_url:
            raise ValueError("That result is not an exact official title or video route")
        return {
            "provider": provider,
            "route_kind": route_kind,
            "provider_content_id": provider_id,
            "canonical_url": canonical_url,
            "route_hash": canonical_hash(canonical_url),
        }

    def prepare(self, *, item: Dict[str, Any], persona_id: str) -> Dict[str, Any]:
        route = self.classify_official_route(str(item.get("url") or ""))
        title = " ".join(str(item.get("title") or "Provider title").split()).strip()[:200]
        execution: Dict[str, Any] = {
            "schema_version": "pilot.entertainment-execution.v1",
            "execution_id": f"entexec_{uuid4().hex}",
            "persona_id": persona_id,
            "title": title,
            **route,
            "status": "awaiting_private_confirmation",
            "entitlement": "unknown_until_provider_confirms",
            "provider_session": "not_inspected",
            "external_effect": False,
            "provider_open_verified": False,
            "playback_verified": False,
            "created_at": utc_now_iso(),
        }
        execution["execution_hash"] = canonical_hash(execution)
        state = self._read()
        state["executions"] = list(state.get("executions") or [])[-199:] + [execution]
        self._write(state)
        return dict(execution)

    def _find(self, execution_id: str, *, persona_id: str) -> tuple[Dict[str, Any], Dict[str, Any]]:
        state = self._read()
        for execution in state.get("executions") or []:
            if isinstance(execution, dict) and execution.get("execution_id") == execution_id:
                if execution.get("persona_id") != persona_id:
                    raise PermissionError("That entertainment route belongs to another private identity")
                return state, execution
        raise KeyError("Entertainment execution was not found")

    def get(self, execution_id: str, *, persona_id: str) -> Dict[str, Any]:
        _state, execution = self._find(execution_id, persona_id=persona_id)
        return dict(execution)

    def confirm(self, execution_id: str, *, persona_id: str) -> Dict[str, Any]:
        state, execution = self._find(execution_id, persona_id=persona_id)
        if execution.get("status") != "awaiting_private_confirmation":
            raise ValueError("That entertainment route is not waiting for confirmation")
        execution["status"] = "approved_for_device_attempt"
        execution["confirmed_at"] = utc_now_iso()
        execution["external_effect"] = False
        execution["execution_hash"] = canonical_hash({k: v for k, v in execution.items() if k != "execution_hash"})
        self._write(state)
        return dict(execution)

    def record_attempt(
        self,
        execution_id: str,
        *,
        persona_id: str,
        receipt: Dict[str, Any],
        explicit_playback: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        state, execution = self._find(execution_id, persona_id=persona_id)
        if execution.get("status") != "approved_for_device_attempt":
            raise PermissionError("Private confirmation is required before opening that provider route")
        after = dict(receipt.get("after") or {})
        provider_open = bool(receipt.get("verified")) and bool(
            after.get("screen_effect_observed") or after.get("opened") or after.get("foreground_app_id")
        )
        playback = dict(explicit_playback or {})
        playback_verified = bool(playback.get("playing")) and bool(playback.get("title"))
        execution.update(
            {
                "status": "playback_verified" if playback_verified else "provider_open_verified" if provider_open else "device_attempt_unverified",
                "external_effect": provider_open,
                "provider_open_verified": provider_open,
                "playback_verified": playback_verified,
                "attempted_at": utc_now_iso(),
                "device_receipt_id": str(receipt.get("receipt_id") or ""),
                "device_action": str(receipt.get("action") or ""),
                "observed_foreground_app": str(after.get("foreground_app_id") or ""),
                "playback": {"title": str(playback.get("title") or "")[:200], "playing": playback_verified} if playback else None,
            }
        )
        execution["execution_hash"] = canonical_hash({k: v for k, v in execution.items() if k != "execution_hash"})
        if provider_open:
            state.setdefault("last_verified_by_persona", {})[persona_id] = {
                "execution_id": execution["execution_id"],
                "title": execution["title"],
                "provider": execution["provider"],
                "canonical_url": execution["canonical_url"],
                "route_hash": execution["route_hash"],
                "playback_verified": playback_verified,
                "verified_at": utc_now_iso(),
            }
        self._write(state)
        return dict(execution)

    def prepare_continue(self, *, persona_id: str) -> Dict[str, Any]:
        previous = dict((self._read().get("last_verified_by_persona") or {}).get(persona_id) or {})
        if not previous:
            raise ValueError("There is no verified provider route for this private identity")
        return self.prepare(item={"title": previous["title"], "url": previous["canonical_url"]}, persona_id=persona_id)

    def reconcile_telemetry(self, telemetry: Dict[str, Any]) -> Dict[str, Any] | None:
        """Upgrade only a matching persona/provider execution from signed playback facts."""
        if not telemetry.get("authenticated"):
            raise PermissionError("Playback reconciliation requires authenticated provider telemetry")
        persona_id = str(telemetry.get("persona_id") or "")
        provider = str(telemetry.get("provider") or "").casefold()
        content = dict(telemetry.get("content") or {})
        playback = dict(telemetry.get("playback") or {})
        telemetry_id = str(telemetry.get("telemetry_id") or "")
        state = self._read()
        candidates = [
            value for value in state.get("executions") or []
            if isinstance(value, dict)
            and value.get("persona_id") == persona_id
            and str(value.get("provider") or "").casefold().replace(" video", "") == provider.replace(" video", "")
        ]
        if not candidates:
            return None
        execution = candidates[-1]
        id_match = bool(content.get("content_id")) and str(content.get("content_id")) == str(execution.get("provider_content_id"))
        title_match = bool(content.get("title")) and str(content.get("title")).casefold() == str(execution.get("title")).casefold()
        if not (id_match or title_match):
            return None
        playing = playback.get("state") == "playing"
        entitlement = dict(telemetry.get("entitlement") or {})
        execution.update({
            "status": "playback_verified" if playing else "provider_open_verified",
            "provider_open_verified": True,
            "playback_verified": playing,
            "provider_session": "authenticated_adapter",
            "entitlement": entitlement.get("status") if entitlement.get("verified") else execution.get("entitlement", "unknown_until_provider_confirms"),
            "playback": {
                "title": str(content.get("title") or execution.get("title") or "")[:200],
                "playing": playing,
                "state": str(playback.get("state") or "unknown"),
                "position_seconds": int(playback.get("position_seconds") or 0),
                "duration_seconds": int(playback.get("duration_seconds") or 0),
            },
            "provider_telemetry_id": telemetry_id,
            "provider_telemetry_hash": str(telemetry.get("record_hash") or ""),
            "telemetry_reconciled_at": utc_now_iso(),
        })
        execution["execution_hash"] = canonical_hash({key: value for key, value in execution.items() if key != "execution_hash"})
        state.setdefault("last_verified_by_persona", {})[persona_id] = {
            "execution_id": execution["execution_id"],
            "title": execution["title"],
            "provider": execution["provider"],
            "canonical_url": execution["canonical_url"],
            "route_hash": execution["route_hash"],
            "playback_verified": playing,
            "verified_at": utc_now_iso(),
        }
        self._write(state)
        return dict(execution)

    def snapshot(self, *, persona_id: str | None = None) -> Dict[str, Any]:
        state = self._read()
        executions = [dict(value) for value in state.get("executions") or [] if isinstance(value, dict)]
        if persona_id is not None:
            executions = [value for value in executions if value.get("persona_id") == persona_id]
            last = dict((state.get("last_verified_by_persona") or {}).get(persona_id) or {}) or None
        else:
            last = None
        return {
            "schema_version": "pilot.entertainment-execution.snapshot.v1",
            "count": len(executions),
            "latest": executions[-1] if executions else None,
            "last_verified": last,
            "policy": "A provider route is not playback; playback requires explicit title and playing evidence.",
        }
