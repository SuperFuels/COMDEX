from __future__ import annotations

from backend.modules.aion_voice.schemas import VoiceResult


BROWSER_SPEECH_PROVIDER_ID = "browser_speech"


def synthesize_with_browser_fallback(*, enabled: bool) -> VoiceResult:
    """Browser speech is intentionally disabled by default.

    The backend cannot generate browser speech audio. This provider only returns
    an explicit instruction/state for the frontend when the user has deliberately
    enabled browser fallback.
    """
    if not enabled:
        return VoiceResult(
            ok=False,
            provider=BROWSER_SPEECH_PROVIDER_ID,
            reason="browser_speech_disabled",
            message="Browser speech fallback is disabled by default.",
            fallback="none",
            metadata={
                "robotic_fallback": True,
                "enabled": False,
                "silent_fallback_allowed": False,
            },
        )

    return VoiceResult(
        ok=False,
        provider=BROWSER_SPEECH_PROVIDER_ID,
        reason="browser_speech_frontend_only",
        message=(
            "Browser speech is enabled, but it must be started explicitly "
            "by the frontend. It must not start silently."
        ),
        fallback="manual_browser_speech",
        metadata={
            "robotic_fallback": True,
            "enabled": True,
            "silent_fallback_allowed": False,
        },
    )
