from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Iterable

from .canonical import canonical_bytes, canonical_hash, utc_now_iso


class LiveContextStore:
    """Build a small, evidence-labelled context only after an explicit Pilot request."""

    def __init__(self, runtime_dir: str | Path) -> None:
        self.path = Path(runtime_dir) / "live" / "latest_context.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def build(
        self,
        *,
        device_state: Dict[str, Any],
        recent_transcripts: Iterable[str] = (),
        belief: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        transcripts = [" ".join(str(item).split()).strip()[:320] for item in recent_transcripts]
        transcripts = [item for item in transcripts if item and "pilot" not in item.lower()][-4:]
        app_id = str(device_state.get("foreground_app_id") or "unknown")[:160]
        app_title = str(device_state.get("foreground_app_title") or app_id)[:160]
        playback = {
            key: device_state[key]
            for key in ("media_title", "title", "playback_state", "position", "duration")
            if device_state.get(key) is not None
        }
        record = {
            "schema_version": "pilot.live.context.v1",
            "created_at": utc_now_iso(),
            "surface": str((belief or {}).get("surface") or "unknown")[:80],
            "app": {"id": app_id, "title": app_title},
            "playback": playback,
            "recent_statement": transcripts[-1] if transcripts else "",
            "recent_transcripts": transcripts,
            "evidence": [
                {"kind": "webos_state", "detail": f"Foreground application reported as {app_title}"},
                *(
                    [{"kind": "ephemeral_local_transcript", "detail": "Recent television speech was transcribed locally"}]
                    if transcripts else []
                ),
            ],
            "confidence": 0.92 if app_id != "unknown" else 0.55,
            "privacy": {
                "raw_audio_retained": False,
                "rolling_audio_seconds": 30,
                "context_persisted_only_after_explicit_request": True,
            },
        }
        record["context_hash"] = canonical_hash(record)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_bytes(canonical_bytes(record))
        os.replace(temporary, self.path)
        return record

    def latest(self) -> Dict[str, Any] | None:
        if not self.path.exists():
            return None
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else None
        except (OSError, json.JSONDecodeError):
            return None
