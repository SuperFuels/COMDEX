from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict
from uuid import uuid4

from .canonical import canonical_bytes, canonical_hash, utc_now_iso


class LiveMediaAuthority:
    """Fail-closed authorization gate for overlays, subtitles, dubbing, audio DSP and clips."""

    def __init__(self, runtime_dir: str | Path) -> None:
        self.root = Path(runtime_dir) / "live_media_authority"
        self.path = self.root / "latest.json"
        self.root.mkdir(parents=True, exist_ok=True)

    def _record(self, kind: str, *, authorized: bool, reason: str, evidence: Dict[str, Any]) -> Dict[str, Any]:
        record = {
            "authority_check_id": f"authority_{uuid4().hex}",
            "created_at": utc_now_iso(),
            "kind": kind,
            "authorized": authorized,
            "reason": reason[:500],
            "evidence": evidence,
            "protected_media_copied": False,
            "model_output_treated_as_permission": False,
        }
        record["record_hash"] = canonical_hash(record)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_bytes(canonical_bytes(record))
        os.chmod(temporary, 0o600)
        os.replace(temporary, self.path)
        return record

    def subtitle_projection(self, *, platform_grants: Dict[str, Any], subtitle_rights: Dict[str, Any]) -> Dict[str, Any]:
        overlay = bool(platform_grants.get("native_overlay_authority"))
        captions = bool(platform_grants.get("caption_projection_authority"))
        rights = bool(subtitle_rights.get("projection_authorized"))
        authorized = overlay and captions and rights
        reason = "Native overlay, caption projection and subtitle rights are verified." if authorized else "Projection requires native overlay authority, caption projection authority and explicit subtitle rights."
        return self._record("synchronized_subtitle_projection", authorized=authorized, reason=reason, evidence={"native_overlay_authority": overlay, "caption_projection_authority": captions, "projection_rights": rights})

    def local_dubbing(self, *, platform_grants: Dict[str, Any], content_rights: Dict[str, Any]) -> Dict[str, Any]:
        audio_route = bool(platform_grants.get("authorized_audio_output_route"))
        rights = bool(content_rights.get("local_dubbing_authorized"))
        authorized = audio_route and rights
        reason = "The platform audio route and content dubbing rights are verified." if authorized else "Local dubbing requires an authorized audio route and explicit rights for this content."
        return self._record("authorized_local_dubbing", authorized=authorized, reason=reason, evidence={"audio_route_authorized": audio_route, "dubbing_rights": rights})

    def audio_enhancement(self, *, platform_grants: Dict[str, Any], preset: str) -> Dict[str, Any]:
        clean = str(preset).strip().lower()
        if clean not in {"dialogue_clarity", "background_reduction", "accessibility"}:
            raise ValueError("Unsupported audio enhancement preset")
        control = bool(platform_grants.get("audio_dsp_control"))
        presets = {str(value).strip().lower() for value in list(platform_grants.get("audio_dsp_presets") or [])}
        authorized = control and clean in presets
        reason = "The hardware exposes this signed DSP preset." if authorized else "This hardware has not exposed the requested signed DSP control."
        return self._record("audio_enhancement", authorized=authorized, reason=reason, evidence={"preset": clean, "audio_dsp_control": control, "preset_exposed": clean in presets})

    def compact_overlay(self, *, platform_grants: Dict[str, Any]) -> Dict[str, Any]:
        authorized = bool(platform_grants.get("native_overlay_authority")) and bool(platform_grants.get("dismissible_overlay_control"))
        reason = "The native application has explicit dismissible-overlay authority." if authorized else "The gateway cannot place an overlay over third-party playback without native platform authority."
        return self._record("compact_native_overlay", authorized=authorized, reason=reason, evidence={"native_overlay_authority": bool(platform_grants.get("native_overlay_authority")), "dismissible_overlay_control": bool(platform_grants.get("dismissible_overlay_control"))})

    def authorized_highlights(self, *, event: Dict[str, Any]) -> Dict[str, Any]:
        links = []
        for item in list(event.get("authorized_highlights") or [])[:30]:
            if not isinstance(item, dict):
                continue
            url = str(item.get("url") or "")[:1000]
            if not url.startswith("https://") or not item.get("rights_authorized") or not item.get("provider_verified"):
                continue
            links.append({
                "title": str(item.get("title") or "Official highlight")[:180],
                "url": url,
                "provider": str(item.get("provider") or "authorized event feed")[:120],
                "incident_id": str(item.get("incident_id") or "")[:100],
            })
        authorized = bool(links)
        reason = f"{len(links)} provider-verified, rights-authorized highlight routes are available." if authorized else "No provider-verified, rights-authorized highlight routes were supplied; Pilot will not scrape or copy programme video."
        return self._record("authorized_event_highlights", authorized=authorized, reason=reason, evidence={"routes": links, "routes_only": True, "video_downloaded": False})

    def latest(self) -> Dict[str, Any] | None:
        if not self.path.exists():
            return None
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else None
        except (OSError, json.JSONDecodeError):
            return None
