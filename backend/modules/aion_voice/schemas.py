from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class VoiceRequest:
    text: str
    provider: Optional[str] = None
    voice_id: Optional[str] = None
    model_id: Optional[str] = None


@dataclass(frozen=True)
class VoiceResult:
    ok: bool
    provider: str
    reason: str
    message: str
    fallback: str = "none"
    audio_bytes: Optional[bytes] = None
    media_type: str = "application/json"
    headers: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "provider": self.provider,
            "reason": self.reason,
            "message": self.message,
            "fallback": self.fallback,
            "media_type": self.media_type,
            "headers": dict(self.headers),
            "metadata": dict(self.metadata),
        }
