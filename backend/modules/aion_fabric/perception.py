from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
import threading
from pathlib import Path
from typing import Any, Callable, Dict

from .canonical import canonical_bytes, utc_now_iso


class PhoneVisualPerception:
    """Consent-driven, local-only TV screen perception from a phone capture.

    The image exists only for the duration of local Apple Vision analysis. The
    persisted record contains structured OCR/classification evidence and the
    payload hash, never the source pixels.
    """

    MAX_IMAGE_BYTES = 5 * 1024 * 1024
    _lock = threading.RLock()

    def __init__(
        self,
        runtime_dir: str | Path,
        *,
        analyzer: Callable[[Path], Dict[str, Any]] | None = None,
    ) -> None:
        self.root = Path(runtime_dir) / "perception"
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "latest_phone_vision.json"
        self.profile_path = self.root / "netflix_profiles.json"
        self.analyzer = analyzer or self._apple_vision

    @staticmethod
    def _netflix_profile_names(text_observations: list[Dict[str, Any]]) -> list[str]:
        ignored = {"netflix", "choose a profile", "choose profile", "who's watching?", "whos watching?", "manage profiles"}
        names: list[str] = []
        for item in text_observations:
            value = " ".join(str(item.get("text") or "").split()).strip()
            normalised = value.lower().rstrip("?")
            if not value or normalised in ignored:
                continue
            # Profile labels occupy the chooser region. This excludes titles
            # and programme copy visible behind translucent Netflix panels.
            if float(item.get("x") or 0) > 0.65 or len(value) > 32:
                continue
            if len(value.split()) > 3 or (value.isupper() and len(value) > 8):
                continue
            if value not in names:
                names.append(value)
        return names[:5]

    @staticmethod
    def _image_suffix(payload: bytes, media_type: str) -> str:
        if payload.startswith(b"\xff\xd8\xff") and media_type in {"image/jpeg", "image/jpg", "application/octet-stream"}:
            return ".jpg"
        if payload.startswith(b"\x89PNG\r\n\x1a\n") and media_type in {"image/png", "application/octet-stream"}:
            return ".png"
        if len(payload) >= 12 and payload[4:8] == b"ftyp" and media_type in {"image/heic", "image/heif", "application/octet-stream"}:
            return ".heic"
        raise ValueError("Phone perception accepts only JPEG, PNG, or HEIC images")

    def _apple_vision(self, image_path: Path) -> Dict[str, Any]:
        script = Path(__file__).with_name("apple_vision.swift")
        if not script.exists() or not Path("/usr/bin/swift").exists():
            raise RuntimeError("Local Apple Vision perception is unavailable on this mother node")
        try:
            result = subprocess.run(
                ["/usr/bin/swift", str(script), str(image_path)],
                capture_output=True,
                text=True,
                timeout=35,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise RuntimeError("Local Apple Vision analysis failed to start") from exc
        if result.returncode != 0:
            detail = " ".join(result.stderr.split())[:300]
            raise RuntimeError(f"Local Apple Vision analysis failed: {detail or 'unknown error'}")
        try:
            value = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError("Local Apple Vision returned invalid structured output") from exc
        if not isinstance(value, dict):
            raise RuntimeError("Local Apple Vision returned a non-object result")
        return value

    @staticmethod
    def _infer_state(texts: list[str], labels: list[Dict[str, Any]]) -> Dict[str, Any]:
        joined = " ".join(texts).lower()
        label_names = " ".join(str(item.get("label") or "") for item in labels).lower()
        surface = "unknown"
        view = "camera_observation"
        cues: list[str] = []
        confidence = 0.45

        if "netflix" in joined:
            surface = "netflix"
            confidence = 0.82
            cues.append("Netflix text detected")
            if any(term in joined for term in ("who's watching", "whos watching", "choose profile", "choose a profile", "manage profiles")):
                view = "profile_chooser"
                confidence = 0.93
                cues.append("profile chooser language detected")
            elif any(term in joined for term in ("search", "explore titles related to")):
                view = "search"
                confidence = 0.88
                cues.append("search language detected")
            elif any(term in joined for term in ("episodes", "more like this", "play from beginning", "resume")):
                view = "title_detail_or_playback_overlay"
                confidence = 0.84
                cues.append("title or playback controls detected")
            else:
                view = "browse"
        elif "google" in joined and any(term in joined for term in ("accept all", "reject all", "before you continue", "cookies")):
            surface = "web_browser"
            view = "google_consent"
            confidence = 0.94
            cues.append("Google consent language detected")
        elif any(term in joined for term in ("aion", "tessaris", "device mesh", "mother connected")):
            surface = "aion_canvas"
            view = "aion"
            confidence = 0.92
            cues.append("Pilot Canvas language detected")
        elif "youtube" in joined:
            surface = "youtube"
            view = "browse_or_playback"
            confidence = 0.82
            cues.append("YouTube text detected")
        elif any(term in label_names for term in ("television", "screen", "monitor")):
            cues.append("screen-like image classified")
            confidence = 0.55

        return {
            "surface": surface,
            "view": view,
            "confidence": confidence,
            "cues": cues,
            "summary": "; ".join(cues) if cues else "No supported TV surface could be identified",
        }

    def analyze(self, payload: bytes, media_type: str) -> Dict[str, Any]:
        if not payload or len(payload) > self.MAX_IMAGE_BYTES:
            raise ValueError("Phone perception image must be between 1 byte and 5 MiB")
        suffix = self._image_suffix(payload, media_type.split(";", 1)[0].strip().lower())
        digest = hashlib.sha256(payload).hexdigest()
        temporary_path: Path | None = None
        try:
            descriptor, name = tempfile.mkstemp(prefix="aion-phone-vision-", suffix=suffix, dir=self.root)
            temporary_path = Path(name)
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(payload)
            raw = self.analyzer(temporary_path)
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)

        texts = [" ".join(str(item).split())[:240] for item in list(raw.get("texts") or []) if str(item).strip()][:40]
        labels = [
            {"label": str(item.get("label") or "")[:100], "confidence": round(float(item.get("confidence") or 0), 4)}
            for item in list(raw.get("labels") or [])[:12]
            if isinstance(item, dict) and str(item.get("label") or "").strip()
        ]
        text_observations = [
            {
                "text": " ".join(str(item.get("text") or "").split())[:240],
                "confidence": round(max(0.0, min(float(item.get("confidence") or 0), 1.0)), 4),
                "x": round(max(0.0, min(float(item.get("x") or 0), 1.0)), 5),
                "y": round(max(0.0, min(float(item.get("y") or 0), 1.0)), 5),
                "width": round(max(0.0, min(float(item.get("width") or 0), 1.0)), 5),
                "height": round(max(0.0, min(float(item.get("height") or 0), 1.0)), 5),
            }
            for item in list(raw.get("text_observations") or [])[:40]
            if isinstance(item, dict) and str(item.get("text") or "").strip()
        ]
        inferred = self._infer_state(texts, labels)
        if inferred.get("view") == "profile_chooser":
            profile_names = self._netflix_profile_names(text_observations)
            if profile_names:
                inferred["profile_names"] = profile_names
        record = {
            "schema_version": "aion.phone.visual-perception.v1",
            "source": "owner_captured_phone_camera",
            "consent": "explicit_capture_submission",
            "image_sha256": digest,
            "image_bytes": len(payload),
            "image_retained": False,
            "texts": texts,
            "text_observations": text_observations,
            "labels": labels,
            "inference": inferred,
            "observed_at": utc_now_iso(),
        }
        with self._lock:
            temporary = self.path.with_suffix(".tmp")
            temporary.write_bytes(canonical_bytes(record))
            os.replace(temporary, self.path)
            if inferred.get("profile_names"):
                profile_record = {
                    "schema_version": "pilot.netflix-profile-labels.v1",
                    "names": list(inferred["profile_names"]),
                    "source_image_sha256": digest,
                    "observed_at": record["observed_at"],
                }
                profile_temporary = self.profile_path.with_suffix(".tmp")
                profile_temporary.write_bytes(canonical_bytes(profile_record))
                os.replace(profile_temporary, self.profile_path)
        return record

    def known_profiles(self) -> Dict[str, Any]:
        with self._lock:
            try:
                value = json.loads(self.profile_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                return {"schema_version": "pilot.netflix-profile-labels.v1", "names": []}
            return value if isinstance(value, dict) else {"schema_version": "pilot.netflix-profile-labels.v1", "names": []}

    def save_profile_names(self, names: list[str]) -> Dict[str, Any]:
        cleaned = [" ".join(str(value).split())[:32] for value in list(names)[:5]]
        if len(cleaned) != 5 or any(not value for value in cleaned):
            raise ValueError("Enter all five Netflix profile names in screen order")
        if len({value.casefold() for value in cleaned}) != 5:
            raise ValueError("Netflix profile names must be distinct")
        record = {
            "schema_version": "pilot.netflix-profile-labels.v1",
            "names": cleaned,
            "source": "owner_private_controller",
            "observed_at": utc_now_iso(),
        }
        with self._lock:
            temporary = self.profile_path.with_suffix(".tmp")
            temporary.write_bytes(canonical_bytes(record))
            os.replace(temporary, self.profile_path)
        return record

    def latest(self) -> Dict[str, Any] | None:
        with self._lock:
            if not self.path.exists():
                return None
            try:
                value = json.loads(self.path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                return None
            return value if isinstance(value, dict) else None
