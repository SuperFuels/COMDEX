from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any, Optional

from backend.modules.aion_voice.schemas import VoiceResult


KOKORO_PROVIDER_ID = "kokoro"
KOKORO_PROVIDER_VERSION = "aion.kokoro_tts.o21b.v0.1"

_PIPELINE: Any = None
_PIPELINE_KEY: tuple[str, str] | None = None


def reset_kokoro_provider_for_tests() -> None:
    global _PIPELINE, _PIPELINE_KEY
    _PIPELINE = None
    _PIPELINE_KEY = None


def _safe_text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:24]


def _cache_dir() -> Path:
    root = os.getenv("AION_VOICE_CACHE_DIR", ".runtime/voice_cache")
    return Path(root) / "kokoro"


def _sample_rate() -> int:
    raw = os.getenv("AION_KOKORO_SAMPLE_RATE", "24000")
    try:
        value = int(raw)
    except Exception:
        value = 24000
    return value if value > 0 else 24000


def _default_voice() -> str:
    return os.getenv("AION_KOKORO_VOICE", "af_heart")


def _default_lang_code() -> str:
    return os.getenv("AION_KOKORO_LANG_CODE", "a")


def _model_id(model_id: Optional[str]) -> str:
    return model_id or os.getenv("AION_KOKORO_MODEL", "kokoro")


def _cache_key(text: str, voice_id: str, model_id: str, sample_rate: int) -> str:
    material = "|".join(
        [
            KOKORO_PROVIDER_VERSION,
            model_id,
            voice_id,
            str(sample_rate),
            hashlib.sha256(text.encode("utf-8")).hexdigest(),
        ]
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _load_pipeline(lang_code: str, model_id: str) -> Any:
    global _PIPELINE, _PIPELINE_KEY

    key = (lang_code, model_id)
    if _PIPELINE is not None and _PIPELINE_KEY == key:
        return _PIPELINE

    try:
        from kokoro import KPipeline  # type: ignore
    except Exception as exc:
        raise RuntimeError(
            "Kokoro is not installed. Install local voice dependencies with: "
            "python -m pip install kokoro soundfile"
        ) from exc

    _PIPELINE = KPipeline(lang_code=lang_code)
    _PIPELINE_KEY = key
    return _PIPELINE


def _first_audio_from_generator(generator: Any) -> Any:
    for item in generator:
        if isinstance(item, tuple) and len(item) >= 3:
            return item[2]
        return item
    raise RuntimeError("Kokoro returned no audio segments.")


def synthesize_with_kokoro(
    text: str,
    *,
    voice_id: Optional[str] = None,
    model_id: Optional[str] = None,
) -> VoiceResult:
    clean_text = (text or "").strip()
    voice = voice_id or _default_voice()
    model = _model_id(model_id)
    sample_rate = _sample_rate()
    lang_code = _default_lang_code()

    if not clean_text:
        return VoiceResult(
            ok=False,
            provider=KOKORO_PROVIDER_ID,
            reason="missing_text",
            message="No text was supplied for local Kokoro TTS.",
            fallback="none",
            metadata={
                "local_voice": True,
                "provider_version": KOKORO_PROVIDER_VERSION,
            },
        )

    cache_root = _cache_dir()
    cache_root.mkdir(parents=True, exist_ok=True)

    key = _cache_key(clean_text, voice, model, sample_rate)
    cache_path = cache_root / f"{key}.wav"

    headers = {
        "x-aion-voice-provider": KOKORO_PROVIDER_ID,
        "x-aion-voice-local": "true",
        "x-aion-voice-cache-key": key,
    }

    if cache_path.exists() and cache_path.stat().st_size > 0:
        audio = cache_path.read_bytes()
        return VoiceResult(
            ok=True,
            provider=KOKORO_PROVIDER_ID,
            reason="ok",
            message="Kokoro local TTS audio returned from cache.",
            fallback="none",
            audio_bytes=audio,
            media_type="audio/wav",
            headers={**headers, "x-aion-voice-cache": "hit"},
            metadata={
                "local_voice": True,
                "cache_hit": True,
                "cache_path": str(cache_path),
                "voice_id": voice,
                "model_id": model,
                "sample_rate": sample_rate,
                "text_hash": _safe_text_hash(clean_text),
                "provider_version": KOKORO_PROVIDER_VERSION,
            },
        )

    try:
        import soundfile as sf  # type: ignore

        pipeline = _load_pipeline(lang_code, model)
        generator = pipeline(clean_text, voice=voice)
        audio = _first_audio_from_generator(generator)

        sf.write(str(cache_path), audio, sample_rate, format="WAV")
        audio_bytes = cache_path.read_bytes()

        return VoiceResult(
            ok=True,
            provider=KOKORO_PROVIDER_ID,
            reason="ok",
            message="Kokoro local TTS audio generated.",
            fallback="none",
            audio_bytes=audio_bytes,
            media_type="audio/wav",
            headers={**headers, "x-aion-voice-cache": "miss"},
            metadata={
                "local_voice": True,
                "cache_hit": False,
                "cache_path": str(cache_path),
                "voice_id": voice,
                "model_id": model,
                "sample_rate": sample_rate,
                "lang_code": lang_code,
                "text_hash": _safe_text_hash(clean_text),
                "provider_version": KOKORO_PROVIDER_VERSION,
            },
        )

    except Exception as exc:
        return VoiceResult(
            ok=False,
            provider=KOKORO_PROVIDER_ID,
            reason="local_tts_error",
            message=str(exc),
            fallback="none",
            headers=headers,
            metadata={
                "local_voice": True,
                "cache_hit": False,
                "voice_id": voice,
                "model_id": model,
                "sample_rate": sample_rate,
                "lang_code": lang_code,
                "text_hash": _safe_text_hash(clean_text),
                "provider_version": KOKORO_PROVIDER_VERSION,
                "install_hint": "python -m pip install kokoro soundfile",
            },
        )
