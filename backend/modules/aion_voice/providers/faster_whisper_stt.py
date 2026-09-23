from __future__ import annotations

import os
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


AION_FAST_WHISPER_STT_VERSION = "aion.o21d.faster_whisper_stt.v0.1"


@dataclass(frozen=True)
class SttResult:
    ok: bool
    provider: str
    text: str = ""
    language: str | None = None
    segments: list[dict[str, Any]] | None = None
    reason: str | None = None
    message: str | None = None
    local: bool = True
    model: str | None = None
    device: str | None = None
    compute_type: str | None = None
    version: str = AION_FAST_WHISPER_STT_VERSION

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        if data["segments"] is None:
            data["segments"] = []
        return data


def get_faster_whisper_config() -> dict[str, str]:
    return {
        "provider": "faster_whisper",
        "model": os.getenv("AION_WHISPER_MODEL", "base"),
        "device": os.getenv("AION_WHISPER_DEVICE", "auto"),
        "compute_type": os.getenv("AION_WHISPER_COMPUTE_TYPE", "int8"),
    }


def transcribe_audio_bytes(audio_bytes: bytes, filename: str = "audio.webm") -> SttResult:
    config = get_faster_whisper_config()

    if not audio_bytes:
        return SttResult(
            ok=False,
            provider="faster_whisper",
            reason="empty_audio",
            message="No audio bytes were supplied for transcription.",
            model=config["model"],
            device=config["device"],
            compute_type=config["compute_type"],
        )

    try:
        from faster_whisper import WhisperModel  # type: ignore
    except Exception as exc:
        return SttResult(
            ok=False,
            provider="faster_whisper",
            reason="local_stt_dependency_missing",
            message=(
                "faster-whisper is not installed yet. "
                "Install local voice dependencies with: "
                "python -m pip install -r backend/requirements-voice-local.txt"
            ),
            model=config["model"],
            device=config["device"],
            compute_type=config["compute_type"],
        )

    suffix = Path(filename or "audio.webm").suffix or ".webm"

    with tempfile.NamedTemporaryFile(prefix="aion_stt_", suffix=suffix, delete=True) as tmp:
        tmp.write(audio_bytes)
        tmp.flush()

        model = WhisperModel(
            config["model"],
            device=config["device"],
            compute_type=config["compute_type"],
        )
        segments_iter, info = model.transcribe(tmp.name)

        segments: list[dict[str, Any]] = []
        text_parts: list[str] = []

        for segment in segments_iter:
            segment_text = str(getattr(segment, "text", "") or "").strip()
            if segment_text:
                text_parts.append(segment_text)
            segments.append(
                {
                    "id": getattr(segment, "id", len(segments)),
                    "start": float(getattr(segment, "start", 0.0) or 0.0),
                    "end": float(getattr(segment, "end", 0.0) or 0.0),
                    "text": segment_text,
                }
            )

        language = getattr(info, "language", None)

        return SttResult(
            ok=True,
            provider="faster_whisper",
            text=" ".join(text_parts).strip(),
            language=language,
            segments=segments,
            model=config["model"],
            device=config["device"],
            compute_type=config["compute_type"],
        )
