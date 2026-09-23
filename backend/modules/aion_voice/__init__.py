"""AION local-first voice provider router.

O21A/O21B lock:
- ElevenLabs is no longer the default voice path.
- Kokoro is the default local provider.
- Browser speech fallback is disabled unless explicitly enabled.
- O21B adds Kokoro local TTS generation and cache support.
"""

from .voice_router import (
    AION_VOICE_ROUTER_VERSION,
    get_voice_provider_status,
    synthesize_text,
)

__all__ = [
    "AION_VOICE_ROUTER_VERSION",
    "get_voice_provider_status",
    "synthesize_text",
]
