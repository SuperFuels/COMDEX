from __future__ import annotations

import os
from typing import Dict, Optional

from backend.modules.aion_voice.providers.browser_fallback import synthesize_with_browser_fallback
from backend.modules.aion_voice.providers.elevenlabs_tts import synthesize_with_elevenlabs
from backend.modules.aion_voice.providers.kokoro_tts import synthesize_with_kokoro
from backend.modules.aion_voice.schemas import VoiceResult


AION_VOICE_ROUTER_VERSION = "aion.voice_router.o21a.v0.1"

DEFAULT_TTS_PROVIDER = "kokoro"
DEFAULT_STT_PROVIDER = "faster_whisper"

SUPPORTED_TTS_PROVIDERS = {
    "kokoro",
    "local_kokoro",
    "elevenlabs",
    "browser_speech",
}

PROVIDER_ALIASES = {
    "local_kokoro": "kokoro",
    "kokoro": "kokoro",
    "elevenlabs": "elevenlabs",
    "browser": "browser_speech",
    "browser_speech": "browser_speech",
}


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on", "enabled"}


def _normalise_provider(provider: Optional[str]) -> str:
    value = (provider or os.getenv("AION_TTS_PROVIDER") or DEFAULT_TTS_PROVIDER).strip().lower()
    return PROVIDER_ALIASES.get(value, value)


def get_voice_provider_status() -> Dict[str, object]:
    provider = _normalise_provider(None)
    allow_elevenlabs = _env_bool("AION_ALLOW_ELEVENLABS", False)
    allow_browser_speech = _env_bool("AION_ALLOW_BROWSER_SPEECH", False)
    local_voice_enabled = _env_bool("AION_LOCAL_VOICE_ENABLED", True)

    return {
        "ok": True,
        "schema_version": AION_VOICE_ROUTER_VERSION,
        "tts_provider": provider,
        "stt_provider": os.getenv("AION_STT_PROVIDER", DEFAULT_STT_PROVIDER),
        "default_tts_provider": DEFAULT_TTS_PROVIDER,
        "default_stt_provider": DEFAULT_STT_PROVIDER,
        "elevenlabs_enabled": allow_elevenlabs,
        "browser_fallback_enabled": allow_browser_speech,
        "local_voice_enabled": local_voice_enabled,
        "local_voice_ready": provider == "kokoro" and local_voice_enabled,
        "cloud_voice": "on" if allow_elevenlabs and provider == "elevenlabs" else "off",
        "no_elevenlabs_credits_required": provider != "elevenlabs",
        "silent_browser_fallback_allowed": False,
        "supported_tts_providers": sorted(SUPPORTED_TTS_PROVIDERS),
    }


def synthesize_text(
    text: str,
    provider: Optional[str] = None,
    voice_id: Optional[str] = None,
    model_id: Optional[str] = None,
) -> VoiceResult:
    selected = _normalise_provider(provider)
    allow_elevenlabs = _env_bool("AION_ALLOW_ELEVENLABS", False)
    allow_browser_speech = _env_bool("AION_ALLOW_BROWSER_SPEECH", False)
    local_voice_enabled = _env_bool("AION_LOCAL_VOICE_ENABLED", True)

    if selected not in SUPPORTED_TTS_PROVIDERS:
        return VoiceResult(
            ok=False,
            provider=selected,
            reason="unsupported_voice_provider",
            message=f"Unsupported AION voice provider: {selected}",
            fallback="none",
            metadata={
                "router_version": AION_VOICE_ROUTER_VERSION,
                "supported_tts_providers": sorted(SUPPORTED_TTS_PROVIDERS),
            },
        )

    if selected == "kokoro":
        if not local_voice_enabled:
            return VoiceResult(
                ok=False,
                provider="kokoro",
                reason="local_voice_disabled",
                message="Local voice is disabled. Set AION_LOCAL_VOICE_ENABLED=true to use Kokoro.",
                fallback="none",
                metadata={
                    "router_version": AION_VOICE_ROUTER_VERSION,
                    "would_call_kokoro": False,
                },
            )
        return synthesize_with_kokoro(text, voice_id=voice_id, model_id=model_id)

    if selected == "elevenlabs":
        return synthesize_with_elevenlabs(
            text,
            enabled=allow_elevenlabs,
            voice_id=voice_id,
            model_id=model_id,
        )

    if selected == "browser_speech":
        return synthesize_with_browser_fallback(enabled=allow_browser_speech)

    return VoiceResult(
        ok=False,
        provider=selected,
        reason="voice_provider_not_routed",
        message=f"Provider {selected} is known but not routed.",
        fallback="none",
        metadata={"router_version": AION_VOICE_ROUTER_VERSION},
    )
