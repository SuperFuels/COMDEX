# 📄 backend/modules/tessaris/tessaris_utils.py
"""
Tessaris Utilities
==================
Provides global helpers for accessing the TessarisEngine singleton.

Used by CodexScheduler, CodexAutopilot, and QQC kernel integrations
to align symbolic execution with Tessaris reflection/intention logic.
"""

from typing import Optional
from backend.modules.tessaris.tessaris_engine import TessarisEngine

# 🧠 Global Tessaris instance cache
_TESSARIS_INSTANCE: Optional[TessarisEngine] = None


def _get_tessaris(container_id: str = "codex_main") -> TessarisEngine:
    """
    Lazily initialize and return the global TessarisEngine instance.

    Args:
        container_id: optional override to bind Tessaris to a specific container.

    Returns:
        TessarisEngine: active singleton instance.
    """
    global _TESSARIS_INSTANCE
    if _TESSARIS_INSTANCE is None:
        print(f"🌌 Initializing TessarisEngine for container: {container_id}")
        _TESSARIS_INSTANCE = TessarisEngine(container_id=container_id)
    return _TESSARIS_INSTANCE


def _reset_tessaris():
    """
    Reset the cached TessarisEngine instance.
    Mostly for tests or hot-reload.
    """
    global _TESSARIS_INSTANCE
    _TESSARIS_INSTANCE = None