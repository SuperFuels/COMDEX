from __future__ import annotations

from typing import Optional

from backend.modules.aion_voice.schemas import VoiceResult


ELEVENLABS_PROVIDER_ID = "elevenlabs"


def synthesize_with_elevenlabs(
    text: str,
    *,
    enabled: bool,
    voice_id: Optional[str] = None,
    model_id: Optional[str] = None,
) -> VoiceResult:
    """O21A guarded ElevenLabs wrapper.

    ElevenLabs must not be called unless explicitly enabled.
    O21A intentionally keeps the old paid provider behind a hard gate.
    """
    if not enabled:
        return VoiceResult(
            ok=False,
            provider=ELEVENLABS_PROVIDER_ID,
            reason="elevenlabs_disabled",
            message=(
                "ElevenLabs is disabled. Set AION_ALLOW_ELEVENLABS=true "
                "and explicitly select provider=elevenlabs to use paid cloud voice."
            ),
            fallback="none",
            metadata={
                "paid_cloud_provider": True,
                "enabled": False,
                "would_call_elevenlabs": False,
            },
        )

    # O21A is only the router skeleton. The existing route can be wired into this
    # provider in a later guarded patch if the user deliberately enables it.
    return VoiceResult(
        ok=False,
        provider=ELEVENLABS_PROVIDER_ID,
        reason="elevenlabs_provider_not_wired_in_o21a",
        message=(
            "ElevenLabs was explicitly enabled, but O21A does not perform "
            "the paid provider call. Wire the existing ElevenLabs implementation "
            "behind this provider after the local-first router lock is stable."
        ),
        fallback="none",
        metadata={
            "paid_cloud_provider": True,
            "enabled": True,
            "would_call_elevenlabs": False,
            "voice_id": voice_id,
            "model_id": model_id,
            "o21a_router_only": True,
        },
    )
