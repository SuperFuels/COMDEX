from __future__ import annotations

import json
import os
import re
import threading
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict
from uuid import uuid4

from .canonical import canonical_bytes, canonical_hash, utc_now_iso


class MultiFrameScreenPerception:
    """Stabilize structured screen meaning across a short, source-pixel-free window."""

    _lock = threading.RLock()
    _POSITION = re.compile(r"\b(?P<position>(?:\d{1,2}:)?\d{1,2}:\d{2})\s*/\s*(?P<duration>(?:\d{1,2}:)?\d{1,2}:\d{2})\b")
    MAX_FRAMES = 12

    def __init__(self, runtime_dir: str | Path) -> None:
        self.root = Path(runtime_dir) / "perception"
        self.path = self.root / "multi_frame_timeline.json"
        self.root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _initial() -> Dict[str, Any]:
        return {
            "schema_version": "pilot.multi-frame-perception.store.v1",
            "frames": [],
            "current": None,
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

    @staticmethod
    def _timestamp(value: str) -> datetime | None:
        try:
            return datetime.fromisoformat(value).astimezone(timezone.utc)
        except (TypeError, ValueError):
            return None

    @classmethod
    def _playback_position(cls, texts: list[str]) -> Dict[str, Any] | None:
        match = cls._POSITION.search(" ".join(texts))
        if not match:
            return None
        return {
            "position": match.group("position"),
            "duration": match.group("duration"),
            "source": "owner_camera_ocr",
            "verified_by_provider": False,
        }

    def accept(
        self,
        *,
        perception: Dict[str, Any],
        fused: Dict[str, Any],
        observer_session_id: str | None,
        provider_telemetry: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        image_hash = str(perception.get("image_sha256") or "")
        if len(image_hash) != 64:
            raise ValueError("A structured source image hash is required")
        frame = {
            "frame_id": f"frame_{uuid4().hex}",
            "observer_session_id": observer_session_id,
            "image_sha256": image_hash,
            "observed_at": str(perception.get("observed_at") or utc_now_iso()),
            "surface": str(fused.get("surface") or "unknown")[:80],
            "app": dict(fused.get("app") or {}),
            "confidence": round(float(fused.get("confidence") or 0), 3),
            "summary": str(fused.get("summary") or "")[:300],
            "subtitles": list((fused.get("subtitles") or {}).get("lines") or [])[:3],
            "scoreboard": dict(fused.get("scoreboard") or {}),
            "provider": {
                key: value for key, value in dict(fused.get("provider_metadata") or {}).items()
                if key in {
                    "provider", "application_provider_hint", "content_id", "title", "channel_title",
                    "metadata_status", "availability_verified", "catalogue_identity_verified",
                    "current_playback_verified", "attribution",
                }
            } or None,
            "programme_candidates": [
                {
                    "title": str(value.get("title") or "")[:160],
                    "ocr_confidence": round(float(value.get("ocr_confidence") or 0), 3),
                    "geometry_score": round(float(value.get("geometry_score") or 0), 3),
                    "source": str(value.get("source") or "owner_capture")[:80],
                }
                for value in list(fused.get("programme_candidates") or [])[:5]
                if isinstance(value, dict) and str(value.get("title") or "").strip()
            ],
            "provider_telemetry": {
                "provider": str(provider_telemetry.get("provider") or "")[:80],
                "content_id": str((provider_telemetry.get("content") or {}).get("content_id") or "")[:160],
                "title": str((provider_telemetry.get("content") or {}).get("title") or "")[:240],
                "playback": dict(provider_telemetry.get("playback") or {}),
                "entitlement": dict(provider_telemetry.get("entitlement") or {}),
                "authenticated": bool(provider_telemetry.get("authenticated")),
                "record_hash": str(provider_telemetry.get("record_hash") or ""),
            } if provider_telemetry else None,
            "playback_position": (
                {
                    "position_seconds": int((provider_telemetry.get("playback") or {}).get("position_seconds") or 0),
                    "duration_seconds": int((provider_telemetry.get("playback") or {}).get("duration_seconds") or 0),
                    "state": str((provider_telemetry.get("playback") or {}).get("state") or "unknown"),
                    "source": "signed_provider_adapter",
                    "verified_by_provider": True,
                }
                if provider_telemetry and provider_telemetry.get("authenticated") and (provider_telemetry.get("playback") or {}).get("state") != "unknown"
                else self._playback_position([str(value) for value in perception.get("texts") or []])
            ),
            "source_pixels_retained": False,
        }
        frame["frame_hash"] = canonical_hash(frame)
        with self._lock:
            state = self._read()
            previous_frames = [value for value in state.get("frames") or [] if isinstance(value, dict)]
            if previous_frames and previous_frames[-1].get("image_sha256") == image_hash:
                current = dict(state.get("current") or {})
                current["duplicate_frame_ignored"] = True
                return current
            frames = (previous_frames + [frame])[-self.MAX_FRAMES:]
            now = self._timestamp(frame["observed_at"]) or datetime.now(timezone.utc)
            recent = [
                value for value in frames
                if (stamp := self._timestamp(str(value.get("observed_at") or ""))) is not None
                and 0 <= (now - stamp).total_seconds() <= 90
            ] or [frame]
            previous_current = dict(state.get("current") or {})
            previous_surface = (
                str(previous_current.get("surface") or "")
                if previous_current.get("surface_stable") else ""
            )
            latest_surface = str(frame.get("surface") or "unknown")
            transition_pending = bool(previous_surface and latest_surface != previous_surface)
            if transition_pending:
                trailing: list[Dict[str, Any]] = []
                for value in reversed(recent):
                    if str(value.get("surface") or "unknown") != latest_surface:
                        break
                    trailing.append(value)
                trailing.reverse()
                # Two consecutive observations on the new surface are enough to
                # start a clean context window. Old programme/title evidence is
                # not allowed to leak into the new application or input.
                if len(trailing) >= 2:
                    recent = trailing
            surfaces = [str(value.get("surface") or "unknown") for value in recent]
            counts = Counter(surfaces)
            stable_surface, stable_count = counts.most_common(1)[0]
            surface_ratio = stable_count / len(recent)
            surface_stable = stable_count >= 2 and surface_ratio >= 2 / 3
            context_changed = bool(
                previous_surface and surface_stable and stable_surface != previous_surface
            )
            telemetry_titles: list[str] = []
            official_titles: list[str] = []
            catalogue_titles: list[str] = []
            ocr_titles: list[str] = []
            for value in recent:
                telemetry = value.get("provider_telemetry") if isinstance(value.get("provider_telemetry"), dict) else {}
                metadata = value.get("provider") if isinstance(value.get("provider"), dict) else {}
                telemetry_title = str(telemetry.get("title") or "").strip()
                metadata_title = str(metadata.get("title") or "").strip()
                metadata_status = str(metadata.get("metadata_status") or "")
                if telemetry_title and telemetry.get("authenticated"):
                    telemetry_titles.append(telemetry_title)
                elif metadata_title and metadata_status == "official_api_verified":
                    official_titles.append(metadata_title)
                elif metadata_title and metadata_status == "public_catalogue_exact_match":
                    catalogue_titles.append(metadata_title)
                for candidate in list(value.get("programme_candidates") or []):
                    if isinstance(candidate, dict):
                        candidate_title = " ".join(str(candidate.get("title") or "").split()).strip()[:160]
                        if candidate_title:
                            ocr_titles.append(candidate_title)

            stable_title = ""
            title_count = 0
            identity_source = "none"
            for title_values, source in (
                (telemetry_titles, "signed_provider_adapter"),
                (official_titles, "official_provider_metadata"),
                (catalogue_titles, "public_programme_catalogue"),
                (ocr_titles, "repeated_ocr"),
            ):
                title_counts = Counter(value for value in title_values if value)
                if title_counts:
                    candidate_title, candidate_count = title_counts.most_common(1)[0]
                    required = 1 if source in {"signed_provider_adapter", "public_programme_catalogue"} else 2
                    if candidate_count >= required:
                        stable_title, title_count, identity_source = candidate_title, candidate_count, source
                        break
            subtitle_timeline: list[str] = []
            for value in recent:
                for line in value.get("subtitles") or []:
                    clean = " ".join(str(line).split()).strip()[:240]
                    if clean and (not subtitle_timeline or subtitle_timeline[-1] != clean):
                        subtitle_timeline.append(clean)
            positions = [dict(value.get("playback_position") or {}) for value in recent if value.get("playback_position")]
            unique_hashes = len({str(value.get("image_sha256") or "") for value in recent})
            current: Dict[str, Any] = {
                "schema_version": "pilot.multi-frame-perception.v1",
                "timeline_id": f"timeline_{uuid4().hex}",
                "observer_session_id": observer_session_id,
                "frame_count": len(recent),
                "unique_frame_count": unique_hashes,
                "surface": stable_surface if surface_stable else "uncertain",
                "surface_stable": surface_stable,
                "surface_support": {"matching_frames": stable_count, "total_frames": len(recent), "ratio": round(surface_ratio, 3)},
                "programme": {
                    "title": stable_title,
                    "stable": bool(stable_title),
                    "supporting_frames": title_count,
                    "identity_source": identity_source,
                    "provider_verified": identity_source in {"signed_provider_adapter", "official_provider_metadata"},
                    "catalogue_verified": identity_source == "public_programme_catalogue",
                    "current_playback_verified": bool(stable_title and identity_source == "signed_provider_adapter" and any(
                        (value.get("provider_telemetry") or {}).get("authenticated")
                        and str(((value.get("provider_telemetry") or {}).get("playback") or {}).get("state") or "unknown") != "unknown"
                        for value in recent
                    )),
                    "signed_playback_telemetry": bool(any((value.get("provider_telemetry") or {}).get("authenticated") for value in recent)),
                },
                "subtitle_timeline": subtitle_timeline[-12:],
                "playback_position": positions[-1] if positions else None,
                "scene_changed": unique_hashes >= 2,
                "context_transition": {
                    "pending": transition_pending and not context_changed,
                    "changed": context_changed,
                    "from_surface": previous_surface or None,
                    "to_surface": stable_surface if context_changed else latest_surface if transition_pending else None,
                    "old_context_evidence_reused": False if transition_pending else None,
                },
                "confidence": round(min(1.0, (surface_ratio * 0.55) + (min(len(recent), 3) / 3 * 0.25) + (0.2 if stable_title else 0)), 3),
                "latest_frame_hash": frame["frame_hash"],
                "source_pixels_retained": False,
                "raw_audio_retained": False,
                "created_at": utc_now_iso(),
            }
            current["evidence_hash"] = canonical_hash(current)
            state["frames"] = frames
            state["current"] = current
            self._write(state)
            return dict(current)

    def snapshot(self) -> Dict[str, Any]:
        state = self._read()
        return {
            "schema_version": "pilot.multi-frame-perception.snapshot.v1",
            "current": state.get("current"),
            "retained_structured_frames": len(state.get("frames") or []),
            "maximum_structured_frames": self.MAX_FRAMES,
            "source_pixels_retained": False,
        }
