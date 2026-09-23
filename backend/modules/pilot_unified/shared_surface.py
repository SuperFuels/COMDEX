from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable
from uuid import uuid4

from backend.modules.aion_fabric.canonical import canonical_bytes, canonical_hash, utc_now_iso
from backend.modules.aion_fabric.identity import DeviceIdentity
from backend.modules.aion_fabric.private_identity import ProductionPrivateIdentity
from .workspace_gateway import ProviderIndependentWorkspaceGateway


class SharedSurfaceManifestAuthority:
    """Mother-signed, identity-aware tiles and cache receipts for shared displays."""

    _lock = threading.RLock()
    _live_presentations: dict[str, dict[str, Any]] = {}
    PUBLIC_TILES = (
        ("games", "Games"), ("aion", "AI TV"), ("education_start", "AI Learning"),
        ("shopping", "AI Shopping"),
    )
    PERSONAL_TILES = (
        ("tasks", "Tasks"), ("calendar", "Calendar"), ("files", "Files"), ("work", "Personal Work"),
    )
    HOUSEHOLD_TILES = (("devices", "IoT & Devices"),)
    LOCKED_DOMAINS = (
        ("personal", "Personal"), ("household", "Household"),
        ("workspace", "Workspace"), ("boardroom", "Boardroom"),
    )

    def __init__(
        self, runtime_dir: str | Path, *, issuer: DeviceIdentity,
        identities: ProductionPrivateIdentity,
        workspace_gateway: ProviderIndependentWorkspaceGateway | None = None,
    ) -> None:
        self.root = Path(runtime_dir) / "shared_surfaces"
        self.path = self.root / "state.json"
        self.root.mkdir(parents=True, exist_ok=True)
        self.issuer = issuer
        self.identities = identities
        self.workspace_gateway = workspace_gateway

    @staticmethod
    def _initial() -> dict[str, Any]:
        return {"schema_version": "pilot.shared-surfaces.v1", "manifests": [], "presentation_cache": [], "purges": []}

    def _read(self) -> dict[str, Any]:
        if not self.path.exists():
            return self._initial()
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else self._initial()
        except (OSError, json.JSONDecodeError):
            return self._initial()

    def _write(self, state: dict[str, Any]) -> None:
        state["updated_at"] = utc_now_iso()
        temporary = self.path.with_suffix(".tmp")
        temporary.write_bytes(canonical_bytes(state)); os.chmod(temporary, 0o600); os.replace(temporary, self.path)

    def _active(self) -> dict[str, Any]:
        return dict(self.identities.snapshot().get("active_shared_identity") or {})

    def purge_locked(self, *, surface_id: str) -> dict[str, Any]:
        active = self._active()
        if active:
            return {"purged": False, "reason": "active_session"}
        with self._lock:
            self._live_presentations.pop(self._presentation_key(surface_id), None)
            state = self._read()
            removed = sum(item.get("surface_id") == surface_id for item in state.get("presentation_cache", []))
            state["presentation_cache"] = [item for item in state.get("presentation_cache", []) if item.get("surface_id") != surface_id]
            state["manifests"] = [item for item in state.get("manifests", []) if item.get("surface_id") != surface_id]
            receipt = {"purge_id": f"surface_purge_{uuid4().hex}", "surface_id": surface_id, "removed_records": removed, "created_at": utc_now_iso()}
            state["purges"] = list(state.get("purges") or [])[-199:] + [receipt]
            self._write(state)
            return {"purged": True, **receipt}

    def _presentation_key(self, surface_id: str) -> str:
        return f"{self.root.resolve()}::{surface_id}"

    @staticmethod
    def _bounded_presentation_content(value: Any, *, depth: int = 0) -> Any:
        if depth > 6:
            return "[content depth limited]"
        if isinstance(value, dict):
            if len(value) > 80:
                raise ValueError("Television presentation contains too many fields")
            return {
                str(key)[:100]: SharedSurfaceManifestAuthority._bounded_presentation_content(item, depth=depth + 1)
                for key, item in value.items()
                if not any(marker in str(key).casefold() for marker in ("password", "secret", "token", "credential", "private_key", "api_key", "cookie"))
            }
        if isinstance(value, (list, tuple)):
            return [SharedSurfaceManifestAuthority._bounded_presentation_content(item, depth=depth + 1) for item in list(value)[:100]]
        if isinstance(value, str):
            return value[:4_000]
        if isinstance(value, (int, float, bool)) or value is None:
            return value
        return str(value)[:500]

    def present(
        self, *, manifest: dict[str, Any], content_kind: str, content_id: str,
        title: str, content: Any, authority_domain: str,
    ) -> dict[str, Any]:
        """Deliberately project bounded repository-backed content into volatile TV memory."""
        active = self._active()
        if not self.verify(manifest) or not manifest.get("private_session"):
            raise PermissionError("An active signed shared-screen manifest is required")
        if str(active.get("persona_id") or "") != str(manifest.get("persona_id") or ""):
            raise PermissionError("The active television identity changed")
        if content_kind not in {"document", "dashboard", "briefing"}:
            raise ValueError("That content cannot be presented on a shared television")
        if authority_domain not in set(manifest.get("authority_domains") or ()):
            raise PermissionError("The television manifest does not grant that authority domain")
        clean_id = " ".join(str(content_id or "").split())[:240]
        clean_title = " ".join(str(title or "").split())[:160]
        if not clean_id or not clean_title:
            raise ValueError("Presentation title and source identifier are required")
        bounded = self._bounded_presentation_content(content)
        encoded = canonical_bytes(bounded)
        if len(encoded) > 256_000:
            raise ValueError("Television presentation exceeds the private display limit")
        now = datetime.now(timezone.utc)
        manifest_expiry = datetime.fromisoformat(str(manifest["expires_at"]).replace("Z", "+00:00"))
        expiry = min(manifest_expiry, now + timedelta(minutes=10))
        presentation = {
            "schema_version": "pilot.shared-presentation.v1",
            "presentation_id": f"surface_presentation_{uuid4().hex}",
            "surface_id": str(manifest["surface_id"]),
            "manifest_id": str(manifest["manifest_id"]),
            "persona_id": str(manifest["persona_id"]),
            "authority_domain": authority_domain,
            "content_kind": content_kind,
            "content_id": clean_id,
            "title": clean_title,
            "content": bounded,
            "content_hash": canonical_hash(bounded),
            "created_at": utc_now_iso(),
            "expires_at": expiry.isoformat(),
            "volatile_only": True,
        }
        with self._lock:
            self._live_presentations[self._presentation_key(str(manifest["surface_id"]))] = presentation
        receipt = self.record_deliberate_presentation(
            manifest=manifest, content_kind=content_kind, content_id=clean_id,
            content_hash=presentation["content_hash"],
        )
        return {**receipt, "title": clean_title, "authority_domain": authority_domain, "expires_at": presentation["expires_at"]}

    def active_presentation(self, *, surface_id: str) -> dict[str, Any] | None:
        active = self._active()
        key = self._presentation_key(surface_id)
        with self._lock:
            presentation = dict(self._live_presentations.get(key) or {})
        if not active or not presentation:
            if not active:
                self.purge_locked(surface_id=surface_id)
            return None
        try:
            expires = datetime.fromisoformat(str(presentation["expires_at"]).replace("Z", "+00:00"))
        except (KeyError, ValueError):
            expires = datetime.min.replace(tzinfo=timezone.utc)
        if expires <= datetime.now(timezone.utc) or presentation.get("persona_id") != active.get("persona_id"):
            with self._lock:
                self._live_presentations.pop(key, None)
            return None
        return presentation

    def dismiss_presentation(self, *, surface_id: str, persona_id: str) -> dict[str, Any]:
        active = self._active()
        if str(active.get("persona_id") or "") != str(persona_id or ""):
            raise PermissionError("Only the active television identity may dismiss private content")
        with self._lock:
            removed = self._live_presentations.pop(self._presentation_key(surface_id), None)
        return {"dismissed": bool(removed), "surface_id": surface_id, "persona_id": persona_id, "dismissed_at": utc_now_iso()}

    def issue_home_manifest(
        self, *, surface_id: str, workspace_manifests: Iterable[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        active = self._active()
        if not active:
            self.purge_locked(surface_id=surface_id)
        persona_id = str(active.get("persona_id") or "public")
        tiles = [
            {"tile_id": key, "label": label, "privacy": "public", "authority_domain": "public"}
            for key, label in self.PUBLIC_TILES
        ]
        if active:
            identity = self.identities.snapshot(viewer_persona_id=persona_id)
            profile = next((item for item in identity.get("profiles", []) if item.get("persona_id") == persona_id), {})
            tiles += [
                {
                    "tile_id": key, "label": label, "privacy": "private",
                    "authority_domain": "personal", "role": str(profile.get("role") or "adult"),
                }
                for key, label in self.PERSONAL_TILES
            ]
            tiles += [
                {
                    "tile_id": key, "label": label, "privacy": "household_shared",
                    "authority_domain": "household", "role": str(profile.get("role") or "adult"),
                }
                for key, label in self.HOUSEHOLD_TILES
            ]
        else:
            tiles += [
                {"tile_id": key, "label": label, "privacy": "locked", "authority_domain": key}
                for key, label in self.LOCKED_DOMAINS
            ]
        supplied_manifests = workspace_manifests
        if supplied_manifests is None and active and self.workspace_gateway is not None:
            lease_id = f"shared-screen/{canonical_hash({'surface_id': surface_id, 'persona_id': persona_id, 'authorizing_device_id': active.get('device_id'), 'activated_at': active.get('activated_at')})[:24]}"
            supplied_manifests = self.workspace_gateway.surface_manifests_for(
                persona_id=persona_id, device_id=str(active.get("device_id") or "trusted-phone"),
                surface_id=surface_id, lease_id=lease_id,
                ttl_seconds=min(300, max(30, int(active.get("idle_timeout_seconds") or 300))),
            )
        for envelope in list(supplied_manifests or ())[:24]:
            if not active or not ProviderIndependentWorkspaceGateway.verify_signed_manifest(
                envelope, expected_persona_id=persona_id, expected_device_id=surface_id,
            ):
                continue
            manifest = dict(envelope.get("manifest") or {})
            space = dict(envelope.get("space") or {})
            membership = dict(envelope.get("membership_summary") or {})
            kind = str(space.get("kind") or "workspace")
            domain = "boardroom" if kind == "boardroom" else "workspace"
            label = str(space.get("display_name") or ("Boardroom" if domain == "boardroom" else "Workspace"))[:80]
            tiles.append({
                "tile_id": f"{domain}.{manifest.get('space_id')}", "label": label,
                "privacy": "organisation" if domain == "boardroom" else "workspace",
                "authority_domain": domain, "space_id": manifest.get("space_id"),
                "membership_id": envelope.get("membership_id"), "role": membership.get("role_id"),
                "capabilities": list(manifest.get("capabilities") or [])[:32],
            })
        expiry = str(active.get("expires_at") or (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat())
        with self._lock:
            current = self._read()
            previous = next((
                item for item in reversed(list(current.get("manifests") or []))
                if item.get("surface_id") == surface_id and item.get("persona_id") == persona_id
                and item.get("tiles") == tiles and self.verify(item)
                and (not active or item.get("expires_at") == expiry)
            ), None)
        if previous is not None:
            return dict(previous)
        payload = {
            "schema_version": "pilot.shared-surface-manifest.v1", "manifest_id": f"surface_manifest_{uuid4().hex}",
            "surface_id": surface_id, "persona_id": persona_id, "display_name": str(active.get("display_name") or ""),
            "tiles": tiles, "private_session": bool(active), "issued_at": utc_now_iso(), "expires_at": expiry,
            "authority_domains": sorted({str(item.get("authority_domain")) for item in tiles}),
            "private_message_content_included": False, "approval_content_included": False,
        }
        envelope = {**payload, "payload_hash": canonical_hash(payload), "issuer_public_key": self.issuer.public_key_b64}
        envelope["signature"] = self.issuer.sign(canonical_bytes(envelope))
        with self._lock:
            state = self._read(); state["manifests"] = list(state.get("manifests") or [])[-49:] + [envelope]; self._write(state)
        return envelope

    @staticmethod
    def verify(envelope: dict[str, Any]) -> bool:
        try:
            signature = str(envelope["signature"]); unsigned = {key: value for key, value in envelope.items() if key != "signature"}
            payload = {key: value for key, value in unsigned.items() if key not in {"payload_hash", "issuer_public_key"}}
            return (
                unsigned["schema_version"] == "pilot.shared-surface-manifest.v1"
                and canonical_hash(payload) == unsigned["payload_hash"]
                and datetime.fromisoformat(str(unsigned["expires_at"]).replace("Z", "+00:00")) > datetime.now(timezone.utc)
                and DeviceIdentity.verify(str(unsigned["issuer_public_key"]), canonical_bytes(unsigned), signature)
            )
        except (KeyError, TypeError, ValueError):
            return False

    def record_deliberate_presentation(
        self, *, manifest: dict[str, Any], content_kind: str, content_id: str, content_hash: str,
    ) -> dict[str, Any]:
        if not self.verify(manifest) or not manifest.get("private_session"):
            raise PermissionError("An active signed shared-screen manifest is required")
        if content_kind not in {"document", "dashboard", "briefing"} or not content_id or len(content_hash) != 64:
            raise ValueError("The presentation scope is invalid")
        record = {
            "presentation_id": f"surface_presentation_{uuid4().hex}", "surface_id": manifest["surface_id"],
            "persona_id": manifest["persona_id"], "content_kind": content_kind, "content_id": content_id,
            "content_hash": content_hash, "status": "deliberately_presented", "cached_content_retained": False,
            "created_at": utc_now_iso(),
        }
        with self._lock:
            state = self._read(); state["presentation_cache"] = list(state.get("presentation_cache") or [])[-49:] + [record]; self._write(state)
        return dict(record)
